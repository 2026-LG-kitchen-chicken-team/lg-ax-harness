"""LG AX agent office - passive Claude Code hook observer.

`office.py install --claude <harness>` copies this file to `<harness>/web/prototypes/agent-office/observe.py` and
registers it as an async command hook (PreToolUse, PostToolUse, PostToolUseFailure, UserPromptSubmit, Stop,
SubagentStart, SubagentStop, SessionStart, SessionEnd) in `.claude/settings.local.json`.

What it does, per hook call:
- reads the hook JSON from stdin and appends ONE small JSON line to `runtime-data/agent-office/events.jsonl`;
- refreshes `runtime-data/agent-office/live.js` (recent events + a short read-only snapshot of product.sqlite) that the
  office page reloads.

What it never does: print to stdout or stderr, exit non-zero, block or change a tool call, call a model or a business
tool, write to product.sqlite, or keep prompt text, command text, tool output, file contents or search queries.
Only names that are already part of the harness (Skill, operation, research role) and the host name of a fetched page
are kept. Where a node comes from a command path the event says so (basis `command_based_mapping`), a loaded SKILL.md
is `instruction_loaded`, and a subagent call seen as a tool call is `observed`. Nothing is inferred from call order.
Standard library only. Errors go to `runtime-data/agent-office/observe-error.log` and nowhere else.
"""
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 1
HERE = Path(__file__).resolve().parent
HARNESS = HERE.parents[2]
OUT = HARNESS / "runtime-data" / "agent-office"
EVENTS = OUT / "events.jsonl"
LIVE = OUT / "live.js"
SNAPSHOT = OUT / "snapshot.json"
LOCK = OUT / ".observe.lock"
ERRORS = OUT / "observe-error.log"
DB = HARNESS / "runtime-data" / "product.sqlite"

MAX_STDIN = 4 * 1024 * 1024        # hook payloads with a large tool_response are read and dropped
MAX_EVENTS_BYTES = 8 * 1024 * 1024  # events.jsonl rolls over to events-<time>.jsonl past this size
LIVE_EVENTS = 600                  # events kept in live.js for the page

# product v0.10.0 inventory (agents/product-planning.md, docs/contracts/product-research-agents.md, skills/manifest.json).
# Node ids match the teammate control room (web/prototypes/control-room/src/catalog.ts) so traces can be shared.
ROLES = {
    "product-official-researcher": "product_official_researcher",
    "product-review-researcher": "product_review_researcher",
    "product-evidence-reviewer": "product_evidence_reviewer",
}
SKILL_OPS = {
    "evidence-retrieval": {"evidence_inventory", "read_evidence_batch", "record_evidence_review", "evidence_coverage", "doctor",
                           "list_models", "open_request", "open_request_bundle", "resolve_request", "resolve_request_bundle",
                           "record_request_research", "current_request", "prepare_planning_input", "retrieve_reviews",
                           "retrieve_product_facts", "select_evidence", "match_product_scope", "set_request_scope_policy",
                           "open_product_workflow", "record_workflow_event", "workflow_status"},
    "web-evidence-collection": {"fetch_web_page", "capture_web_page", "import_web_evidence", "import_web_evidence_bulk",
                                "configure_web_research"},
    "needs-structuring": {"select_evidence", "validate_source_refs"},
    "feature-comparison": {"match_product_scope", "retrieve_product_facts", "select_evidence"},
    "concept-writing": {"validate_constraints", "validate_source_refs"},
    "review-and-revise": {"save_and_export", "prepare_web_result", "deliver_result", "save_reviewed_result", "export_session",
                          "current_request", "get_turn", "record_usage", "cancel_turn", "prepare_review_packet",
                          "verify_review_packet", "validate_result_contract", "review_product_result", "start_turn",
                          "save_result", "begin_invocation", "finish_invocation"},
}
RUN_PY = re.compile(r"skills[\\/]+([a-z0-9-]{1,60})[\\/]+scripts[\\/]+run\.py[\"']?\s+([A-Za-z_]{1,60})")
SKILL_MD = re.compile(r"skills[\\/]+([a-z0-9-]{1,60})[\\/]+SKILL\.md$", re.I)
ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,59}$")
SHELLS = {"Bash", "PowerShell"}
SUBAGENT_TOOLS = {"Task", "Agent"}
WEB_TOOLS = {"WebFetch", "WebSearch"}
PHASE = {"PreToolUse": "start", "PostToolUse": "end", "PostToolUseFailure": "fail"}
FILE_TOOLS = {"Read": "file_path", "Write": "file_path", "Edit": "file_path", "NotebookEdit": "notebook_path",
              "Grep": "path", "Glob": "path"}
