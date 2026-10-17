"""Result-file delivery and read-only diagnosis. No model, server or browser automation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import hook

LIMIT = 64 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bytes(paths, path):
    hook.checked_path(paths.harness, str(path))
    if path.stat().st_size > LIMIT:
        raise ValueError("file_too_large")
    return path.read_bytes()


def shape(value):
    """Same structural boundary as viewState.ts; never certifies source meaning."""
    if not isinstance(value, dict) or value.get("kind") != "lgax-view":
        return False
    report = value.get("report")
    if report is not None and (not isinstance(report, dict) or not isinstance(report.get("export"), dict)
                              or not isinstance(report["export"].get("turns"), list)
                              or any(not isinstance(t, dict) or not isinstance(t.get("state"), dict)
                                     for t in report["export"]["turns"])):
        return False
    def text(obj, key):
        return key not in obj or isinstance(obj[key], str)
    if not text(value, "generated_at"):
        return False
    for section, keys in (("app", ("title", "subtitle")), ("context", ("meta", "loaded"))):
        if section in value and (not isinstance(value[section], dict) or any(not text(value[section], k) for k in keys)):
            return False
    context = value.get("context", {})
    if "file" in context and (not isinstance(context["file"], dict) or not isinstance(context["file"].get("name"), str)):
        return False
    if "status" in context and (not isinstance(context["status"], list) or any(
            not isinstance(s, dict) or not isinstance(s.get("text"), str) for s in context["status"])):
        return False
    if "footer" in context and (not isinstance(context["footer"], list) or any(not isinstance(s, str) for s in context["footer"])):
        return False
    pages = value.get("pages")
    if not isinstance(pages, list) or not pages:
        return False
    ids = set()
    def tree(v, depth=0):
        if depth > 64:
            return False
        if isinstance(v, list):
            return all(tree(x, depth + 1) for x in v)
        if not isinstance(v, dict):
            return True
        for key in ("blocks", "items", "columns", "cols", "rows", "nodes", "links", "quotes"):
            if key in v and (not isinstance(v[key], list) or any(x is None for x in v[key])):
                return False
        if "blocks" in v and any(not isinstance(b, dict) or not isinstance(b.get("type"), str) for b in v["blocks"]):
            return False
        if v.get("type") == "flow":
            if not v.get("columns") or any(not isinstance(c, dict) or not isinstance(c.get("key"), str)
                                           or not c["key"] or not text(c, "title") for c in v["columns"]):
                return False
            if any(not isinstance(n, dict) for key in ("nodes", "links") for n in v.get(key, [])):
                return False
        if v.get("type") == "claims" and any(not isinstance(x, dict) for x in v.get("items", [])):
            return False
        return all(tree(x, depth + 1) for x in v.values())
    for p in pages:
        if (not isinstance(p, dict) or not isinstance(p.get("id"), str) or not p["id"] or p["id"] in ids
                or not isinstance(p.get("title"), str) or not text(p, "nav")
                or not isinstance(p.get("blocks"), list) or not tree(p)):
            return False
        if p.get("caption") is not None and (not isinstance(p["caption"], dict)
                or any(not text(p["caption"], k) for k in ("title", "text", "meta"))):
            return False
        ids.add(p["id"])
    return value.get("focus") is None or value["focus"] in ids


def payload(raw):
    text = raw.decode("utf-8-sig")
    match = re.fullmatch(r"\s*(?:/\*.*?\*/\s*)?window\.LGAX_VIEW\s*=\s*(.*?)\s*;\s*", text, re.S)
    if not match:
        raise ValueError("sidecar_assignment")
    return json.loads(match[1], parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non_finite_json")))


def preflight(paths, export, hashes):
    paths.validate()
    raw = read_bytes(paths, export)
    body = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(body, dict) or not isinstance(body.get("session_id"), str) or not isinstance(body.get("turns"), list):
        raise ValueError("export_shape")
    builder = hook.load_build_view(hashes["build_view"])
    requests = body.get("requests") or []
    if not isinstance(requests, list) or any(not isinstance(r, dict) for r in requests):
        raise ValueError("request_shape")
    if body["turns"]:
        if any(not isinstance(t, dict) or not isinstance(t.get("state"), dict) for t in body["turns"]):
            raise ValueError("turn_shape")
        metadata = {}
        _, state = builder.load_web_result(body, export, file_metadata=metadata)
        if state != "verified_binding":
            return body, state, digest(raw)
        current = builder.current_export_turn(body)["state"]
        relevant = [r for r in requests if (r.get("input") or {}).get("request_key") == current.get("request_key")
                    or (not r.get("turn_id") and (r.get("input") or {}).get("prior_turn_id") == current.get("turn_id"))]
    elif not requests:
        raise ValueError("export_empty")
    else:
        relevant = requests
        if any((r.get("response") or {}).get("status") not in ("held", "needs_input") for r in requests):
            return body, "request_in_progress", digest(raw)
    # save_and_export may precede workflow finish. Wait for the final export,
    # not merely the existence of an approved intermediate result. This clock
    # is local workflow finish, never proof of native end_turn/process exit.
    if any(isinstance(r.get("workflow"), dict) and r["workflow"].get("tracked")
           and not r["workflow"].get("finished_at") for r in relevant):
        return body, "awaiting_workflow_finish", digest(raw)
    return body, "verified_binding" if body["turns"] else "request_only", digest(raw)


def diagnose(paths, hashes, export=None, out=None):
    """Only metadata and failure categories leave this function, never source text."""
    paths.validate()
    out = Path(out or paths.out)
    result = {"files": {}, "sidecar_syntax": "not_checked", "view_shape": "not_checked",
              "current_binding": "not_checked", "display_verified": False}
    for name in ("index.html", "view-data.js"):
        p = out / name
        hook.checked_path(paths.harness, str(p))
        exists = p.is_file()
        raw = read_bytes(paths, p) if exists else b""
        result["files"][name] = {"exists": exists, "bytes": len(raw), "sha256": digest(raw) if exists else None}
    index = result["files"]["index.html"]
    result["index_matches_installed"] = index["sha256"] == hashes["index"]
    if not result["files"]["view-data.js"]["exists"]:
        result["sidecar_syntax"] = "missing"
        return result
    try:
        view = payload(read_bytes(paths, out / "view-data.js"))
    except (ValueError, UnicodeError):
        result["sidecar_syntax"] = "invalid"
        return result
    result["sidecar_syntax"] = "valid_assignment_json"
    result["view_shape"] = "valid" if shape(view) else "invalid"
    if result["view_shape"] != "valid":
        return result
    result["pages"] = len(view["pages"])
    latest = hook.newest_export(paths) if export is None else None
    export = Path(latest.path) if latest else export
    if export:
        try:
            body, state, export_sha = preflight(paths, export, hashes)
        except (Exception, SystemExit):
            result["current_binding"] = "invalid_export"
            return result
        result["export"] = export.name
        result["export_sha256"] = export_sha
        result["current_binding"] = state
        stamp = view.get("delivery")
        result["display_ready"] = isinstance(stamp, dict) and stamp.get("display_ready") is True
        if stamp is not None and (not isinstance(stamp, dict) or stamp.get("export_sha256") != export_sha):
            result["current_binding"] = "sidecar_stale"
            return result
        if state == "verified_binding":
            builder = hook.load_build_view(hashes["build_view"])
            expected = builder.current_export_turn(body)
            shown = (view.get("report") or {}).get("export", {}).get("turns", [])
            st = shown[0].get("state", {}) if len(shown) == 1 else {}
            result["current_binding"] = "matched_current" if (st.get("turn_id") == expected["state"].get("turn_id")
                and st.get("result_version") == expected["state"].get("result_version")
                and st.get("latest_result") == expected["state"].get("latest_result")) else "sidecar_stale"
        elif state == "request_only":
            result["current_binding"] = "request_only" if isinstance(stamp, dict) and stamp.get("export_sha256") == export_sha else "sidecar_stale"
    return result


class Delivery:
    def __init__(self, harness, engine, opener=None):
        self.paths = hook.Paths(str(harness))
        self.paths.validate()
        self.engine = engine
        self.opener = opener
        # Office records do not bind a business export to a native thread.
        # One user-started observer lifetime is the safe once-open scope.
        self.open_scope = "observer-" + uuid.uuid4().hex
        app = Path(harness) / "web/prototypes/visual-viewer"
        self.hashes = {key: digest(read_bytes(self.paths, app / name)) for key, name in
                       (("build_view", "build_view.py"), ("index", "index.html"))}
        self.legacy_business = None
        previous = hook.read_state(self.paths)
        if previous.get("opened_sessions") and not previous.get("last_open_request") and previous.get("last_export"):
            try:
                old = json.loads(read_bytes(self.paths, Path(self.paths.exports) / previous["last_export"]).decode("utf-8-sig"))
                self.legacy_business = old.get("session_id")
            except (OSError, ValueError, TypeError):
                pass

    def deliver(self, export, allow_open=True):
        paths = self.paths
        export = Path(export)
        lock = hook.Lock(paths)
        if not lock.acquire(2):
            return {"status": "busy", "display_verified": False}
        stage = None
        try:
            body, state, before = preflight(paths, export, self.hashes)
            if state not in ("verified_binding", "request_only"):
                return {"status": "waiting_binding", "binding": state, "display_verified": False}
            current = hook.read_state(paths)
            entry = hook.newest_export(paths)
            if entry is None or Path(entry.path) != export:
                return {"status": "superseded", "display_verified": False}
            key = hook.export_key(entry)
            good = diagnose(paths, self.hashes, export)
            ready = (good["view_shape"] == "valid" and good["index_matches_installed"]
                     and good["current_binding"] in ("matched_current", "request_only")
                     and good.get("display_ready") is True)
            if current.get("built_key") != key or not ready:
                os.makedirs(paths.out, exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix=".delivery-", dir=paths.out))
                hook.checked_path(paths.harness, str(stage))
                builder = hook.load_build_view(self.hashes["build_view"])
                summary = builder.generate(export, None, "auto", out_dir=stage, insights_dir=Path(paths.out),
                                           index_sha256=self.hashes["index"])
                generated = payload(read_bytes(paths, stage / "view-data.js"))
                generated["delivery"] = {**generated.get("delivery", {}), "export_sha256": before,
                                         "web_binding_state": state, "display_ready": True}
                (stage / "view-data.js").write_text("window.LGAX_VIEW = " + json.dumps(generated, ensure_ascii=False, allow_nan=False) + ";\n", encoding="utf-8")
                check = diagnose(paths, self.hashes, export, stage)
                if check["view_shape"] != "valid" or not check["index_matches_installed"] or check["current_binding"] not in ("matched_current", "request_only"):
                    raise ValueError("generated_sidecar_invalid")
                newest = hook.newest_export(paths)
                if digest(read_bytes(paths, export)) != before or newest is None or hook.export_key(newest) != key:
                    return {"status": "superseded", "display_verified": False}
                paths.validate()
                for name in ("index.html", "view-data.js"):
                    os.replace(stage / name, Path(paths.out) / name)
                current.update(last_key=key, built_key=key, last_export=export.name,
                               built_at=time_stamp(), web_delivery=state, web_signature=hook.web_signature(paths),
                               focus=summary["focus"], warnings=summary["warnings"], insights=summary["insights"])
                current.pop("failed_key", None)
                current.pop("baseline", None)
                hook.write_state(paths, current)
            business = f"{self.engine}:{body['session_id']}"
            session = f"{self.engine}:{self.open_scope}"
            if not allow_open:
                opened = {"open_requested": False, "open_status": "not_requested"}
            elif body["session_id"] == self.legacy_business:
                opened = {"open_requested": False, "open_status": "legacy_attempt_unknown"}
            else:
                opened = hook.request_browser(paths, session, business, self.opener)
            states = [t["state"].get("status") for t in body["turns"][-1:]] or [
                (r.get("response") or {}).get("status") for r in body.get("requests", [])]
            workflows = [r["workflow"] for r in body.get("requests", []) if isinstance(r.get("workflow"), dict)
                         and r["workflow"].get("tracked")]
            return {"status": "ready", "export": export.name, "binding": state, "business_status": states,
                    "local_workflow_finished": all(w.get("finished_at") for w in workflows) if workflows else None,
                    "native_end_observed": False, **opened, "display_verified": False}
        finally:
            try:
                if stage is not None:
                    # No recursive deletion; remove only known, guarded temporary files.
                    for name in ("index.html", "view-data.js"):
                        p = stage / name
                        hook.checked_path(paths.harness, str(p))
                        if p.exists():
                            p.unlink()
                    stage.rmdir()
            finally:
                lock.release()


def time_stamp():
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def native_completion(paths, body):
    """Match sanitized native observations to this business request, never by time.

    The observer records identifiers/events only. No raw conversation or command
    is read here; a quiet or disconnected observer is not an AI failure.
    """
    records = Path(paths.harness) / "runtime-data/agent-office/events.jsonl"
    if not records.is_file():
        return {"status": "waiting_native_completion"}
    try:
        raw = read_bytes(paths, records)
        if raw and not raw.endswith(b"\n"):
            return {"status": "waiting_native_completion"}
        events = [json.loads(line) for line in raw.splitlines()[-1500:] if line.strip()]
        if any(not isinstance(e, dict) for e in events):
            return {"status": "waiting_native_completion"}
        events = [e for e in events if e.get("v") == 1]
        main = lambda e: e.get("actor") == "main" and not e.get("agent_id")
        anchors = [i for i,e in enumerate(events) if main(e) and e.get("kind") == "request"]
        if not anchors:
            return {"status": "waiting_native_completion"}
        chosen = events[anchors[-1]]
        session = chosen.get("session")
        prompts, children, selected = {chosen.get("prompt_id")}, set(), []
        open_children = set()
        for event in events[anchors[-1]:]:
            if event.get("session") != session:
                continue
            detail = event.get("detail") or {}
            if not isinstance(detail, dict):
                continue
            if (event.get("kind") == "subagent" and event.get("phase") in ("end", "fail")
                    and event.get("agent_id") not in children):
                # A lifecycle tail without an observed dispatch/start cannot
                # establish a continuation of this request merely by sharing its prompt id.
                continue
            if (main(event) and event.get("kind") in ("handback_delivered", "notification")
                    and detail.get("from_agent_id") in children):
                prompts.add(event.get("prompt_id"))
            linked = event.get("prompt_id") in prompts or event.get("agent_id") in children
            if not linked:
                continue
            if event.get("kind") == "delegate" and detail.get("launched_agent_id"):
                children.add(detail["launched_agent_id"])
                open_children.add(detail["launched_agent_id"])
            if event.get("kind") == "subagent" and event.get("phase") == "start" and event.get("agent_id"):
                children.add(event["agent_id"])
                open_children.add(event["agent_id"])
            if event.get("kind") == "subagent" and event.get("phase") in ("end", "fail"):
                open_children.discard(event.get("agent_id"))
            if event.get("kind") in ("handback", "handback_delivered", "notification"):
                open_children.discard(detail.get("from_agent_id"))
            selected.append(event)
        current = (body.get("turns") or [{}])[-1]
        expected = current.get("web_binding") or {}
        keys = ("session_id", "turn_id", "request_key")
        if not all(isinstance(expected.get(k), str) and expected[k] for k in keys):
            return {"status": "waiting_native_completion"}
        matches = [e for e in selected if main(e) and all(
            ((e.get("detail") or {}).get("business_binding") or {}).get(k) == expected[k] for k in keys)]
        if not matches:
            return {"status": "waiting_native_completion"}
        terminal = [e for e in selected if main(e) and e.get("kind") in ("turn_cancelled", "turn_end")]
        if any(e.get("kind") == "turn_cancelled" for e in terminal):
            return {"status": "native_cancelled"}
        if not terminal or terminal[-1].get("kind") != "turn_end":
            return {"status": "waiting_native_completion"}
        if open_children:
            return {"status": "waiting_native_completion"}
        final_index = max(i for i,e in enumerate(selected) if e is terminal[-1])
        if any((main(e) and e.get("kind") in ("request", "handback_delivered", "notification"))
               or (e.get("kind") == "subagent" and e.get("phase") in ("end", "fail"))
               for e in selected[final_index + 1:]):
            return {"status": "waiting_native_completion"}
        end_detail = terminal[-1].get("detail") or {}
        if (end_detail.get("interrupted") is True
                or end_detail.get("turn_status") in ("failed", "cancelled", "interrupted")
                or end_detail.get("response_status") in ("failed", "cancelled", "incomplete", "error")):
            return {"status": "native_failed"}
        return {"status": "native_completed", "native_session": session}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {"status": "waiting_native_completion"}
