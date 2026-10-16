"""Presentation-only local usage display. Never launches a model or changes its context."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys
import threading
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from observer.storage import JsonlReader

HERE = Path(__file__).resolve().parent
FIELDS = ("input", "output", "cache_read", "cache_write", "reasoning")


def stamp(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except ValueError:
        return None


def count(value):
    return value if type(value) is int and 0 <= value <= 2**53 - 1 else None


def usage(raw, engine):
    if not isinstance(raw, dict):
        return dict.fromkeys(FIELDS)
    mapping = ({"input": "input_tokens", "output": "output_tokens", "cache_read": "cached_input_tokens",
                "reasoning": "reasoning_output_tokens"} if engine == "codex" else
               {"input": "input_tokens", "output": "output_tokens", "cache_read": "cache_read_input_tokens",
                "cache_write": "cache_creation_input_tokens"})
    result = {key: count(raw.get(mapping[key])) if key in mapping else None for key in FIELDS}
    if engine == "codex" and ((result["cache_read"] is not None and result["input"] is not None
                               and result["cache_read"] > result["input"]) or
                              (result["reasoning"] is not None and result["output"] is not None
                               and result["reasoning"] > result["output"])):
        raise ValueError("invalid_usage_subset")
    return result


class Meter:
    """One explicit source and identity. Repeated snapshots/messages replace, never sum twice."""
    def __init__(self, engine, session, role="parent", since=None, until=None):
        if engine not in ("codex", "claude") or role not in ("parent", "child"):
            raise ValueError("invalid_profile")
        self.engine, self.session, self.role = engine, str(UUID(session)), role
        self.bound = False
        self.values = dict.fromkeys(FIELDS)
        self.messages, self.responses = {}, {}
        self.highwater = {}
        self.basis = "unobserved"
        self.status = "waiting"
        self.start, self.last, self.end = None, None, None
        self.model = None
        self.records, self.errors = 0, set()
        self.since = stamp(since) if since else None
        if since and self.since is None:
            raise ValueError("invalid_since")
        self.until = stamp(until) if until else None
        if until and (self.until is None or self.since is not None and self.until < self.since):
            raise ValueError("invalid_until")
        self.baseline = None

    def snapshot(self, raw, basis):
        value = usage(raw, self.engine)
        if not any(v is not None for v in value.values()):
            return False
        if basis == "session_cumulative":
            if any(v is not None and v < self.highwater.get(k, 0) for k, v in value.items()):
                self.errors.add("usage_regressed")
                return False
            self.highwater.update({k: v for k, v in value.items() if v is not None})
        self.values, self.basis = value, basis
        return True

    def summed(self, entries, basis):
        self.values = {key: (sum(v[key] for v in entries.values()) if entries and
                            all(v[key] is not None for v in entries.values()) else None) for key in FIELDS}
        self.basis = basis

    def feed(self, raw):
        typ = raw.get("type")
        p = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        identity = (p.get("id") if typ == "session_meta" else raw.get("thread_id") if typ == "thread.started"
                    else raw.get("session_id") or raw.get("sessionId") if self.engine == "claude" else None)
        if identity:
            if identity != self.session:
                self.errors.add("identity_mismatch")
                return
            self.bound = True
        if not self.bound:
            return
        # All subsequent records carrying an identity must remain in this selected session.
        sid = raw.get("session_id") or raw.get("sessionId")
        if sid and sid != self.session:
            self.errors.add("identity_mismatch")
            return
        at = stamp(raw.get("timestamp"))
        if self.until is not None and (at is None or at > self.until):
            return
        if self.since is not None and (at is None or at < self.since):
            if typ == "event_msg" and p.get("type") == "token_count":
                self.baseline = usage((p.get("info") or {}).get("total_token_usage"), "codex")
            return
        self.records += 1
        if at is not None:
            self.last = max(self.last or at, at)
        if self.engine == "codex":
            subtype = p.get("type")
            if typ == "turn_context" and isinstance(p.get("model"), str) and re.fullmatch(r"gpt-[a-z0-9.-]{1,80}", p["model"]):
                self.model = p["model"]
            if typ == "response_item" and p.get("role") == "user" and (self.start is None or self.status == "completed"):
                self.start, self.status, self.end = at, "running", None
            if typ == "event_msg" and subtype in ("task_started", "turn_started"):
                self.start = at
                self.status, self.end = "running", None
            if typ == "event_msg" and subtype == "token_count" and not self.responses:
                totals = (p.get("info") or {}).get("total_token_usage")
                if not self.snapshot(totals, "session_cumulative"):
                    return
                if self.since is not None and self.baseline:
                    delta = {k: v - self.baseline[k] if v is not None and self.baseline[k] is not None else None
                             for k, v in self.values.items()}
                    if any(v is not None and v < 0 for v in delta.values()):
                        self.errors.add("usage_regressed")
                    else:
                        self.values, self.basis = delta, "cumulative_window_delta"
            # Newer rollout schema: per response, repeated records update the same response.
            if typ == "token_usage_record":
                entry = p or raw
                rid = entry.get("response_id")
                tokens = entry.get("usage") or entry.get("token_usage")
                if rid and isinstance(rid, str) and len(rid) <= 200 and isinstance(tokens, dict):
                    if rid not in self.responses and len(self.responses) >= 4096:
                        self.errors.add("response_limit")
                        return
                    self.responses[rid] = usage(tokens, "codex")
                    self.summed(self.responses, "unique_responses")
            if typ == "turn.started":
                self.status, self.start, self.end = "running", at, None
            if typ == "turn.completed":
                self.snapshot(raw.get("usage"), "cli_turn_reported")
            if typ in ("turn.completed", "turn.failed") or (typ == "event_msg" and subtype in
                    ("task_complete", "turn_complete", "turn_aborted")):
                self.status = "failed" if typ == "turn.failed" or subtype == "turn_aborted" else "completed"
                self.end = at
        else:
            message = raw.get("message") if isinstance(raw.get("message"), dict) else {}
            content = message.get("content")
            human = isinstance(content, str) or isinstance(content, list) and any(
                isinstance(block, dict) and block.get("type") in ("text", "input_text", "image") for block in content)
            if typ == "user" and human and raw.get("isMeta") is not True:
                self.start, self.status, self.end = at, "running", None
            model = message.get("model") or (raw.get("model") if typ == "system" else None)
            if isinstance(model, str) and re.fullmatch(r"claude-(?:opus|sonnet|haiku|fable)-[a-z0-9.-]{1,70}", model):
                self.model = model
            mid = message.get("id")
            if typ == "assistant" and isinstance(mid, str) and len(mid) <= 200 and isinstance(message.get("usage"), dict):
                if mid not in self.messages and len(self.messages) >= 4096:
                    self.errors.add("message_limit")
                    return
                self.messages[mid] = usage(message.get("usage"), "claude")
                self.summed(self.messages, "unique_messages")
            if typ == "assistant" and message.get("stop_reason") == "end_turn":
                self.status, self.end = "completed", at
            if typ == "result":
                # CLI terminal aggregates may cover different layers; do not add them to messages.
                if not self.messages:
                    self.snapshot(raw.get("usage"), "cli_result_reported")
                self.status = "failed" if raw.get("is_error") else "completed"
                self.end = at or self.last

    def view(self, live=False):
        stop = self.end if self.end is not None else time.time() if live and self.status == "running" else self.last
        elapsed = round(max(0, stop - self.start), 1) if stop is not None and self.start is not None else None
        return {"engine": self.engine, "role": self.role, "session_id": self.session, "model": self.model,
                "status": self.status, "basis": self.basis, "tokens": self.values.copy(),
                "elapsed_seconds": elapsed, "elapsed_basis": "latest_observed_task_interval" if elapsed is not None else "unobserved",
                "last_event_utc": datetime.fromtimestamp(self.last, timezone.utc).isoformat() if self.last else None,
                "records": self.records, "errors": sorted(self.errors),
                "coverage": "selected_log_only", "time_filter": self.since is not None, "backend_billing": None}


class Display:
    def __init__(self, sources, mode="replay"):
        if mode not in ("live", "replay") or not 1 <= len(sources) <= 9:
            raise ValueError("invalid_display_config")
        self.sources = [(JsonlReader(path, max_line=4 * 1024 * 1024), meter) for path, meter in sources]
        self.mode, self.lock = mode, threading.Lock()

    def poll(self):
        with self.lock:
            for reader, meter in self.sources:
                for _, record in reader.poll(final=self.mode == "replay"):
                    try:
                        meter.feed(record)
                    except (ValueError, TypeError, KeyError):
                        meter.errors.add("invalid_record")
                meter.errors.update(reader.errors)

    def view(self):
        with self.lock:
            return {"format": "lgax-presentation-usage-v1", "mode": self.mode,
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                    "sources": [m.view(live=self.mode == "live") for _, m in self.sources],
                    "model_calls_added": 0, "deployment": "presentation_only", "total_billing": None}


def handler(display):
    page = (HERE / "index.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Only this loopback origin is served; no arbitrary file path or cross-origin API.
            host = self.headers.get("Host", "")
            if host != f"127.0.0.1:{self.server.server_port}":
                self.send_error(403)
                return
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                self.send_error(403)
                return
            if self.path == "/":
                raw, content = page, "text/html; charset=utf-8"
            elif self.path == "/usage.json":
                raw, content = json.dumps(display.view(), ensure_ascii=False).encode(), "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_):
            pass

    return Handler


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", choices=("codex", "claude"), required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--child", nargs=2, action="append", default=[], metavar=("SESSION_ID", "JSONL"))
    p.add_argument("--mode", choices=("live", "replay"), default="replay")
    p.add_argument("--since", help="Explicit timestamp for a recorded task; without it show the selected session")
    p.add_argument("--until", help="Optional recorded task end timestamp; excludes later conversation turns")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--snapshot", type=Path, help="Write sanitized JSON once, without starting a server")
    a = p.parse_args()
    if not 0 <= a.port <= 65535:
        p.error("invalid port")
    sources = [(a.log, Meter(a.engine, a.session_id, since=a.since, until=a.until))]
    sources += [(Path(path), Meter(a.engine, sid, "child", since=a.since, until=a.until)) for sid, path in a.child]
    display = Display(sources, a.mode)
    display.poll()
    if a.snapshot:
        if any(a.snapshot.resolve() == path.resolve() for path, _ in sources):
            p.error("snapshot cannot replace a source")
        with a.snapshot.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(display.view(), ensure_ascii=False, indent=2) + "\n")
        print("Sanitized presentation snapshot written; model calls added: 0")
        return
    server = ThreadingHTTPServer(("127.0.0.1", a.port), handler(display))
    stop = threading.Event()

    def refresh():
        while not stop.wait(1):
            if a.mode == "live":
                display.poll()

    thread = threading.Thread(target=refresh, daemon=True)
    thread.start()
    print(f"Presentation token widget: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
