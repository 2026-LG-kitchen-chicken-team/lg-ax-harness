"""Development-only, human-operated measurement; no model/runtime invocation."""
from __future__ import annotations

from collections import defaultdict
import ctypes
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

PHASES = ("setup", "read", "input", "evidence", "edit", "wait")
ACTIVE = ("read", "input", "evidence", "edit")
CONDITIONS = ("manual", "general_ai", "harness")
USAGE = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
MODEL_FIELDS = ("model", "cli", "cli_version", "reasoning")
META_FIELDS = ("participant", "case_id", "condition", "data_version", "product_model", "data_fingerprint", "case_file_sha256", "input_sha256", "completion_sha256", "product_sha256", "model_and_settings", "learning_order", "attempt_index")
SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
ROOT = Path(__file__).resolve().parents[2]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not SAFE.fullmatch(value):
        raise ValueError("Use an anonymous ASCII identifier, 1..80 letters/digits/_/-")
    return value


def atomic_create(path, value):
    """Install a complete file exclusively. Existing evidence is never replaced."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)  # atomic and fails if destination exists (Windows/Linux)
    finally:
        Path(temp).unlink(missing_ok=True)


def clock_sample():
    """Python monotonic is system-wide; boot identity separates resets/reboots."""
    clock_id = None
    if os.name == "nt":
        class TimeOfDay(ctypes.Structure):
            _fields_ = [("boot", ctypes.c_int64), ("now", ctypes.c_int64),
                        ("bias", ctypes.c_int64), ("zone", ctypes.c_uint32),
                        ("reserved", ctypes.c_uint32), ("boot_bias", ctypes.c_uint64),
                        ("sleep_bias", ctypes.c_uint64)]
        info = TimeOfDay()
        status = ctypes.WinDLL("ntdll").NtQuerySystemInformation(3, ctypes.byref(info), ctypes.sizeof(info), None)
        if status == 0:
            clock_id = digest({"boot": info.boot, "machine": os.environ.get("COMPUTERNAME", "")})
    else:
        boot = Path("/proc/sys/kernel/random/boot_id")
        if boot.exists():
            clock_id = hashlib.sha256(boot.read_bytes()).hexdigest()
    return {"utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.monotonic_ns(), "clock_id": clock_id}


def validate_metadata(meta):
    if set(meta) != set(META_FIELDS):
        raise ValueError("Metadata must use only the documented fields; no private free text")
    for key in ("participant", "case_id", "data_version", "product_model"):
        identifier(meta[key])
    if meta["condition"] not in CONDITIONS:
        raise ValueError("Unknown condition")
    for key in ("data_fingerprint", "case_file_sha256", "input_sha256", "completion_sha256", "product_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", meta[key]):
            raise ValueError("Missing SHA256: " + key)
    if not isinstance(meta.get("learning_order"), list) or sorted(meta["learning_order"]) != sorted(CONDITIONS):
        raise ValueError("learning_order must list all three conditions once")
    if type(meta.get("attempt_index")) is not int or meta["attempt_index"] < 1:
        raise ValueError("attempt_index must be positive")
    if meta["condition"] != "manual" and not isinstance(meta.get("model_and_settings"), dict):
        raise ValueError("AI condition needs actual model, CLI version and settings (unknown allowed)")
    settings = meta.get("model_and_settings")
    if settings is not None:
        if set(settings) != set(MODEL_FIELDS):
            raise ValueError("model_and_settings needs only model/cli/cli_version/reasoning")
        for value in settings.values():
            if not isinstance(value, str) or not 1 <= len(value) <= 120 or any(c in value for c in ("@", "\\", "/", ":", "\n", "\r")):
                raise ValueError("Settings must be short labels without email, path or free text")
    if meta["condition"] == "manual" and meta.get("model_and_settings") is not None:
        raise ValueError("Manual condition must have model_and_settings=null")
    if not meta.get("product_model") or not meta.get("data_version"):
        raise ValueError("Exact product model/data version required")
    return meta


class Store:
    def __init__(self, root=None):
        self.root = Path(root or ROOT / ".harness/measurement").resolve()

    def path(self, run):
        return self.root / identifier(run)

    def create(self, run, meta, human_confirmed=False):
        if not human_confirmed:
            raise ValueError("A real participant must pass --human-confirmed")
        meta = validate_metadata(meta.copy())
        path = self.path(run)
        path.mkdir(parents=True, exist_ok=False)
        atomic_create(path / "metadata.json", {"schema": 1, "run_id": run, "metadata": meta, "created": clock_sample()})
        return run

    def load(self, run):
        path = self.path(run)
        meta = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        if meta["run_id"] != run or meta["schema"] != 1:
            raise ValueError("Invalid run metadata")
        validate_metadata(meta["metadata"])
        events, previous = [], None
        for file in sorted((path / "events").glob("*.json")):
            event = json.loads(file.read_text(encoding="utf-8"))
            checksum = event.pop("sha256")
            if digest(event) != checksum or event["sequence"] != len(events) + 1 or event["previous"] != previous:
                raise ValueError("Event chain incomplete/modified; preserve originals and inspect")
            event["sha256"] = checksum
            previous = checksum
            events.append(event)
        return meta, events

    def append(self, run, data, event_id=None, human_confirmed=False, sample=None):
        if not human_confirmed:
            raise ValueError("A real participant must pass --human-confirmed")
        event_id = identifier(event_id or str(uuid.uuid4()))
        path = self.path(run)
        lock = path / ".write-lock"
        lock.mkdir()  # concurrent/crashed writers fail visibly; no stale-lock guessing
        try:
            meta, events = self.load(run)
            for old in events:
                if old["event_id"] == event_id:
                    if old["data"] == data:
                        return old
                    atomic_create(path / "conflicts" / (str(uuid.uuid4()) + ".json"),
                                  {"event_id": event_id, "attempt": data, "original_sha256": old["sha256"]})
                    raise ValueError("Conflicting event ID; original and attempted payload preserved")
            self._validate_data(meta["metadata"], events, data)
            event = {"event_id": event_id, "sequence": len(events) + 1,
                     "previous": events[-1]["sha256"] if events else None,
                     "sample": sample if sample is not None else clock_sample(), "data": data}
            event["sha256"] = digest(event)
            atomic_create(path / "events" / (f"{event['sequence']:08d}-{event_id}.json"), event)
            return event
        finally:
            lock.rmdir()

    @staticmethod
    def _validate_data(meta, events, data):
        kind = data.get("kind")
        if kind in ("start", "pause", "finish"):
            actor = identifier(data["participant"])
            if actor != meta["participant"]:
                raise ValueError("One participant per run; collaborators use separate runs")
            if any(e["data"]["kind"] == "finish" for e in events):
                raise ValueError("Run finished; use a new run for repeats/corrections")
            opened = None
            for event in events:
                if event["data"]["kind"] == "start":
                    opened = event["data"]["phase"]
                elif event["data"]["kind"] == "pause":
                    opened = None
            if kind == "start" and data.get("phase") not in PHASES:
                raise ValueError("Unknown activity phase")
            if kind == "pause" and opened is None:
                raise ValueError("No activity is open")
            if kind == "finish":
                if data.get("outcome") not in ("completed", "held", "failed", "aborted"):
                    raise ValueError("Unknown outcome")
                for field in ("additional_inputs", "revisions"):
                    if data.get(field) is not None and (type(data[field]) is not int or data[field] < 0):
                        raise ValueError("Counts must be nonnegative or null")
                if data["outcome"] in ("completed", "held") and not data.get("result_sha256"):
                    raise ValueError("Completed/held run requires actual result artifact")
        elif kind == "quality":
            reviewer = identifier(data["reviewer"])
            if reviewer == meta["participant"] or data.get("verdict") not in ("equivalent", "not_equivalent", "pending"):
                raise ValueError("Independent reviewer and explicit quality verdict required")
            if data["verdict"] != "pending" and not data.get("evidence_sha256"):
                raise ValueError("Quality verdict needs independent evidence")
            if data["verdict"] != "pending" and not any(e["data"]["kind"] == "finish" for e in events):
                raise ValueError("Quality verdict requires a finished result")
        elif kind == "billing":
            identifier(data["transaction_id"])
            if data.get("refund_of") is not None:
                identifier(data["refund_of"])
            if data.get("attribution") not in ("verified", "window_only", "unverified"):
                raise ValueError("Unknown attribution")
            if not re.fullmatch(r"[A-Z][A-Z0-9_:-]{1,39}", data.get("unit", "")):
                raise ValueError("Keep currency or named credit units separate")
            if data.get("amount") is not None:
                if not isinstance(data["amount"], str):
                    raise ValueError("Amount must be a decimal string; do not use floats")
                try:
                    amount = Decimal(data["amount"])
                except InvalidOperation as exc:
                    raise ValueError("Invalid decimal amount") from exc
                if not amount.is_finite():
                    raise ValueError("Amount must be finite decimal or null")
                if amount < 0 and not data.get("refund_of"):
                    raise ValueError("Negative charges require refund_of; preserve original transaction")
            if data["attribution"] == "verified" and (not data.get("evidence_sha256") or data.get("concurrent_other_usage") is not False):
                raise ValueError("Verified charge needs evidence and exclusion of concurrent unrelated usage")
        elif kind == "usage":
            identifier(data["scope_id"])
            identifier(data["source"])
            if type(data.get("snapshot_index")) is not int or data["snapshot_index"] < 0:
                raise ValueError("Cumulative snapshot index must be nonnegative")
            if data.get("coverage") not in ("partial", "all_calls_verified"):
                raise ValueError("Specify observed coverage")
            for key in USAGE:
                value = data.get(key)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Usage must be nonnegative integer or null")
            for total, subset in (("input_tokens", "cached_input_tokens"), ("output_tokens", "reasoning_output_tokens")):
                if data.get(total) is not None and data.get(subset) is not None and data[subset] > data[total]:
                    raise ValueError("Subset usage exceeds total")
        else:
            raise ValueError("Unknown event kind")


def union_seconds(intervals):
    """Union closed monotonic intervals per actor/clock; sum people, not overlaps."""
    groups = defaultdict(list)
    for actor, clock, start, end in intervals:
        if clock is None or type(start) is not int or type(end) is not int or end < start:
            return None
        groups[(actor, clock)].append((start, end))
    total = 0
    for spans in groups.values():
        spans.sort()
        left, right = spans[0]
        for start, end in spans[1:]:
            if start <= right:
                right = max(right, end)
            else:
                total += right - left
                left, right = start, end
        total += right - left
    return total / 1_000_000_000


def elapsed(start, end):
    if not start or not end or not start.get("clock_id") or start["clock_id"] != end.get("clock_id"):
        return None
    delta = end["monotonic_ns"] - start["monotonic_ns"]
    return delta / 1_000_000_000 if delta >= 0 else None


def timing(events):
    opened, spans, unknown, first, finish = None, defaultdict(list), [], None, None
    measured_phases = set()
    for event in events:
        data, sample = event["data"], event["sample"]
        kind = data["kind"]
        if kind not in ("start", "pause", "finish"):
            continue
        if opened:
            phase, actor, start = opened
            duration = elapsed(start, sample)
            if duration is None:
                unknown.append("clock_reset_or_reverse:" + phase)
            else:
                spans[phase].append((actor, start["clock_id"], start["monotonic_ns"], sample["monotonic_ns"]))
            opened = None
        if kind == "start":
            opened = (data["phase"], data["participant"], sample)
            measured_phases.add(data["phase"])
            if data["phase"] != "setup" and first is None:
                first = sample
        elif kind == "finish":
            finish = sample
    if opened:
        unknown.append("open_interval:" + opened[0])
    if finish is None:
        unknown.append("not_finished")
    active = [span for phase in ACTIVE for span in spans[phase]]
    if first is None:
        unknown.append("no_work_activity_recorded")
    return {"human_active_seconds": None if unknown else union_seconds(active),
            "setup_seconds": None if "setup" not in measured_phases or any("setup" in item for item in unknown) else union_seconds(spans["setup"]),
            "wait_seconds": None if "wait" not in measured_phases or any("wait" in item for item in unknown) else union_seconds(spans["wait"]),
            "wall_seconds": elapsed(first, finish),
            "closed_known_active_seconds": union_seconds(active),
            "by_phase_seconds": {p: None if p not in measured_phases or any(p in item for item in unknown) else union_seconds(spans[p]) for p in PHASES},
            "unknown_reasons": unknown}


def billing_report(events):
    transactions, conflicts, duplicates = {}, set(), 0
    for event in events:
        data = event["data"]
        if data["kind"] != "billing":
            continue
        key = data["transaction_id"]
        if key in transactions:
            if transactions[key] == data:
                duplicates += 1
            else:
                conflicts.add(key)
        else:
            transactions[key] = data
    refunds = defaultdict(list)
    for key, data in transactions.items():
        original_id = data.get("refund_of")
        if original_id is None:
            continue
        original = transactions.get(original_id)
        # A refund must point directly to a positive charge, never to itself,
        # another refund or a cycle. Resolve after collecting all records so
        # receiving refund evidence before charge evidence is safe.
        if (original_id == key or original is None or original_id in conflicts
                or original["unit"] != data["unit"] or original.get("refund_of") is not None
                or original["amount"] is None or Decimal(original["amount"]) <= 0
                or (data["amount"] is not None and Decimal(data["amount"]) > 0)):
            conflicts.add(key)
        elif key not in conflicts and data["amount"] is not None:
            refunds[original_id].append(key)
    for original_id, refund_ids in refunds.items():
        refunded = sum((-Decimal(transactions[key]["amount"]) for key in refund_ids), Decimal(0))
        if refunded > Decimal(transactions[original_id]["amount"]):
            conflicts.update(refund_ids)
    units = defaultdict(lambda: {"verified": [], "window_only": [], "unverified": [], "conflicts": 0, "unknown": 0})
    for key, data in transactions.items():
        group = units[data["unit"]]
        if key in conflicts:
            group["conflicts"] += 1
        elif data["amount"] is None:
            group["unknown"] += 1
        else:
            group[data["attribution"]].append(Decimal(data["amount"]))
    output = {}
    for unit, group in units.items():
        output[unit] = {"verified_attributed_amount": None if group["conflicts"] or group["unknown"] or not group["verified"] else str(sum(group["verified"], Decimal(0))),
                        "window_only_amount": str(sum(group["window_only"], Decimal(0))) if group["window_only"] else None,
                        "unverified_amount": str(sum(group["unverified"], Decimal(0))) if group["unverified"] else None,
                        "conflict_transactions": group["conflicts"], "unknown_amounts": group["unknown"]}
    return {"units": output, "duplicate_records_ignored": duplicates, "actual_total_cost": None,
            "coverage": "observed_transactions_only", "note": "No conversion between currencies, tokens, subscriptions or credits"}


def usage_report(events):
    groups = defaultdict(list)
    for event in events:
        data = event["data"]
        if data["kind"] == "usage":
            groups[(data["source"], data["scope_id"])].append(data)
    result = []
    for (source, scope), snapshots in sorted(groups.items()):
        seen, invalid, duplicates = {}, False, 0
        for value in snapshots:
            index = value["snapshot_index"]
            if index in seen:
                if seen[index] == value:
                    duplicates += 1
                else:
                    invalid = True
            seen[index] = value
        ordered = [seen[key] for key in sorted(seen)]
        high_water = {}
        for snapshot in ordered:
            for field in USAGE:
                observed = snapshot.get(field)
                if observed is None:
                    continue  # a partial observation does not reset cumulative history
                previous = high_water.get(field)
                if previous is not None and observed < previous:
                    invalid = True
                high_water[field] = observed if previous is None else max(previous, observed)
        last = ordered[-1]
        values = {k: None if invalid else last.get(k) for k in USAGE}
        values["noncached_input_tokens"] = None if values["input_tokens"] is None or values["cached_input_tokens"] is None else values["input_tokens"] - values["cached_input_tokens"]
        result.append({"source": source, "scope_id": scope, "latest_snapshot_index": last["snapshot_index"],
                       "values": values, "coverage": "unknown" if invalid else last["coverage"],
                       "conflict_or_reverse": invalid, "duplicate_records_ignored": duplicates})
    return {"scopes": result, "combined_total": None, "note": "Latest cumulative value per scope; scopes are never assumed disjoint"}


def report(store, run):
    meta, events = store.load(run)
    finish = next((e["data"] for e in reversed(events) if e["data"]["kind"] == "finish"), None)
    qualities = [e["data"] for e in events if e["data"]["kind"] == "quality"]
    starts = [e["sample"]["utc"] for e in events if e["data"]["kind"] == "start" and e["data"]["phase"] != "setup"]
    finishes = [e["sample"]["utc"] for e in events if e["data"]["kind"] == "finish"]
    return {"schema": 1, "run_id": run, "metadata": {key: meta["metadata"][key] for key in META_FIELDS}, "timing": timing(events),
            "created_at": meta["created"]["utc"], "started_at": starts[0] if starts else None, "finished_at": finishes[-1] if finishes else None,
            "outcome": finish["outcome"] if finish else "in_progress",
            "additional_inputs": finish.get("additional_inputs") if finish else None,
            "revisions": finish.get("revisions") if finish else None,
            "result_sha256": finish.get("result_sha256") if finish else None,
            "quality": {"verdict": qualities[-1]["verdict"], "reviewer": qualities[-1]["reviewer"], "evidence_sha256": qualities[-1].get("evidence_sha256")} if qualities else {"verdict": "pending"},
            "billing": billing_report(events), "usage": usage_report(events),
            "evidence_chain_sha256": events[-1]["sha256"] if events else None,
            "conflict_attempts": len(list((store.path(run) / "conflicts").glob("*.json"))),
            "human_attestation_only": True,
            "limitations": ["Human-operated attestation; CLI cannot prove who pressed keys", "Independent quality required before reductions", "Small/order-sensitive sample; no general effect claim", "Raw evidence stays private; inspect before sharing metadata"]}


def compare(baseline, candidate):
    reasons = []
    for field in ("case_id", "data_version", "product_model", "data_fingerprint", "case_file_sha256", "input_sha256", "completion_sha256", "product_sha256"):
        if baseline["metadata"].get(field) != candidate["metadata"].get(field):
            reasons.append("mismatch:" + field)
    if baseline["metadata"]["condition"] == candidate["metadata"]["condition"]:
        reasons.append("same_condition")
    if baseline["metadata"]["condition"] != "manual" and candidate["metadata"]["condition"] != "manual":
        if baseline["metadata"]["model_and_settings"] != candidate["metadata"]["model_and_settings"]:
            reasons.append("mismatch:model_and_settings")
    for name, value in (("baseline", baseline), ("candidate", candidate)):
        if value["quality"]["verdict"] != "equivalent":
            reasons.append(name + ":quality_pending_or_not_equivalent")
        if value["outcome"] not in ("completed", "held") or value["conflict_attempts"]:
            reasons.append(name + ":failed_open_or_conflicting")
        if value["timing"]["human_active_seconds"] is None or value["timing"]["wall_seconds"] is None:
            reasons.append(name + ":missing_time")
        if value["additional_inputs"] is None or value["revisions"] is None:
            reasons.append(name + ":missing_counts")
    before = baseline["timing"]["human_active_seconds"]
    after = candidate["timing"]["human_active_seconds"]
    if before is not None and before <= 0:
        reasons.append("zero_baseline")
    return {"baseline_run": baseline["run_id"], "candidate_run": candidate["run_id"],
            "human_active_reduction_percent": None if reasons else float((Decimal(str(before)) - Decimal(str(after))) / Decimal(str(before)) * 100),
            "gate_reasons": reasons, "cost_reduction_percent": None,
            "note": "Pair only; failures/retries and order/exposure must be reported for the whole series. Missing charge never blocks timing report or becomes zero."}


COMPLETION = "근거와 원문 위치·정확 모델/버전, 불편과 기존 기능 대조, 제약에 맞는 기획안 최대2개, 미확인/보류 사유, 최종 결과파일. 정직한 근거 부족 보류 허용. 같은 업무완료 기준; 설치와 대기 별도."


def prepare(directory, participant, condition, order, model_settings=None, attempt=1):
    """Copy common real inputs without evaluator expected answers/rubric."""
    directory = Path(directory)
    case_file = ROOT / "evals/judge/s05-cases.json"
    cases = json.loads(case_file.read_text(encoding="utf-8"))
    case = next(c for c in cases["cases"] if c["id"] == "S05-R01")
    data_dir = ROOT / "data/business/lg-research-v3"
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    source_hashes = {p.name: file_sha(p) for p in sorted(data_dir.iterdir()) if p.is_file()}
    for declared in manifest["files"]:
        if source_hashes[declared["path"]] != declared["sha256"]:
            raise ValueError("Dataset manifest checksum mismatch")
    sources = [json.loads(line) for line in (data_dir / "sources.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    models = json.loads((data_dir / "models.json").read_text(encoding="utf-8"))
    if isinstance(models, dict):
        models = models["models"]
    model = next(m for m in models if m["model_id"] == case["model_id"])
    scope = {k: model[k] for k in ("model_id", "model_version", "document_version")}
    filtered = [s for s in sources if all(s[k] == v for k, v in scope.items())]
    common = {"case_id": case["id"], "product_model": case["model_id"], "question": case["turns"][0], "constraints": case["constraints"],
              "data_version": manifest["data_version"], "scope": scope, "sources": filtered, "completion": COMPLETION,
              "additional_rule": "저장v3 제공 자료만 사용. 외부 조사/다른 모델/새 원문 금지. 하네스 답변과 평가 기대정답은 수행 전에 보지 않는다."}
    product_hashes = {p.relative_to(ROOT).as_posix(): file_sha(p) for folder in ("agents", "skills", "product-tools", "adapters")
                      for p in sorted((ROOT / folder).rglob("*")) if p.is_file() and p.suffix in (".py", ".md", ".json")}
    meta = {"participant": participant, "case_id": case["id"], "condition": condition,
            "data_version": manifest["data_version"], "product_model": case["model_id"], "data_fingerprint": digest(source_hashes),
            "case_file_sha256": file_sha(case_file), "input_sha256": digest(common), "completion_sha256": digest(COMPLETION),
            "product_sha256": digest(product_hashes), "model_and_settings": model_settings,
            "learning_order": order, "attempt_index": attempt}
    validate_metadata(meta)
    directory.mkdir(parents=True, exist_ok=False)
    atomic_create(directory / "task.json", common)
    atomic_create(directory / "metadata.json", meta)
    atomic_create(directory / "fingerprints.json", {"data_files": source_hashes, "product_files": product_hashes})
    return meta