# Shell commands are never stored. Only the program names below (first word of each part of the command) are kept,
# plus the harness's own entry points; anything else is "other".
PROGRAMS = {
    "ls", "dir", "cat", "type", "head", "tail", "find", "grep", "rg", "wc", "pwd", "cd", "echo", "mkdir", "cp", "mv", "rm",
    "python", "python3", "py", "uv", "git", "sed", "awk", "jq", "curl", "wget", "sort", "uniq", "node", "npm", "npx",
    "get-childitem", "get-content", "set-location", "test-path", "select-string", "new-item", "remove-item", "copy-item",
    "move-item", "invoke-webrequest", "out-file", "set-content", "get-item", "write-output", "measure-object",
}
HARNESS_SCRIPTS = {"product-doctor.py": "product_doctor"}
SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
# Where a file tool worked, by folder area only (file names are not stored, except a Skill's own SKILL.md).
AREAS = (("runtime-data/exports", "exports"), ("runtime-data/web-evidence", "web_evidence"), ("runtime-data/catalogs", "catalogs"),
         ("runtime-data/deliverables", "deliverables"), ("runtime-data", "runtime"), (".claude/skills", "skills"),
         (".agents/skills", "skills"), ("skills", "skills"), (".claude/agents", "agents"), ("agents", "agents"), ("docs", "docs"),
         ("data", "data"), ("product-tools", "tools"), ("web", "web"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def short(value, limit=120):
    return value[:limit] if isinstance(value, str) else None


TOKEN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
AGENT_FROM = re.compile(r"from=\"([0-9a-f]{8,40})\"")
HANDBACK_TOOL = "SubagentHandback"


def token(value):
    """A short identifier-like value (status, agent type, agent id); anything else is dropped."""
    return value if isinstance(value, str) and TOKEN.match(value) else None


def actor_of(payload: dict) -> str:
    """The acting agent. Claude Code adds agent_id and agent_type to events from inside a subagent; agent_type alone is
    also set for `claude --agent`, so a research role is used only when agent_id is present too."""
    if payload.get("agent_id"):
        role = ROLES.get(payload.get("agent_type") or "")
        if role:
            return role
        return "other_subagent"
    return "main"


def programs_of(command: str) -> list:
    out = []
    for part in SEPARATORS.split(command)[:12]:
        words = part.strip().split()
        while words and ("=" in words[0] and not words[0].startswith("-")):  # VAR=value prefixes
            words = words[1:]
        if not words:
            continue
        name = re.split(r"[\\/]", words[0].strip("\"'&."))[-1].lower()
        name = name[:-4] if name.endswith(".exe") else name
        script = next((HARNESS_SCRIPTS[w.split("/")[-1].split("\\")[-1]] for w in words[1:4]
                       if w.split("/")[-1].split("\\")[-1] in HARNESS_SCRIPTS), None)
        out.append(script or (name if name in PROGRAMS else "other"))
    return list(dict.fromkeys(out))[:6]


def area_of(path: str, cwd) -> dict:
    """Folder area of a file tool's path relative to the harness; no file names."""
    if not path:
        return {}
    try:
        target = Path(path)
        if not target.is_absolute():
            target = Path(cwd if isinstance(cwd, str) and cwd else HARNESS) / target
        rel = os.path.relpath(os.path.normcase(os.path.abspath(target)), os.path.normcase(os.path.abspath(HARNESS)))
    except (ValueError, OSError):
        return {"area": "outside"}
    rel = rel.replace("\\", "/")
    if rel == ".":
        return {"area": "harness"}
    if rel.startswith(".."):
        return {"area": "outside"}
    for prefix, name in AREAS:
        if rel == prefix or rel.startswith(prefix + "/"):
            found = {"area": name}
            if name == "skills":
                skill = rel[len(prefix) + 1:].split("/")[0]
                if skill in SKILL_OPS:
                    found["skill"] = skill
            return found
    return {"area": "harness"}


def classify(payload: dict) -> dict:
    """One hook payload -> one event. Only harness names, ids, times and host names are kept."""
    hook = payload.get("hook_event_name") or ""
    tool = payload.get("tool_name") if isinstance(payload.get("tool_name"), str) else None
    tin = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    actor = actor_of(payload)
    event = {
        "v": VERSION, "id": uuid.uuid4().hex[:16], "ts": now(), "ts_basis": "hook_received", "src": "claude", "hook": hook,
        "session": short(payload.get("session_id"), 80), "prompt_id": short(payload.get("prompt_id"), 80),
        "agent_id": short(payload.get("agent_id"), 80),
        "actor": actor, "tool": short(tool, 60), "call": short(payload.get("tool_use_id"), 80),
        "kind": "lifecycle", "node": actor, "op": None, "ops": [], "phase": "point", "basis": "observed", "detail": {},
        # field names only (never values), to confirm what this Claude Code version sends
        "keys": sorted(k for k in payload if isinstance(k, str))[:40], "input_keys": sorted(k for k in tin if isinstance(k, str))[:20],
    }
    if isinstance(payload.get("duration_ms"), (int, float)):
        event["detail"]["duration_ms"] = round(float(payload["duration_ms"]), 1)
    if payload.get("is_interrupt") is True:
        event["detail"]["interrupted"] = True
    if hook in PHASE:
        event["phase"] = PHASE[hook]
        event["kind"] = "tool"
        if tool in SUBAGENT_TOOLS:
            role = ROLES.get(tin.get("subagent_type") or "")
            event.update(kind="delegate", node=role or "unknown_subagent")
            if not role:
                event["detail"]["subagent_type"] = token(tin.get("subagent_type"))
            response = payload.get("tool_response")
            if hook == "PostToolUse" and isinstance(response, dict):
                # A background subagent returns at once with status async_launched; its real return comes later
                # (SubagentHandback, then SubagentStop with the same agent id).
                event["detail"]["response_status"] = token(response.get("status"))
                if response.get("isAsync") is True:
                    event["detail"]["background"] = True
                event["detail"]["launched_agent_id"] = token(response.get("agentId"))
        elif tool == HANDBACK_TOOL:
            event.update(kind="handback", node=actor)
        elif tool == "Skill":
            name = tin.get("skill") or tin.get("name") or tin.get("command")
            name = name if isinstance(name, str) else ""
            name = name.split(":")[-1].strip().lstrip("/")
            event.update(kind="skill_load", node=name if name in SKILL_OPS else "unknown_skill", basis="instruction_loaded")
        elif tool in SHELLS:
            command = tin.get("command") if isinstance(tin.get("command"), str) else ""
            pairs = [(s, o) for s, o in RUN_PY.findall(command) if s in SKILL_OPS]
            if pairs:
                skill, op = pairs[0]
                event.update(kind="skill_op", node=skill, op=op if op in SKILL_OPS[skill] else "unknown_operation",
                             basis="command_based_mapping",
                             ops=[{"skill": s, "op": o if o in SKILL_OPS[s] else "unknown_operation"} for s, o in pairs[:8]])
                if hook == "PostToolUse":
                    failed = tool_error(payload.get("tool_response"))
                    if failed:
                        event["phase"] = "fail"
                        event["detail"]["error"] = failed
            else:
                event["kind"] = "shell"
                event["detail"]["programs"] = programs_of(command)
        elif tool in FILE_TOOLS:
            path = tin.get(FILE_TOOLS[tool]) if isinstance(tin.get(FILE_TOOLS[tool]), str) else ""
            match = SKILL_MD.search(path.replace("\\", "/"))
            if tool == "Read" and match and match.group(1) in SKILL_OPS:
                event.update(kind="skill_load", node=match.group(1), basis="instruction_loaded")
            else:
                event["kind"] = "file"
                event["detail"].update(area_of(path, payload.get("cwd")))
        elif tool in WEB_TOOLS:
            event["kind"] = "web"
            if tool == "WebFetch":
                host = urlsplit(tin.get("url") if isinstance(tin.get("url"), str) else "").hostname
                event["detail"]["host"] = short(host, 120)
    elif hook == "UserPromptSubmit":
        # Claude Code delivers a subagent's result and task notices as user turns. They are told apart by their
        # opening marker only; no prompt text is kept.
        prompt = payload.get("prompt") if isinstance(payload.get("prompt"), str) else ""
        head = prompt.lstrip()[:200]
        if head.startswith("Another Claude session sent a message:") or head.startswith("<agent-message"):
            found = AGENT_FROM.search(head)
            event.update(kind="handback_delivered", node="main", actor="main")
            if found:
                event["detail"]["from_agent_id"] = found.group(1)
        elif head.startswith("<task-notification>"):
            event.update(kind="notification", node="main", actor="main")
        else:
            event.update(kind="request", node="main", actor="main")
    elif hook in ("SubagentStart", "SubagentStop"):
        role = ROLES.get(payload.get("agent_type") or "") or "other_subagent"
        event.update(kind="subagent", node=role, actor=role, phase="start" if hook == "SubagentStart" else "end")
        if role == "other_subagent":
            event["detail"]["agent_type"] = token(payload.get("agent_type"))
    elif hook == "Stop":
        event.update(kind="turn_end", node="main", actor="main")
    elif hook in ("SessionStart", "SessionEnd"):
        event.update(kind="session", node="main", actor="main", phase="start" if hook == "SessionStart" else "end")
        source = payload.get("source") or payload.get("reason")
        if isinstance(source, str) and ERROR_CODE.match(source):
            event["detail"]["reason"] = source
    return event


def tool_error(response):
    """A product-tools call prints one JSON object; keep only its error code when it says ok=false."""
    text = None
    if isinstance(response, dict):
        text = response.get("stdout") if isinstance(response.get("stdout"), str) else None
    elif isinstance(response, str):
        text = response
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        data = json.loads(text[start:])
    except ValueError:
        return None
    if isinstance(data, dict) and data.get("ok") is False:
        code = data.get("error") or data.get("code")
        if isinstance(code, dict):
            code = code.get("code")
        return code if isinstance(code, str) and ERROR_CODE.match(code) else "failed"
    return None


# --- files ---------------------------------------------------------------------------------------------------------
class Lock:
    """Cross-process lock on a side file (async hooks can run at the same time)."""

    def __init__(self, path: Path, wait=3.0):
        self.path, self.wait, self.fh = path, wait, None

    def __enter__(self):
        self.fh = open(self.path, "a+b")
        deadline = time.monotonic() + self.wait
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    self.fh.seek(0)
                    msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError("agent-office lock busy")
                time.sleep(0.02)

    def __exit__(self, *exc):
        try:
            if os.name == "nt":
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()


def replace(tmp: Path, path: Path):
    """os.replace with the short retry Windows sometimes needs (WinError 5 while a reader has the file open)."""
    for delay in (0, 0.05, 0.1, 0.2):
        time.sleep(delay)
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            continue
    os.replace(tmp, path)


def write_text(path: Path, text: str):
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    replace(tmp, path)


def append_event(event: dict):
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    if EVENTS.is_file() and EVENTS.stat().st_size > MAX_EVENTS_BYTES:
        os.replace(EVENTS, OUT / f"events-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.jsonl")
    with open(EVENTS, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)


def recent_events(limit=LIVE_EVENTS) -> list:
    if not EVENTS.is_file():
        return []
    with open(EVENTS, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - 512 * 1024))
        lines = fh.read().decode("utf-8", errors="replace").splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


# --- product.sqlite, read only and short ------------------------------------------------------------------------------
def host_of(url) -> str | None:
    return short(urlsplit(url).hostname, 120) if isinstance(url, str) else None


def snapshot_db() -> dict:
    """A short read-only look at the harness database. Never creates or changes it; a busy database is skipped.

    product-tools writes with BEGIN IMMEDIATE and a 5 s timeout on a rollback journal, so this reader opens the file
    read-only, waits at most 0.2 s and closes at once."""
    if not DB.is_file():
        return {"available": False, "reason": "no_database"}
    uri = DB.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=0.2, isolation_level=None)
    try:
        con.execute("PRAGMA query_only=1")
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        snap = {"available": True, "read_at": now(), "workflow": None, "workflow_events": [], "request": None, "turn": None,
                "results": 0, "evidence_delivered": None, "evidence_reviews": None, "cancelled": False}
        if "product_workflows" in tables:
            row = con.execute("SELECT research_id, started_at, budget_seconds, research_stopped_at, finished_at "
                              "FROM product_workflows ORDER BY started_at DESC LIMIT 1").fetchone()
            if row:
                snap["workflow"] = {"research_id": row[0], "started_at": row[1], "budget_seconds": row[2],
                                    "research_stopped_at": row[3], "finished_at": row[4]}
                if "product_workflow_events" in tables:
                    for kind, at, raw in con.execute(
                            "SELECT kind, observed_at, payload FROM product_workflow_events WHERE research_id=? "
                            "ORDER BY observed_at, rowid", (row[0],)).fetchall()[-80:]:
                        snap["workflow_events"].append({"kind": kind, "observed_at": at, **workflow_detail(kind, raw)})
        if "conversation_requests" in tables:
            row = con.execute("SELECT payload, turn_id, response FROM conversation_requests ORDER BY rowid DESC LIMIT 1").fetchone()
            if row:
                payload = loads(row[0])
                response = loads(row[2])
                snap["request"] = {"question": short(payload.get("question"), 300), "turn_id": row[1],
                                   "status": short(response.get("status"), 40) if isinstance(response, dict) else None}
        if "turns" in tables:
            row = con.execute("SELECT turn_id, status, revision_count, result_version, valid, created_at FROM turns "
                              "ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                snap["turn"] = {"turn_id": row[0], "status": row[1], "revision_count": row[2], "result_version": row[3],
                                "valid": bool(row[4]), "created_at": row[5]}
                if "results" in tables:
                    snap["results"] = con.execute("SELECT COUNT(*) FROM results WHERE turn_id=?", (row[0],)).fetchone()[0]
                if "evidence_deliveries" in tables:
                    snap["evidence_delivered"] = con.execute(
                        "SELECT COUNT(DISTINCT source_id) FROM evidence_deliveries WHERE turn_id=?", (row[0],)).fetchone()[0]
                if "evidence_reviews" in tables:
                    snap["evidence_reviews"] = con.execute(
                        "SELECT COUNT(*) FROM evidence_reviews WHERE turn_id=?", (row[0],)).fetchone()[0]
                if "cancellations" in tables:
                    snap["cancelled"] = con.execute("SELECT 1 FROM cancellations WHERE turn_id=?", (row[0],)).fetchone() is not None
        return snap
    finally:
        con.close()


