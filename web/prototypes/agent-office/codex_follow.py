"""LG AX agent office - follow a Codex session log and write the same office records as the Claude hook.

Codex keeps one rollout JSONL per thread (main session and each spawned agent) under CODEX_HOME/sessions/YYYY/MM/DD/.
This reader turns the records of ONE selected main session (and the agent threads whose session_meta names it as the
parent) into office events in <harness>/runtime-data/agent-office/events.jsonl and live.js, the files the page reads.

It follows the team observer's rules (observer/README.md): it reads only a selected session (an explicit file, or with
--latest the newest main session whose own session_meta says it ran in this harness folder), checks that identity
before using any record, never interprets an unfinished last line, never starts, stops or signals Codex and calls no
model. Codex 0.162 runs commands inside a code-mode `exec` tool; the team observer does not look inside it, so this
reader also uses the per-command records Codex writes (item_completed CommandExecution, web search, MCP, file change).

Kept: times (from the log), thread/turn/call ids, tool kind, Skill and operation names from `skills/<skill>/scripts/
run.py <op>` command paths, program names from a fixed list, folder areas, web host names, exit status and the save
outcome (accepted, reason code, turn status). Not kept: prompts, messages, reasoning, commands, outputs, search
queries, URL paths, file names or contents. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import observe as ob  # noqa: E402  (same folder; shares the mapping rules and the writers)

ROLE_NAMES = {**ob.ROLES, **{v: v for v in ob.ROLES.values()}}  # Codex agent files use product_review_researcher
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
READ_PROGRAMS = {"cat", "type", "get-content", "head", "tail", "sed", "less", "more"}
PARSED_TOOL = {"read": "Read", "list_files": "Glob", "search": "Grep"}
MAX_LINE = 1024 * 1024
MAX_FILE = 256 * 1024 * 1024


class FollowError(Exception):
    pass


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))


def iso(value) -> str | None:
    """Log times as the office's UTC millisecond strings: epoch milliseconds or an ISO string with a zone."""
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            stamp = datetime.fromtimestamp(value / 1000, timezone.utc)
        elif isinstance(value, str) and len(value) <= 40:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return None
        else:
            return None
    except (ValueError, OverflowError, OSError):
        return None
    return stamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def uuid_of(value) -> str | None:
    return value.lower() if isinstance(value, str) and UUID.match(value.lower()) else None


def first_meta(path: Path) -> dict | None:
    """Identity of a rollout file from its first session_meta record: id, cwd, parent and agent role only."""
    try:
        with open(path, "rb") as fh:
            for _ in range(5):
                line = fh.readline(MAX_LINE + 1)
                if not line or len(line) > MAX_LINE:
                    return None
                try:
                    record = json.loads(line)
                except ValueError:
                    return None
                if isinstance(record, dict) and record.get("type") == "session_meta":
                    return meta_of(record)
    except OSError:
        return None
    return None


def meta_of(record: dict) -> dict | None:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    sid = uuid_of(payload.get("id"))
    if not sid:
        return None
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    sub = source.get("subagent") if isinstance(source.get("subagent"), dict) else {}
    spawn = sub.get("thread_spawn") if isinstance(sub.get("thread_spawn"), dict) else {}
    parent = uuid_of(payload.get("parent_thread_id")) or uuid_of(spawn.get("parent_thread_id"))
    role = payload.get("agent_role") or spawn.get("agent_role") or spawn.get("agent_type")
    return {"id": sid, "cwd": payload.get("cwd") if isinstance(payload.get("cwd"), str) else None, "parent": parent,
            "role": ob.token(role), "ts": iso(record.get("timestamp")) or iso(payload.get("timestamp")),
            "cli_version": ob.token(payload.get("cli_version")), "subagent": bool(sub) or bool(parent)}


def same_folder(a, b) -> bool:
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except (TypeError, ValueError):
        return False


