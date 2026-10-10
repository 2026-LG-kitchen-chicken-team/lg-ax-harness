"""Fail-closed sanitization of explicitly selected Codex JSONL sources."""
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
SKILLS = ("evidence-retrieval", "needs-structuring", "feature-comparison", "concept-writing",
          "review-and-revise", "web-evidence-collection")
TOOLS = {"command_execution", "mcp_tool_call", "web_search", "file_change", "function_call",
         "exec_command", "write_stdin", "read_file", "shell", "shell_command", "apply_patch"}
ITEMS = TOOLS | {"agent_message", "reasoning", "plan", "collab_tool_call"}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def native_id(value):
    try:
        return str(UUID(value)) if isinstance(value, str) else None
    except ValueError:
        return None


def safe_id(value):
    if native_id(value):
        return native_id(value)
    if isinstance(value, str) and re.fullmatch(r"item_[0-9]{1,12}", value):
        return value
    # Opaque identifiers are correlated by a digest; never forward arbitrary strings.
    return "id-" + digest(value)[:24] if isinstance(value, str) and value else None


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat() if parsed.tzinfo else None
    except ValueError:
        return None


def usage(raw):
    if not isinstance(raw, dict):
        return {key: None for key in FIELDS}
    return {key: raw.get(key) if type(raw.get(key)) is int and raw[key] >= 0 else None for key in FIELDS}


def valid_usage(value):
    for part, total in (("cached_input_tokens", "input_tokens"), ("reasoning_output_tokens", "output_tokens")):
        if value[part] is not None and value[total] is not None and value[part] > value[total]:
            return False
    return any(value[key] is not None for key in FIELDS)


def command_mapping(command):
    """Indicators only: reading a Skill never proves its execution."""
    if not isinstance(command, str):
        return None, None
    lower = command.lower().replace("\\", "/")
    read = any(word in lower for word in ("get-content", "read_text", "read_file", "cat ", "type "))
    if read and "skill.md" in lower:
        return "instruction_loaded", next((s for s in SKILLS if "/" + s + "/" in lower), None)
    for skill in SKILLS:
        if "/" + skill + "/scripts/run.py" in lower:
            return "command_based_mapping", skill
    operations = {
        "prepare_planning_input": "evidence-retrieval", "open_request_bundle": "evidence-retrieval",
        "review_product_result": "review-and-revise", "save_result": "review-and-revise",
        "retrieve_reviews": "evidence-retrieval", "retrieve_product_facts": "evidence-retrieval",
        "fetch_web_page": "web-evidence-collection", "capture_web_page": "web-evidence-collection",
        "import_web_evidence": "web-evidence-collection",
    }
    for operation, skill in operations.items():
        if operation in lower:
            return "command_based_mapping", skill
    return None, None