def loads(raw):
    try:
        value = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def workflow_detail(kind: str, raw) -> dict:
    data = loads(raw).get("data")
    data = data if isinstance(data, dict) else {}
    if kind == "research_plan":
        return {"product": short(data.get("product_name"), 120)}
    if kind == "source_scan":
        reviews = data.get("reviews")
        return {"host": host_of(data.get("source_url")), "page": short(data.get("page_label"), 80),
                "status": short(data.get("status"), 20), "reviews": len(reviews) if isinstance(reviews, list) else None,
                "source_type": short(data.get("source_type"), 40)}
    if kind == "research_stop":
        return {"code": short(data.get("code"), 40)}
    if kind == "analysis_scope":
        ids = data.get("source_ids")
        return {"sources": len(ids) if isinstance(ids, list) else None}
    if kind == "finish":
        return {"layout_review": short(data.get("layout_review"), 20)}
    return {}


REFRESH_DB = {"PostToolUse", "PostToolUseFailure", "Stop", "SubagentStop", "SessionStart", "UserPromptSubmit"}


def refresh_live(event: dict):
    snap = None
    if event["hook"] in REFRESH_DB and (event["kind"] in ("skill_op", "delegate", "subagent", "turn_end", "session", "request")):
        try:
            snap = snapshot_db()
        except sqlite3.Error as exc:  # busy or locked: keep the previous snapshot and say so
            snap = None
            note_error(f"snapshot skipped: {type(exc).__name__}")
        if snap is not None:
            write_text(SNAPSHOT, json.dumps(snap, ensure_ascii=False))
    if snap is None and SNAPSHOT.is_file():
        snap = loads(SNAPSHOT.read_text(encoding="utf-8"))
    live = {"kind": "lgax-agent-office-live", "version": VERSION, "written_at": now(), "harness_version": harness_version(),
            "events": recent_events(), "db": snap}
    write_text(LIVE, "/* agent-office observe.py writes this file; do not edit. */\nwindow.LGAX_OFFICE_LIVE = "
               + json.dumps(live, ensure_ascii=False) + ";\n")