def day_folders(since: datetime, until: datetime | None = None) -> list[Path]:
    """sessions/YYYY/MM/DD folders from one day before `since` to one day after `until` (local and UTC dates differ)."""
    until = until or datetime.now(timezone.utc)
    root = codex_home() / "sessions"
    day, out = (since - timedelta(days=1)).date(), []
    while day <= (until + timedelta(days=1)).date():
        folder = root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
        if folder.is_dir():
            out.append(folder)
        day += timedelta(days=1)
    return out


def rollouts(folders) -> list[Path]:
    files = []
    for folder in folders:
        try:
            files += [p for p in folder.iterdir() if p.name.startswith("rollout-") and p.suffix == ".jsonl" and p.is_file()]
        except OSError:
            continue
    return sorted(files, key=lambda p: p.name)


def list_sessions(harness: Path, days=3) -> list[dict]:
    """Main Codex sessions recorded in this harness folder in the last few days (newest last)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    found, children = [], {}
    for path in rollouts(day_folders(since)):
        meta = first_meta(path)
        if not meta:
            continue
        if meta["parent"]:
            children[meta["parent"]] = children.get(meta["parent"], 0) + 1
        elif meta["cwd"] and same_folder(meta["cwd"], harness):
            found.append({**meta, "path": str(path)})
    for item in found:
        item["agents"] = children.get(item["id"], 0)
    return found


def wait_for_new(harness: Path, max_seconds: float, poll=1.0) -> tuple[Path, dict]:
    """Wait for a main session in this folder that starts after now (start this, then open Codex and ask)."""
    known = {s["id"] for s in list_sessions(harness, days=1)}
    deadline = time.monotonic() + max_seconds
    while time.monotonic() < deadline:
        fresh = [s for s in list_sessions(harness, days=1) if s["id"] not in known]
        if fresh:
            return Path(fresh[-1]["path"]), fresh[-1]
        time.sleep(poll)
    raise FollowError("기다리는 동안 이 하네스 폴더에서 새 Codex 세션이 시작되지 않았습니다.")


def select(harness: Path, rollout: Path | None, latest: bool) -> tuple[Path, dict]:
    if rollout:
        meta = first_meta(rollout)
        if not meta:
            raise FollowError(f"Codex 세션 기록(rollout)의 첫 줄에서 session_meta를 찾지 못했습니다: {rollout}")
        if meta["parent"]:
            raise FollowError("하위 에이전트의 기록입니다. 메인 세션의 rollout 파일을 고르세요.")
        if not meta["cwd"] or not same_folder(meta["cwd"], harness):
            raise FollowError(f"이 Codex 세션은 다른 폴더에서 실행됐습니다({meta['cwd']}). 하네스 폴더에서 연 세션을 고르세요.")
        return rollout, meta
    if latest:
        sessions = list_sessions(harness)
        if not sessions:
            raise FollowError(f"최근 3일 동안 이 하네스 폴더({harness})에서 연 Codex 세션 기록이 없습니다.")
        newest = sessions[-1]
        return Path(newest["path"]), newest
    raise FollowError("--rollout <파일> 또는 --latest 중 하나를 정하세요.")


class Reader:
    """Bounded incremental JSONL reader. An unfinished last line waits for its newline (same rule as the observer)."""

    def __init__(self, path: Path, offset=0, seq=0):
        self.path, self.offset, self.seq, self.pending, self.errors = path, offset, seq, b"", {}

    def poll(self):
        out = []
        try:
            size = self.path.stat().st_size
            if size < self.offset:
                self.errors["truncated"] = self.errors.get("truncated", 0) + 1
                return out
            with open(self.path, "rb") as fh:
                fh.seek(self.offset)
                while self.offset < min(size, MAX_FILE):
                    chunk = fh.read(65536)
                    if not chunk:
                        break
                    self.offset += len(chunk)
                    self.pending += chunk
                    while b"\n" in self.pending:
                        line, self.pending = self.pending.split(b"\n", 1)
                        self.seq += 1
                        if len(line) > MAX_LINE:
                            continue
                        try:
                            value = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(value, dict):
                            out.append((self.seq, value))
                    if len(self.pending) > MAX_LINE:
                        self.pending = b""
        except OSError:
            self.errors["unavailable"] = self.errors.get("unavailable", 0) + 1
        return out

    @property
    def done_offset(self):
        """Offset of the last complete line (resume point)."""
        return self.offset - len(self.pending)


def command_text(item: dict) -> str:
    command = item.get("command")
    if isinstance(command, list):
        return " ".join(c for c in command if isinstance(c, str))[:20000]
    return command[:20000] if isinstance(command, str) else ""


def classify_command(item: dict, cwd) -> dict:
    """What a Codex shell command was, by the same rules as the Claude hook (run.py path, SKILL.md, programs, area)."""
    text = command_text(item)
    pairs = [(s, o) for s, o in ob.RUN_PY.findall(text) if s in ob.SKILL_OPS]
    if pairs:
        skill, op = pairs[0]
        op = op if op in ob.CLI_OPS else "unknown_operation"
        found = {"kind": "skill_op", "node": skill, "op": op, "basis": "command_based_mapping",
                 "ops": [{"skill": s, "op": o if o in ob.CLI_OPS else "unknown_operation"} for s, o in pairs[:8]], "detail": {}}
        if op in ob.CLI_OPS and op not in ob.SKILL_OPS[skill]:
            found["detail"]["other_skill_operation"] = True
        return found
    parsed = [p for p in item.get("parsed_cmd") or [] if isinstance(p, dict)]
    paths = [p.get("path") for p in parsed if isinstance(p.get("path"), str)]
    programs = ob.programs_of(text) if text else []
    for path in paths or re.findall(r"[^\s\"']*SKILL\.md", text, re.I):
        match = ob.SKILL_MD.search(path.replace("\\", "/"))
        if match and match.group(1) in ob.SKILL_OPS and (any(p.get("type") == "read" for p in parsed) or READ_PROGRAMS & set(programs)):
            return {"kind": "skill_load", "node": match.group(1), "basis": "instruction_loaded", "detail": {}}
    if parsed and all(p.get("type") in PARSED_TOOL for p in parsed):
        return {"kind": "file", "tool": PARSED_TOOL[parsed[0]["type"]], "basis": "observed",
                "detail": ob.area_of(paths[0], cwd) if paths else {}}
    return {"kind": "shell", "basis": "observed", "detail": {"programs": programs}}


def duration_ms(item: dict, start, end):
    d = item.get("duration")
    if isinstance(d, dict) and isinstance(d.get("secs"), int):
        return round(d["secs"] * 1000 + (d.get("nanos") or 0) / 1e6, 1)
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return float(end - start)
    return None


class Thread:
    """One rollout file: the main session or one spawned agent thread."""

    def __init__(self, path: Path, meta: dict, main_id: str, offset=0, seq=0):
        self.path, self.meta, self.main_id = path, meta, main_id
        self.child = meta["id"] != main_id
        role = ROLE_NAMES.get(meta.get("role") or "")
        self.actor = (role or "other_subagent") if self.child else "main"
        self.agent_id = meta["id"] if self.child else None
        self.reader = Reader(path, offset, seq)
        self.verified = offset > 0  # identity was checked when this offset was saved
        self.turn = None
        self.cwd = meta.get("cwd")
        self.finished = False
        self.calls = {}  # call id -> tool name, so the end record names the same tool

    def event(self, key, hook, kind, ts, **fields):
        base = {"v": ob.VERSION, "id": hashlib.sha256(f"{self.meta['id']}:{key}:{hook}".encode()).hexdigest()[:16],
                "ts": ts or ob.now(), "ts_basis": "codex_log" if ts else "reader_received", "src": "codex", "hook": hook,
                "session": self.main_id, "prompt_id": self.turn, "agent_id": self.agent_id, "actor": self.actor,
                "tool": None, "call": None, "kind": kind, "node": self.actor, "op": None, "ops": [],
                "phase": "point", "basis": "observed", "detail": {}, "keys": [], "input_keys": []}
        base.update(fields)
        return base

    def poll(self) -> list[dict]:
        out = []
        for seq, record in self.reader.poll():
            if record.get("type") == "session_meta":
                meta = meta_of(record)
                self.verified = bool(meta and meta["id"] == self.meta["id"])
                if self.verified:
                    out.append(self.event("session", "SubagentStart" if self.child else "SessionStart",
                                          "subagent" if self.child else "session", meta["ts"], phase="start",
                                          detail={} if self.child else {"reason": "codex"}))
                continue
            if not self.verified:
                continue  # never use records before the selected identity is confirmed
            out += self.records(seq, record)
        return out

    def records(self, seq, record) -> list[dict]:
        kind = record.get("type")
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        ptype = payload.get("type")
        ts = iso(record.get("timestamp"))
        # A resumed follower may begin after task_started. Each public wrapped
        # item still carries its real native turn, so retain that identity.
        if kind == "event_msg" and isinstance(payload.get("turn_id"), str):
            self.turn = ob.short(payload["turn_id"], 80)
        if kind == "event_msg" and ptype == "task_started":
            self.turn = ob.short(payload.get("turn_id"), 80)
            self.finished = False
            return []
        if kind == "event_msg" and ptype in ("task_complete", "turn_aborted"):
            if self.child:
                self.finished = True
                return [self.event(f"end:{seq}", "SubagentStop", "subagent", ts, phase="end",
                                   detail={"reason": ptype})]
            self.finished = True
            return [self.event(f"end:{seq}", "Stop", "turn_cancelled" if ptype == "turn_aborted" else "turn_end", ts,
                               detail={"reason": ptype, "interrupted": True} if ptype == "turn_aborted" else {})]
        if kind == "event_msg" and ptype == "item_completed" and isinstance(payload.get("item"), dict):
            return self.item(payload, payload["item"], ts)
        if kind == "response_item" and ptype in ("custom_tool_call", "function_call"):
            name = payload.get("name") if isinstance(payload.get("name"), str) else ptype
            call = ob.short(payload.get("call_id"), 80)
            fields = {"tool": ob.short(name, 60), "call": call, "kind": "tool", "phase": "start"}
            if call:
                self.calls[call] = fields["tool"]
                if len(self.calls) > 2000:
                    self.calls.pop(next(iter(self.calls)))
            if "spawn" in name and ptype == "function_call":
                fields.update(self.spawn_fields(payload))
            return [self.event(f"call:{call or seq}", "PreToolUse", fields.pop("kind"), ts, **fields)]
        if kind == "response_item" and ptype in ("custom_tool_call_output", "function_call_output"):
            call = ob.short(payload.get("call_id"), 80)
            return [self.event(f"call:{call or seq}", "PostToolUse", "tool", ts, tool=self.calls.get(call), call=call, phase="end")]
        return []

    def spawn_fields(self, payload) -> dict:
        try:
            args = json.loads(payload.get("arguments")) if isinstance(payload.get("arguments"), str) else {}
        except ValueError:
            args = {}
        role = ROLE_NAMES.get((args or {}).get("agent_type") or (args or {}).get("agent_role") or "") if isinstance(args, dict) else None
        return {"kind": "delegate", "node": role or "unknown_subagent", "detail": {"background": True}}

    def item(self, wrapper: dict, item: dict, ts) -> list[dict]:
        itype = item.get("type")
        start, end = wrapper.get("started_at_ms"), wrapper.get("completed_at_ms")
        t0, t1 = iso(start) or ts, iso(end) or ts
        key = f"item:{ob.short(item.get('id'), 80) or t1}"
        call = ob.short(item.get("id"), 80)
        if itype == "UserMessage":
            if self.child:
                return []
            return [self.event(key, "UserPromptSubmit", "request", t0, node="main")]
        if itype == "CommandExecution":
            found = classify_command(item, self.cwd)
            tool = found.pop("tool", "shell")
            failed = item.get("status") in ("failed", "cancelled") or (isinstance(item.get("exit_code"), int) and item["exit_code"] != 0)
            fields = {"tool": tool, "call": call, "node": found.get("node", self.actor), "op": found.get("op"),
                      "ops": found.get("ops", []), "basis": found["basis"]}
            begin = self.event(key, "PreToolUse", found["kind"], t0, phase="start", detail=dict(found["detail"]), **fields)
            detail = dict(found["detail"])
            ms = duration_ms(item, start, end)
            if ms is not None:
                detail["duration_ms"] = ms
            stdout = item.get("stdout") if isinstance(item.get("stdout"), str) else item.get("aggregated_output")
            if found["kind"] == "skill_op":
                code = ob.tool_error(stdout)
                if code:
                    failed, detail["error"] = True, code
                elif not failed and fields["op"] in ob.SAVE_OPS:
                    detail.update(ob.save_outcome(stdout))
            # SDK/helper calls also return real public business metadata. Keep
            # their shell classification; identifiers do not certify a Skill.
            if not failed:
                detail.update(ob.business_binding(stdout))
            if failed and isinstance(item.get("exit_code"), int) and "error" not in detail:
                detail["exit_code"] = item["exit_code"]
            finish = self.event(key, "PostToolUseFailure" if failed else "PostToolUse", found["kind"], t1,
                                phase="fail" if failed else "end", detail=detail, **fields)
            return [begin, finish]
        if itype == "Extension" and item.get("kind") == "web.search":
            action = item.get("action") if isinstance(item.get("action"), dict) else {}
            host = ob.host_of(action.get("url")) if action.get("type") == "openPage" else None
            tool = "WebFetch" if host else "WebSearch"
            detail = {"host": host} if host else {}
            return [self.event(key, "PreToolUse", "web", t0, tool=tool, call=call, phase="start", detail=dict(detail)),
                    self.event(key, "PostToolUse", "web", t1, tool=tool, call=call, phase="end", detail=detail)]
        if itype == "McpToolCall":
            server = ob.token(item.get("server")) or "mcp"
            name = f"mcp__{server}__{ob.token(item.get('tool')) or 'tool'}"
            failed = item.get("status") in ("failed", "cancelled")
            detail = {}
            ms = duration_ms(item, start, end)
            if ms is not None:
                detail["duration_ms"] = ms
            return [self.event(key, "PreToolUse", "tool", t0, tool=name, call=call, phase="start"),
                    self.event(key, "PostToolUseFailure" if failed else "PostToolUse", "tool", t1, tool=name, call=call,
                               phase="fail" if failed else "end", detail=detail)]
        if itype == "FileChange":
            changes = item.get("changes") if isinstance(item.get("changes"), dict) else {}
            path = next((p for p in changes if isinstance(p, str)), "")
            failed = item.get("status") in ("failed", "cancelled")
            detail = ob.area_of(path, self.cwd)
            return [self.event(key, "PreToolUse", "file", t0, tool="Edit", call=call, phase="start", detail=dict(detail)),
                    self.event(key, "PostToolUseFailure" if failed else "PostToolUse", "file", t1, tool="Edit", call=call,
                               phase="fail" if failed else "end", detail=detail)]
        return []


def load_state() -> dict:
    path = ob.OUT / "codex-follow.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(main_id: str, threads: dict, seen: list):
    """Where each followed session stopped (per main session, last 30), so a rerun adds nothing twice."""
    data = load_state()
    sessions = data.get("sessions") if isinstance(data.get("sessions"), dict) else {}
    sessions.pop(main_id, None)
    # File names only (no personal folder paths); the files are found again under CODEX_HOME/sessions.
    sessions[main_id] = {"threads": {Path(p).name: {"id": t.meta["id"], "offset": t.reader.done_offset, "seq": t.reader.seq}
                                      for p, t in threads.items()}, "seen": seen[-6000:]}
    while len(sessions) > 30:
        sessions.pop(next(iter(sessions)))
    ob.write_text(ob.OUT / "codex-follow.json", json.dumps({"sessions": sessions}))


def write(events: list[dict], seen: set, order: list):
    fresh = [e for e in events if e["id"] not in seen]
    if not fresh:
        return []
    with ob.Lock(ob.LOCK, wait=10):
        for e in fresh:
            ob.append_event(e)
            seen.add(e["id"])
            order.append(e["id"])
        ob.refresh_live(fresh[-1])
    return fresh


def follow(harness: Path, rollout: Path | None = None, latest=False, once=False, until_complete=False,
           max_seconds=3 * 3600, poll=0.5, printer=None, announce=None, wait=False, waiting=None) -> dict:
    """Read the selected session (and its agent threads) into the office records. `once` reads what is there and stops."""
    ob.use_harness(harness)
    if not ob.safe_dirs():
        raise FollowError("runtime-data 폴더가 링크(심볼릭 링크·정션)라 쓰지 않습니다.")
    ob.OUT.mkdir(parents=True, exist_ok=True)
    if wait:
        if waiting:
            waiting()
        path, meta = wait_for_new(harness, max_seconds)
    else:
        path, meta = select(harness, rollout, latest)
    sessions = load_state().get("sessions")
    previous = sessions.get(meta["id"], {}) if isinstance(sessions, dict) else {}
    saved = previous.get("threads", {}) if isinstance(previous.get("threads"), dict) else {}
    seen_order = [x for x in previous.get("seen", []) if isinstance(x, str)]
    seen = set(seen_order)

    def open_thread(p: Path, m: dict):
        s = saved.get(p.name, {})
        ok = s.get("id") == m["id"]
        return Thread(p, m, meta["id"], s.get("offset", 0) if ok else 0, s.get("seq", 0) if ok else 0)

    threads = {path: open_thread(path, meta)}
    if announce:
        announce(path, meta)
    started = time.monotonic()
    started_at = datetime.fromisoformat(meta["ts"].replace("Z", "+00:00")) if meta.get("ts") else datetime.now(timezone.utc)
    last_scan, written, agents = 0.0, 0, 0
    reason = "read_all" if once else "time_limit"
    try:
        while True:
            if time.monotonic() - last_scan > 2 or once:
                last_scan = time.monotonic()
                for p in rollouts(day_folders(started_at)):
                    if p in threads:
                        continue
                    m = first_meta(p)
                    if m and m["parent"] == meta["id"]:
                        threads[p] = open_thread(p, m)
                        agents += 1
            events = []
            for t in list(threads.values()):
                events += t.poll()
            fresh = write(events, seen, seen_order)
            written += len(fresh)
            if fresh:
                save_state(meta["id"], threads, seen_order)
                if printer:
                    for e in fresh:
                        printer(e)
            if once:
                save_state(meta["id"], threads, seen_order)
                break
            if until_complete and threads[path].finished and all(t.finished for t in threads.values() if t.child):
                reason = "session_turn_finished"
                break
            if time.monotonic() - started >= max_seconds:
                break
            time.sleep(poll)
    except KeyboardInterrupt:
        reason = "interrupted"
    save_state(meta["id"], threads, seen_order)
    return {"session": meta["id"], "rollout": str(path), "agent_threads": agents, "events_written": written,
            "stop_reason": reason, "cli_version": meta.get("cli_version")}
