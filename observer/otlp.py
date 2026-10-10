"""Langfuse v4 OTLP/HTTP JSON adapter, using only Python's standard library.

No generation/model/cost attributes: native session totals are metadata only.
Each completed observation gets at most one attempted send, including failures.
"""
import base64
from datetime import datetime
import hashlib
import json
import os
import queue
import re
import threading
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or
            parsed.query or parsed.fragment or parsed.path != "/api/public/otel/v1/traces" or
            any(c in value for c in ("\r", "\n", " "))):
        raise ValueError("invalid_https_otlp_endpoint")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid_https_otlp_endpoint") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("invalid_https_otlp_endpoint")
    return value


def nanos(value):
    return str(int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1_000_000_000))


def hash_id(value, size):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:size]


def attr(key, value):
    if type(value) is bool:
        val = {"boolValue": value}
    elif type(value) is int:
        val = {"intValue": str(value)}
    else:
        val = {"stringValue": value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))}
    return {"key": key, "value": val}


def payload(event):
    if event.get("status") not in ("completed", "failed", "cancelled"):
        raise ValueError("only_completed_spans_exportable")
    # Re-allowlist here; never export an arbitrary dictionary from disk.
    if event.get("entity_kind") not in ("agent", "tool", "runtime", "turn"):
        raise ValueError("invalid_entity_kind")
    for key in ("event_id", "source_log_ref"):
        if not re.fullmatch(r"[a-f0-9]{64}", event.get(key, "")):
            raise ValueError("invalid_event_reference")
    allowed = {"run_id", "native_thread_id", "turn_id", "invocation_id", "parent_id", "status",
        "event_kind", "source_kind", "mode", "coverage", "usage_scope", "usage_snapshot",
        "skill_mapping_basis", "mapped_skill", "timing_basis", "native_usage_snapshot", "native_usage_status", "cli_version"}
    metadata = {key: event.get(key) for key in allowed}
    # Validate metadata strings rather than allowing private paths/keys from a tampered journal.
    for key, value in metadata.items():
        if isinstance(value, str) and (len(value) > 80 or not re.fullmatch(r"[A-Za-z0-9_.-]+", value) or value.startswith(("sk-", "pk-"))):
            raise ValueError("invalid_metadata")
    fields = {"input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"}
    for key in ("usage_snapshot", "native_usage_snapshot"):
        snapshot = metadata.get(key)
        if not isinstance(snapshot, dict) or set(snapshot) != fields or any(v is not None and (type(v) is not int or v < 0) for v in snapshot.values()):
            raise ValueError("invalid_usage_metadata")
    trace_id = hash_id(event["run_id"] + ":" + event["native_thread_id"], 32)
    span_seed = event.get("invocation_id") or event["event_id"]
    span_id = hash_id(event["native_thread_id"] + ":" + event["source_log_ref"] + ":" + span_seed, 16)
    end = event.get("source_timestamp") or event["observed_timestamp"]
    start = event.get("start_timestamp") or end
    if int(nanos(start)) > int(nanos(end)):
        start = end
    attributes = [attr("langfuse.observation.type", "tool" if event["entity_kind"] == "tool" else "span"),
        attr("langfuse.session.id", event["native_thread_id"]), attr("langfuse.trace.name", "native-observer"),
        attr("langfuse.environment", "development")]
    attributes.extend(attr("langfuse.observation.metadata." + key, value) for key, value in sorted(metadata.items()))
    span = {"traceId": trace_id, "spanId": span_id, "name": "native-observer." + event["entity_kind"],
        "kind": 1, "startTimeUnixNano": nanos(start), "endTimeUnixNano": nanos(end),
        "attributes": attributes, "status": {"code": 2 if event["status"] == "failed" else 0}}
    if event.get("parent_id"):
        span["parentSpanId"] = hash_id(event["native_thread_id"] + ":" + event["source_log_ref"] + ":" + event["parent_id"], 16)
    return {"resourceSpans": [{"resource": {"attributes": [attr("service.name", "lg-native-observer")]},
        "scopeSpans": [{"scope": {"name": "observer", "version": "0.1.0"}, "spans": [span]}]}]}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward authentication to a redirected host.
        return None


