"""Transactional local workflow state. It does not control native model turns."""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import re
import sqlite3
import uuid
from .contracts import MAX_RESULT_BYTES, ToolError, canonical, fail, fingerprint, identifier, integer, obj, planning_input, strict_json, text
from .tools import ProductTools

def now():
    return datetime.now(timezone.utc).isoformat()

def code_fingerprint():
    base = Path(__file__).parent
    return hashlib.sha256(b"".join(p.name.encode() + b"\0" + p.read_bytes() for p in sorted(base.glob("*.py")))).hexdigest()

class StateStore:
    def __init__(self, path, dataset, workspace=None):
        self.dataset = dataset
        self.workspace = Path(workspace).resolve() if workspace is not None else None
        self.tools = ProductTools(dataset)
        self.code_hash = code_fingerprint()
        path = Path(path)
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS datasets(version TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS turns(
                turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, request_key TEXT NOT NULL,
                input_json TEXT NOT NULL, context_hash TEXT NOT NULL, dataset_hash TEXT NOT NULL,
                code_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', valid INTEGER NOT NULL DEFAULT 1,
                revision_count INTEGER NOT NULL DEFAULT 0, result_version INTEGER NOT NULL DEFAULT 0,
                invalidation_reason TEXT, created_at TEXT NOT NULL,
                UNIQUE(session_id, request_key));
            CREATE TABLE IF NOT EXISTS results(
                turn_id TEXT NOT NULL REFERENCES turns(turn_id), result_key TEXT NOT NULL, payload TEXT NOT NULL,
                payload_hash TEXT NOT NULL, result_version INTEGER NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(turn_id, result_key));
            CREATE TABLE IF NOT EXISTS usage(
                turn_id TEXT NOT NULL REFERENCES turns(turn_id), call_id TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(turn_id, call_id));
            CREATE TABLE IF NOT EXISTS invocations(
                turn_id TEXT NOT NULL REFERENCES turns(turn_id), invocation_id TEXT NOT NULL,
                tool_name TEXT NOT NULL, request_hash TEXT NOT NULL, attempts INTEGER NOT NULL,
                status TEXT NOT NULL, retryable INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(turn_id, invocation_id));
            CREATE TABLE IF NOT EXISTS retrieval_cache(
                cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL, payload_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cancellations(
                turn_id TEXT PRIMARY KEY REFERENCES turns(turn_id), cancel_key TEXT NOT NULL,
                request_json TEXT NOT NULL, prior_status TEXT NOT NULL, created_at TEXT NOT NULL);
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(results)")}
        if "validation_json" not in columns:
            self.db.execute("ALTER TABLE results ADD COLUMN validation_json TEXT NOT NULL DEFAULT '{}'")
        if "dataset_path" not in {row[1] for row in self.db.execute("PRAGMA table_info(turns)")}:
            # Internal recovery hint only. Old turns remain unbound until an
            # explicit --data is supplied; never infer a path from a version.
            self.db.execute("ALTER TABLE turns ADD COLUMN dataset_path TEXT")
        try:
            with self.transaction():
                known = self.db.execute("SELECT fingerprint FROM datasets WHERE version=?", (dataset.version,)).fetchone()
                if known and known[0] != dataset.fingerprint:
                    fail("data_version_reused", "Changed catalog must use a new data_version")
                self.db.execute("INSERT OR IGNORE INTO datasets VALUES(?, ?)", (dataset.version, dataset.fingerprint))
        except Exception:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        # Compose request resolution with start_turn atomically on this connection.
        # A savepoint rolls back only its own work; the outer transaction still
        # owns the write lock and final commit.
        if self.db.in_transaction:
            name = "nested_" + uuid.uuid4().hex
            self.db.execute("SAVEPOINT " + name)
            try:
                yield
            except BaseException:
                self.db.execute("ROLLBACK TO " + name)
                self.db.execute("RELEASE " + name)
                raise
            else:
                self.db.execute("RELEASE " + name)
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def row(self, session_id, turn_id):
        identifier(session_id, "session_id")
        identifier(turn_id, "turn_id")
        row = self.db.execute("SELECT * FROM turns WHERE session_id=? AND turn_id=?", (session_id, turn_id)).fetchone()
        if not row:
            fail("turn_not_found", "Turn not found in session")
        return row

    def fresh(self, row):
        return bool(row["valid"]) and row["dataset_hash"] == self.dataset.fingerprint and row["code_hash"] == self.code_hash

    def start_turn(self, planning, user_submitted):
        planning_input(planning)
        self.dataset.check_input(planning)
        if user_submitted is not True:
            fail("user_input_required", "Only explicit user input may create a business turn")
        payload = canonical(planning)
        context = {k: v for k, v in planning.items() if k not in ("session_id", "request_key")}
        context_hash = fingerprint({"input": context, "dataset": self.dataset.fingerprint, "code": self.code_hash})
        reused = False
        with self.transaction():
            prior = self.db.execute("SELECT * FROM turns WHERE session_id=? AND request_key=?", (planning["session_id"], planning["request_key"])).fetchone()
            if prior:
                if prior["input_json"] != payload:
                    fail("request_conflict", "Same session/request key has different input")
                if not self.fresh(prior):
                    fail("stale_context", "Old request is invalidated; explicit new user input/key is needed")
                turn_id, reused = prior["turn_id"], True
            else:
                # Conservative whole-result invalidation; retrieval has a separate cache key.
                self.db.execute("UPDATE turns SET valid=0, invalidation_reason='input_or_dependency_changed' WHERE session_id=? AND context_hash!=? AND valid=1", (planning["session_id"], context_hash))
                turn_id = "turn-" + uuid.uuid4().hex
                catalog = self.dataset.root
                relative = (catalog.relative_to(self.workspace).as_posix()
                            if self.workspace is not None and catalog.is_relative_to(self.workspace) else None)
                self.db.execute("INSERT INTO turns(turn_id,session_id,request_key,input_json,context_hash,dataset_hash,code_hash,created_at,dataset_path) VALUES(?,?,?,?,?,?,?,?,?)",
                                (turn_id, planning["session_id"], planning["request_key"], payload, context_hash, self.dataset.fingerprint, self.code_hash, now(), relative))
        return {"reused_request": reused, **self.get_turn(planning["session_id"], turn_id)}

    def usage_summary(self, session_id, turn_id=None):
        query = "SELECT u.payload FROM usage u JOIN turns t ON t.turn_id=u.turn_id WHERE t.session_id=?"
        args = [session_id]
        if turn_id:
            query += " AND t.turn_id=?"
            args.append(turn_id)
        calls = [strict_json(r[0]) for r in self.db.execute(query, args)]
        summary = {"recorded_calls": len(calls), "coverage": "reported_calls_only; native completeness unverified", "totals": {}, "unknown_counts": {}}
        for field in ("input_tokens", "output_tokens", "cache_tokens", "reasoning_tokens", "cost_usd"):
            known = [c[field] for c in calls if c[field] is not None]
            summary["unknown_counts"][field] = len(calls) - len(known)
            summary["totals"][field] = (str(sum((Decimal(x) for x in known), Decimal(0))) if field == "cost_usd" else sum(known)) if known else None
        summary["status"] = "unknown" if not calls or all(v is None for v in summary["totals"].values()) else "partially_measured"
        summary["remaining_budget"] = None
        return summary

    def get_turn(self, session_id, turn_id):
        row = self.row(session_id, turn_id)
        history = list(self.db.execute("SELECT result_key,payload_hash,result_version,created_at,validation_json FROM results WHERE turn_id=? ORDER BY result_version", (turn_id,)))
        latest = self.db.execute("SELECT payload,payload_hash,validation_json FROM results WHERE turn_id=? ORDER BY result_version DESC LIMIT 1", (turn_id,)).fetchone()
        valid = self.fresh(row)
        candidate = strict_json(latest[0]) if latest else None
        if latest and fingerprint(candidate) != latest[1]:
            fail("result_integrity", "Stored result fingerprint changed")
        validation = strict_json(latest[2]) if latest else None
        structurally_valid = validation is not None and validation.get("contract_valid") is True
        planning = strict_json(row["input_json"])
        known_runtime = all(planning["runtime"][key] is not None for key in ("engine", "engine_version", "model_id", "settings_fingerprint"))
        known_workflow = all(planning["workflow"][key] is not None for key in ("skill_fingerprint", "prompt_fingerprint"))
        return {"session_id": session_id, "turn_id": turn_id, "request_key": row["request_key"], "input": planning,
                "status": row["status"], "revision_count": row["revision_count"], "result_version": row["result_version"],
                "context_fingerprint": row["context_hash"], "valid": valid,
                "business_reuse_eligible": valid and structurally_valid and known_runtime and known_workflow and row["status"] == "completed",
                "invalidation_reason": row["invalidation_reason"] or (None if valid else "dataset_or_code_changed"),
                "latest_result": candidate if valid and structurally_valid and row["status"] != "cancelled" else None,
                "cancellation": self.cancellation(turn_id),
                "last_validation": self.compact_validation(validation),
                "result_history": [{**{k: r[k] for k in ("result_key", "payload_hash", "result_version", "created_at")}, "validation": self.compact_validation(strict_json(r["validation_json"]))} for r in history],
                "usage_summary": self.usage_summary(session_id, turn_id),
                "semantic_status": "unverified", "acceptance_ready": False, "native_execution_controlled": False}

    def cancellation(self, turn_id):
        row = self.db.execute("SELECT * FROM cancellations WHERE turn_id=?", (turn_id,)).fetchone()
        if row is None:
            return None
        return {"cancel_key": row["cancel_key"], "reason": strict_json(row["request_json"])["reason"],
                "prior_status": row["prior_status"], "recorded_at": row["created_at"],
                "scope": "local_business_write_barrier", "native_execution_controlled": False,
                "backend_stop_observed": None}

    def cancel_turn(self, session_id, turn_id, cancel_key, reason, expected_result_version, user_submitted):
        """Close business writes atomically; never infer native/backend termination."""
        identifier(cancel_key, "cancel_key")
        text(reason, "reason", 1000)
        integer(expected_result_version, "expected_result_version", 0, 3)
        if user_submitted is not True:
            fail("user_input_required", "Business cancellation requires explicit user input")
        request = canonical({"cancel_key": cancel_key, "reason": reason,
                             "expected_result_version": expected_result_version, "user_submitted": True})
        with self.transaction():
            row = self.row(session_id, turn_id)
            prior = self.db.execute("SELECT request_json FROM cancellations WHERE turn_id=?", (turn_id,)).fetchone()
            if prior:
                if prior[0] != request:
                    fail("cancel_conflict", "Turn already has a different cancellation request")
                reused = True
            else:
                if row["status"] in ("completed", "failed", "cancelled"):
                    fail("terminal_turn", "A finished turn cannot be cancelled retroactively")
                if row["result_version"] != expected_result_version:
                    fail("state_conflict", "Result version changed; reread turn before cancelling")
                # No freshness requirement: even a stale unfinished turn needs a
                # write barrier. Candidates, counters, usage and invocations stay intact.
                self.db.execute("INSERT INTO cancellations VALUES(?,?,?,?,?)",
                                (turn_id, cancel_key, request, row["status"], now()))
                self.db.execute("UPDATE turns SET status='cancelled' WHERE turn_id=?", (turn_id,))
                reused = False
        return {"reused_cancellation": reused, "turn": self.get_turn(session_id, turn_id),
                "scope": "local_business_write_barrier", "native_execution_controlled": False,
                "backend_stop_observed": None}

    @staticmethod
    def compact_validation(value):
        if value is None:
            return None
        result = {k: v for k, v in value.items() if k not in ("assessment", "review")}
        if "review" in value:
            result["review_summary"] = {k: v for k, v in value["review"].items() if k in ("can_finalize_reported_result", "reported_reasoning_consistent", "semantic_status", "acceptance_ready")}
            findings = value["review"].get("findings", [])
            result["review_summary"]["findings"] = findings[:20]
            result["review_summary"]["findings_omitted"] = max(0, len(findings) - 20)
        return result

    def save_result(self, session_id, turn_id, result_key, result, expected_result_version, assessment=None, require_review=False, response_mode="full"):
        if response_mode not in ("full", "receipt"):
            fail("invalid_input", "response_mode must be full or receipt")
        identifier(result_key, "result_key")
        integer(expected_result_version, "expected_result_version", 0, 3)
        payload = canonical(result)
        if not isinstance(result, dict) or len(payload.encode("utf-8")) > MAX_RESULT_BYTES:
            fail("input_limit", "Candidate must be an object <= 128 KiB")
        accepted, reason = True, None
        report = None
        with self.transaction():
            row = self.row(session_id, turn_id)
            if row["status"] == "cancelled":
                fail("terminal_turn", "A cancelled turn cannot accept candidate writes or replays")
            if not self.fresh(row):
                fail("stale_context", "Cannot store result for invalidated turn")
            if self.db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('request_selection_policies','conversation_requests')").fetchone()[0] == 2:
                from .selection import SelectionPolicy
                SelectionPolicy(self.db).check_turn(turn_id, self.dataset, strict_json(row["input_json"]))
            duplicate = self.db.execute("SELECT payload,payload_hash,validation_json FROM results WHERE turn_id=? AND result_key=?", (turn_id, result_key)).fetchone()
            if duplicate:
                if duplicate[0] != payload:
                    fail("result_conflict", "Result key already has different payload")
                if fingerprint(result) != duplicate[1]:
                    fail("result_integrity", "Stored candidate fingerprint changed")
                report = strict_json(duplicate[2])
                if require_review and not report.get("review_required"):
                    fail("result_conflict", "Stored candidate did not require review; cannot upgrade a replay")
                if report.get("assessment") != assessment:
                    fail("result_conflict", "Result key already has a different review assessment")
                accepted = report.get("contract_valid") is True
                reason = report.get("error", {}).get("code")
            else:
                if self.db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('product_workflows','conversation_requests')").fetchone()[0] == 2:
                    for request in self.db.execute("SELECT session_id,request_key FROM conversation_requests WHERE turn_id=?", (turn_id,)).fetchall():
                        research = "research-" + fingerprint(list(request))
                        finished = self.db.execute("SELECT finished_at FROM product_workflows WHERE research_id=?", (research,)).fetchone()
                        if finished and finished[0]:
                            fail("workflow_finished", "A finished workflow cannot accept a new candidate; retain the finished version")
                if row["result_version"] != expected_result_version:
                    fail("state_conflict", "Result version changed; reread turn before saving")
                if row["status"] in ("failed", "cancelled"):
                    fail("terminal_turn", "A failed/cancelled turn requires new explicit user input")
                revision = max(0, row["result_version"])
                if revision > 2:
                    self.db.execute("UPDATE turns SET status='held', invalidation_reason='business_revision_limit' WHERE turn_id=?", (turn_id,))
                    accepted, reason = False, "business_revision_limit"
                else:
                    try:
                        report = self.tools.validate_result_contract(strict_json(row["input_json"]), result)
                        if result["revisions"] != revision:
                            fail("revision_mismatch", "Result revision must match stored business revision count")
                        report["review_required"] = require_review
                        if require_review or assessment is not None:
                            from .planning import review_product_result
                            review = review_product_result(self.dataset, {"input": strict_json(row["input_json"]), "result": result, "assessment": assessment})
                            report.update(review=review, assessment=assessment)
                            if not review["can_finalize_reported_result"]:
                                fail("review_not_finalizable", "Reported review requires correction or a held result")
                        if result["status"] == "completed":
                            self.require_evidence_coverage(session_id, turn_id)
                    except ToolError as exc:
                        report = {**(report or {}), "review_required": require_review, "assessment": assessment, "contract_valid": False, "semantic_status": "unverified", "acceptance_ready": False,
                                  "error": {"code": exc.code, "message": str(exc)}}
                        accepted, reason = False, exc.code
                    version = row["result_version"] + 1
                    self.db.execute("INSERT INTO results(turn_id,result_key,payload,payload_hash,result_version,created_at,validation_json) VALUES(?,?,?,?,?,?,?)",
                                    (turn_id, result_key, payload, fingerprint(result), version, now(), canonical(report)))
                    status = result["status"] if accepted else "held" if revision == 2 else "needs_revision"
                    self.db.execute("UPDATE turns SET status=?, revision_count=?, result_version=? WHERE turn_id=?", (status, revision, version, turn_id))
        turn = self.get_turn(session_id, turn_id)
        if response_mode == "receipt":
            turn = {k: turn[k] for k in ("session_id", "turn_id", "request_key", "status", "revision_count", "result_version", "context_fingerprint", "valid", "invalidation_reason", "cancellation", "semantic_status", "acceptance_ready")}
        response = {"accepted": accepted, "reason": reason, "validation": self.compact_validation(report), "turn": turn}
        if response_mode == "receipt":
            saved = self.db.execute("SELECT payload,payload_hash,result_version,validation_json FROM results WHERE turn_id=? AND result_key=?", (turn_id, result_key)).fetchone()
            response["receipt"] = {"schema_version": 1, "session_id": session_id, "turn_id": turn_id, "result_key": result_key,
                "candidate_result_version": saved[2] if saved else None, "current_result_version": turn["result_version"],
                "result_sha256": saved[1] if saved else None,
                "assessment_sha256": fingerprint(strict_json(saved[3]).get("assessment")) if saved else None,
                "accepted": accepted, "status": turn["status"], "valid": turn["valid"],
                "semantic_status": "unverified", "acceptance_ready": False,
                "detail_operation": "current_request/get_turn; complete candidate and assessment in export_session"}
        return response

    def require_evidence_coverage(self, session_id, turn_id):
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"product_workflows", "conversation_requests"} <= tables:
            return
        for request in self.db.execute("SELECT session_id,request_key FROM conversation_requests WHERE turn_id=?", (turn_id,)):
            research = "research-" + fingerprint(list(request))
            columns = {r[1] for r in self.db.execute("PRAGMA table_info(product_workflows)")}
            query = "SELECT budget_seconds,timing_policy FROM product_workflows WHERE research_id=?" if "timing_policy" in columns else "SELECT budget_seconds,NULL FROM product_workflows WHERE research_id=?"
            clock = self.db.execute(query, (research,)).fetchone()
            if clock and (clock[0] <= 600 or clock[1] == "natural-completion-v1"):
                from .evidence_coverage import EvidenceCoverage
                EvidenceCoverage(self).require_complete(session_id, turn_id)
                from .workflow import WorkflowAudit
                WorkflowAudit(self.db, self.path.parent.parent).require_scope_disclosure(research)

    def record_usage(self, session_id, turn_id, call):
        obj(call, ("call_id", "status", "input_tokens", "output_tokens", "cache_tokens", "reasoning_tokens", "cost_usd"))
        identifier(call["call_id"], "call_id")
        if call["status"] not in ("succeeded", "failed", "cancelled"):
            fail("invalid_input", "Invalid observed call status")
        for key in ("input_tokens", "output_tokens", "cache_tokens", "reasoning_tokens"):
            if call[key] is not None:
                integer(call[key], key)
        if call["cost_usd"] is not None:
            try:
                if not isinstance(call["cost_usd"], str) or len(call["cost_usd"]) > 30:
                    raise ValueError("Expected decimal string")
                cost = Decimal(call["cost_usd"])
                if not cost.is_finite() or not 0 <= cost <= 100000:
                    raise ValueError("Invalid cost")
            except (InvalidOperation, ValueError):
                fail("invalid_input", "cost_usd must be nonnegative finite decimal string or null")
        payload = canonical(call)
        with self.transaction():
            self.row(session_id, turn_id)
            duplicate = self.db.execute("SELECT payload FROM usage WHERE turn_id=? AND call_id=?", (turn_id, call["call_id"])).fetchone()
            if duplicate and duplicate[0] != payload:
                fail("usage_conflict", "Call ID already has a different observation")
            self.db.execute("INSERT OR IGNORE INTO usage VALUES(?,?,?)", (turn_id, call["call_id"], payload))
        return self.usage_summary(session_id)

    def invocation(self, session_id, turn_id, invocation_id, tool_name, request_fingerprint):
        identifier(invocation_id, "invocation_id")
        identifier(tool_name, "tool_name")
        if not isinstance(request_fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", request_fingerprint):
            fail("invalid_input", "request_fingerprint must be SHA256 hex")
        with self.transaction():
            row = self.row(session_id, turn_id)
            if row["status"] in ("completed", "failed", "cancelled") or row["result_version"] >= 3:
                fail("terminal_turn", "A finished/exhausted turn cannot begin new Tool invocations")
            if not self.fresh(row):
                fail("stale_context", "Invocation belongs to invalidated turn")
            previous = self.db.execute("SELECT * FROM invocations WHERE turn_id=? AND invocation_id=?", (turn_id, invocation_id)).fetchone()
            if previous:
                if previous["tool_name"] != tool_name or previous["request_hash"] != request_fingerprint:
                    fail("invocation_conflict", "Invocation ID has different tool/input")
                if previous["status"] != "failed" or not previous["retryable"] or previous["attempts"] >= 2:
                    fail("retry_not_allowed", "Invocation is running, completed, nonretryable or exhausted")
                self.db.execute("UPDATE invocations SET attempts=attempts+1,status='running',retryable=0 WHERE turn_id=? AND invocation_id=?", (turn_id, invocation_id))
            else:
                count = self.db.execute("SELECT COUNT(*) FROM invocations WHERE turn_id=?", (turn_id,)).fetchone()[0]
                if count >= 40:
                    fail("tool_call_limit", "At most 40 logical Tool invocations per business turn")
                self.db.execute("INSERT INTO invocations VALUES(?,?,?,?,1,'running',0)", (turn_id, invocation_id, tool_name, request_fingerprint))
            result = dict(self.db.execute("SELECT * FROM invocations WHERE turn_id=? AND invocation_id=?", (turn_id, invocation_id)).fetchone())
        return {**result, "scope": "caller-reported invocation registry; does not execute Tools"}

    def finish_invocation(self, session_id, turn_id, invocation_id, status, retryable):
        identifier(invocation_id, "invocation_id")
        if status not in ("succeeded", "failed", "cancelled") or type(retryable) is not bool or (status != "failed" and retryable):
            fail("invalid_input", "Invalid Tool completion/retry flag")
        with self.transaction():
            self.row(session_id, turn_id)
            row = self.db.execute("SELECT * FROM invocations WHERE turn_id=? AND invocation_id=?", (turn_id, invocation_id)).fetchone()
            if not row or row["status"] != "running":
                fail("invocation_not_running", "Tool invocation must already be running")
            self.db.execute("UPDATE invocations SET status=?,retryable=? WHERE turn_id=? AND invocation_id=?", (status, int(retryable), turn_id, invocation_id))
        return {"invocation_id": invocation_id, "status": status, "technical_retries": row["attempts"] - 1,
                "scope": "caller-reported completion; actual Tool integration is separate"}

    def retrieve(self, kind, exact, query="", limit=12, feature_key=None, offset=0):
        # Validate before cache access. Cached data is not an LLM result.
        self.dataset.check_scope(exact)
        request = {"kind": kind, "scope": exact, "query": query, "limit": limit, "feature_key": feature_key, "offset": offset}
        key = fingerprint({"request": request, "dataset": self.dataset.fingerprint, "code": self.code_hash})
        row = self.db.execute("SELECT payload,payload_hash FROM retrieval_cache WHERE cache_key=?", (key,)).fetchone()
        if row:
            data = strict_json(row[0])
            if fingerprint(data) != row[1]:
                fail("cache_integrity", "Cached retrieval fingerprint changed")
            return {**data, "cache_hit": True}
        result = self.dataset.retrieve(kind, exact, query, limit, feature_key, offset)
        with self.transaction():
            self.db.execute("INSERT OR REPLACE INTO retrieval_cache VALUES(?,?,?)", (key, canonical(result), fingerprint(result)))
        return {**result, "cache_hit": False}