def harness_version():
    try:
        data = json.loads((HARNESS / "product-install.json").read_text(encoding="utf-8"))
        return short(data.get("version") or data.get("source_version") or data.get("format"), 60)
    except (OSError, ValueError):
        return None


def note_error(message: str):
    try:
        with open(ERRORS, "a", encoding="utf-8") as fh:
            fh.write(f"{now()} {message}\n")
    except OSError:
        pass


def safe_dirs() -> bool:
    """Refuse to write through a symlink or junction (a sandboxed process could plant one)."""
    for path in (HARNESS / "runtime-data", OUT):
        try:
            if path.is_symlink() or (os.name == "nt" and getattr(os.lstat(path), "st_file_attributes", 0) & 0x400):
                return False
        except FileNotFoundError:
            continue
    return True


def main(argv=None) -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_STDIN + 1)
        if not safe_dirs():
            return 0
        OUT.mkdir(parents=True, exist_ok=True)
        if len(raw) > MAX_STDIN:
            note_error("hook payload larger than the limit; recorded without tool fields")
            payload = {}
        else:
            payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
        event = classify(payload)
        with Lock(LOCK):
            append_event(event)
            refresh_live(event)
    except Exception as exc:  # the hook must never disturb the session
        try:
            if safe_dirs():
                OUT.mkdir(parents=True, exist_ok=True)
                note_error(f"{type(exc).__name__}: {str(exc)[:300]}")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    devnull = open(os.devnull, "w")
    sys.stdout = sys.stderr = devnull
    try:
        main(sys.argv)
    finally:
        os._exit(0)