class Collector:
    """One selected native ID; snapshots replace, never add to previous snapshots."""
    def __init__(self, selected_id, run_id, mode="replay", state=None):
        if native_id(selected_id) != selected_id.lower():
            raise ValueError("invalid_native_id")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id) or run_id.startswith(("sk-", "pk-")):
            raise ValueError("invalid_run_id")
        if mode not in ("replay", "tail"):
            raise ValueError("invalid_mode")
        self.selected_id, self.run_id, self.mode = selected_id.lower(), run_id, mode
        self.state = state or {"identity": {}, "sequence": {}, "usage": {}, "counts": {}, "starts": {}}
        self.state.setdefault("starts", {})
        self.state.setdefault("cli_version", None)
        self.last_observed = None

    def count(self, name):
        self.state["counts"][name] = self.state["counts"].get(name, 0) + 1

    def feed(self, raw, source_ref, seq, source_kind):
        if not isinstance(raw, dict) or source_kind not in ("cli", "rollout") or not re.fullmatch(r"[a-f0-9]{64}", source_ref):
            self.count("invalid_records")
            return None
        kind = raw.get("type")
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        identity = raw.get("thread_id") if kind == "thread.started" else payload.get("id") if kind == "session_meta" else None
        if kind in ("thread.started", "session_meta"):
            if native_id(identity) != self.selected_id:
                self.state["identity"][source_ref] = False
                self.count("identity_mismatch")
                return None
            self.state["identity"][source_ref] = True
            version = payload.get("cli_version")
            if isinstance(version, str) and re.fullmatch(r"[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}", version):
                self.state["cli_version"] = version
        if self.state["identity"].get(source_ref) is not True:
            self.count("unverified_identity")
            return None
        last_seq = self.state["sequence"].get(source_ref, 0)
        if type(seq) is not int or seq <= last_seq:
            self.count("duplicate_or_stale_sequence")
            return None
        self.state["sequence"][source_ref] = seq
        source_time = timestamp(raw.get("timestamp"))
        observed_time = now()
        self.last_observed = observed_time
        item = raw.get("item") if isinstance(raw.get("item"), dict) else {}
        event_kind, entity_kind, entity_name, status = None, "runtime", "codex", "observed"
        invocation_id = safe_id(item.get("id") or payload.get("call_id"))
        turn_id = safe_id(raw.get("turn_id") or payload.get("turn_id"))
        parent_id = safe_id(item.get("parent_id") or payload.get("parent_id"))
        mapping, skill = None, None
        raw_usage, scope = None, None
        if kind == "thread.started" or kind == "session_meta":
            event_kind, entity_kind, status = "session_identity", "agent", "observed"
        elif kind in ("turn.started", "turn.completed", "turn.failed", "error"):
            event_kind = kind
            entity_kind = "turn" if kind.startswith("turn.") else "runtime"
            status = {"turn.started": "started", "turn.completed": "completed", "turn.failed": "failed", "error": "failed"}[kind]
            if kind == "turn.completed":
                raw_usage, scope = raw.get("usage"), "cli_turn_reported"
        elif kind in ("item.started", "item.updated", "item.completed"):
            item_kind = item.get("type")
            if item_kind not in ITEMS:
                self.count("unsupported_items")
                return None
            entity_name = item_kind
            entity_kind = "tool" if item_kind in TOOLS else "agent" if item_kind == "collab_tool_call" else "runtime"
            event_kind = kind
            status = "started" if kind == "item.started" else "completed" if kind == "item.completed" else "partial"
            if item.get("status") in ("failed", "cancelled"):
                status = item["status"]
            if item_kind == "command_execution" and type(item.get("exit_code")) is int and item["exit_code"] != 0:
                status = "failed"
            mapping, skill = command_mapping(item.get("command"))
        elif kind == "event_msg" and payload.get("type") == "token_count":
            event_kind, status = "usage_snapshot", "partial"
            info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
            raw_usage, scope = info.get("total_token_usage"), "native_session_cumulative"
        elif kind == "event_msg" and payload.get("type") in ("task_complete", "task_started", "turn_aborted"):
            event_kind = payload["type"]
            status = {"task_complete": "completed", "task_started": "started", "turn_aborted": "cancelled"}[event_kind]
            entity_kind = "turn"
        elif kind == "response_item" and payload.get("type") in ("function_call", "function_call_output"):
            event_kind = payload["type"]
            status = "started" if event_kind == "function_call" else "completed"
            entity_kind = "tool"
            entity_name = payload.get("name") if payload.get("name") in TOOLS else "function_call"
            if event_kind == "function_call":
                arguments = payload.get("arguments")
                try:
                    parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
                except ValueError:
                    parsed = None
                if isinstance(parsed, dict):
                    mapping, skill = command_mapping(parsed.get("cmd") or parsed.get("command"))
        else:
            self.count("unobserved_record_types")
            return None
        snapshot = usage(raw_usage)
        if scope and raw_usage is not None:
            previous = self.state["usage"].get(scope)
            # CLI usage is reported per turn. Only rollout totals are cumulative.
            regression = scope == "native_session_cumulative" and previous and any(
                snapshot[k] is not None and previous["snapshot"].get(k) is not None and snapshot[k] < previous["snapshot"][k] for k in FIELDS)
            if not valid_usage(snapshot) or regression:
                self.count("regressing_or_invalid_usage")
                snapshot = usage(None)
            else:
                self.state["usage"][scope] = {"snapshot": snapshot, "status": status,
                    "observed_timestamp": observed_time, "turn_id": turn_id}
        if event_kind in ("task_complete", "turn.completed"):
            current = self.state["usage"].get("native_session_cumulative")
            if current:
                current["status"] = "completed_observation"
        key = invocation_id or turn_id or ("turn" if entity_kind == "turn" else event_kind)
        start_key = source_ref + ":" + key
        if status == "started":
            self.state["starts"][start_key] = source_time or observed_time
            # Bounded active bookkeeping even for incomplete/never-ended items.
            if len(self.state["starts"]) > 512:
                self.state["starts"].pop(next(iter(self.state["starts"])))
                self.count("active_state_dropped")
        start_time = self.state["starts"].get(start_key) if status in ("completed", "failed", "cancelled") else None
        if status in ("completed", "failed", "cancelled"):
            self.state["starts"].pop(start_key, None)
        event_id = digest(source_ref + ":" + str(seq) + ":" + json.dumps(raw, sort_keys=True, ensure_ascii=False))
        self.count("accepted_events")
        native_usage = self.state["usage"].get("native_session_cumulative")
        return {"schema_version": 1, "run_id": self.run_id, "native_thread_id": self.selected_id,
            "session_id": self.selected_id, "turn_id": turn_id, "agent_id": self.selected_id,
            "event_id": event_id, "seq": seq, "source_timestamp": source_time,
            "observed_timestamp": observed_time, "start_timestamp": start_time,
            "timing_basis": "source" if source_time and start_time else "observer_receipt",
            "entity_kind": entity_kind, "entity_name": entity_name, "event_kind": event_kind,
            "invocation_id": invocation_id, "parent_id": parent_id, "status": status,
            "source_log_ref": source_ref, "source_kind": source_kind, "mode": self.mode,
            "coverage": "selected_native_log_partial", "usage_scope": scope,
            "usage_snapshot": snapshot, "skill_mapping_basis": mapping, "mapped_skill": skill,
            "native_usage_snapshot": native_usage["snapshot"] if native_usage else usage(None),
            "native_usage_status": native_usage["status"] if native_usage else None,
            "cli_version": self.state["cli_version"],
            "backend_call_count": None, "cost_usd": None}

    def summary(self):
        native = self.state["usage"].get("native_session_cumulative")
        cli = self.state["usage"].get("cli_turn_reported")
        snapshot = native["snapshot"] if native else usage(None)
        noncached = snapshot["input_tokens"] - snapshot["cached_input_tokens"] if snapshot["input_tokens"] is not None and snapshot["cached_input_tokens"] is not None else None
        return {"schema_version": 1, "run_id": self.run_id, "native_thread_id": self.selected_id,
            "mode": self.mode, "coverage": "selected_native_log_partial", "native_usage": native,
            "last_cli_turn_usage": cli, "noncached_input_tokens": noncached,
            "last_observed_timestamp": self.last_observed, "counters": self.state["counts"],
            "cli_version": self.state["cli_version"],
            "backend_call_count": None, "cost_usd": None,
            "observer_created_model_requests": 0, "observer_added_model_context": 0}