class Exporter:
    def __init__(self, store, environment=None, timeout=2.0, capacity=128, opener=None):
        if not 0.05 <= timeout <= 10 or not 1 <= capacity <= 1024:
            raise ValueError("invalid_export_bounds")
        env = os.environ if environment is None else environment
        target, public, secret = (env.get(name) for name in ("OBSERVER_OTLP_ENDPOINT", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"))
        self.configured = bool(target and public and secret)
        self.target = endpoint(target) if target else None
        self.authorization = "Basic " + base64.b64encode((public + ":" + secret).encode()).decode() if self.configured else None
        self.timeout, self.store = timeout, store
        self.opener = opener or build_opener(NoRedirect())
        self.queue = queue.Queue(maxsize=capacity)
        self.attempted_ids = store.attempted()
        self.counters = {"queued": 0, "dropped": 0, "exported": 0, "failed": 0, "duplicate": 0, "not_configured": 0}
        self.stopping = threading.Event()
        self.thread = None

    def submit(self, event):
        if event.get("status") not in ("completed", "failed", "cancelled"):
            return
        if not self.configured:
            self.counters["not_configured"] += 1
            return
        try:
            body_value = payload(event)
            span = body_value["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
            attempt_id = hash_id(span["traceId"] + ":" + span["spanId"], 64)
        except (ValueError, KeyError, TypeError):
            self.counters["failed"] += 1
            return
        if attempt_id in self.attempted_ids:
            self.counters["duplicate"] += 1
            return
        try:
            body = json.dumps(body_value).encode("utf-8")
            self.store.mark_attempt(attempt_id)
            self.attempted_ids.add(attempt_id)
            self.queue.put_nowait(body)
            self.counters["queued"] += 1
        except queue.Full:
            self.counters["dropped"] += 1
        except (OSError, ValueError, KeyError, TypeError):
            self.counters["failed"] += 1

    def start(self):
        if self.configured and self.thread is None:
            self.thread = threading.Thread(target=self.work, daemon=True, name="observer-export")
            self.thread.start()

    def work(self):
        while not self.stopping.is_set():
            try:
                body = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                request = Request(self.target, data=body, method="POST", headers={"Content-Type": "application/json",
                    "Authorization": self.authorization, "x-langfuse-ingestion-version": "4"})
                with self.opener.open(request, timeout=self.timeout) as response:
                    if not 200 <= response.status < 300:
                        raise OSError("http_failure")
                    # A 2xx partial-success response is not full acceptance.
                    raw = response.read(65537)
                    if len(raw) > 65536:
                        raise ValueError("response_limit")
                    value = json.loads(raw) if raw else {}
                    partial = value.get("partialSuccess", {})
                    if partial.get("rejectedSpans", "0") not in (0, "0", None) or partial.get("errorMessage"):
                        raise ValueError("partial_export_rejected")
                self.counters["exported"] += 1
            except Exception:
                # Credential values, response body, URLs and exception strings never leave this adapter.
                self.counters["failed"] += 1
            finally:
                self.queue.task_done()

    def close(self, grace=3.0):
        if self.thread:
            self.thread.join(timeout=0)  # Do not block waiting for the worker's infinite loop.
            import time
            deadline = time.monotonic() + min(max(grace, 0), 10)
            while self.queue.unfinished_tasks and time.monotonic() < deadline:
                time.sleep(0.02)
            self.stopping.set()
            self.thread.join(timeout=self.timeout + 0.2)
        while True:
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                self.counters["dropped"] += 1
            except queue.Empty:
                break

    def summary(self):
        return {"configured": self.configured, "protocol": "OTLP_HTTP_JSON_v4", "counters": dict(self.counters)}
