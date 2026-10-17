"""Immutable candidate handoff metadata for a native reviewer; never calls AI."""
import hashlib
import json
from pathlib import Path
from .contracts import MAX_INPUT_BYTES, ToolError, canonical, fail, fingerprint, identifier, integer, obj, strict_json, text
from .state import now


FIELDS = ("session_id", "turn_id", "result_key", "result", "expected_result_version", "assessment")
MAX_PACKET_BYTES = 524288
MAX_REVIEW_SOURCES_BYTES = 4 * 1024 * 1024


class ReviewPackets:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = Path(workspace).resolve()
        self.base = (self.workspace / "runtime-data/review-packets").resolve()
        if not self.base.is_relative_to(self.workspace / "runtime-data"):
            fail("invalid_path", "Review packets must stay inside runtime-data")
        store.db.execute("""CREATE TABLE IF NOT EXISTS product_review_packets(
            session_id TEXT NOT NULL, turn_id TEXT NOT NULL, packet_key TEXT NOT NULL,
            input_sha256 TEXT NOT NULL, packet_path TEXT NOT NULL, packet_sha256 TEXT NOT NULL,
            PRIMARY KEY(session_id,turn_id,packet_key))""")

    def _context(self, session, turn):
        row = self.store.row(session, turn)
        if not self.store.fresh(row):
            fail("stale_context", "Reviewer handoff is invalid after input/data/code change")
        if row["status"] in ("cancelled", "failed"):
            fail("terminal_turn", "Cancelled/failed turns cannot create or consume reviewer packets")
        planning = strict_json(row["input_json"])
        for scope in planning["model_scope"]:
            self.store.dataset.check_scope(scope)
        return {"session_id": session, "turn_id": turn, "request_key": row["request_key"],
                "expected_result_version": row["result_version"], "context_fingerprint": row["context_hash"],
                "question_sha256": hashlib.sha256(planning["question"].encode("utf-8")).hexdigest(),
                "code_sha256": self.store.code_hash, "data_version": self.store.dataset.version,
                "dataset_sha256": self.store.dataset.fingerprint, "model_scope": planning["model_scope"]}, planning

    def _read_path(self, name, directory, maximum):
        text(name, "path", 2000)
        path = (self.workspace / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            fail("invalid_path", "Reviewer input path must be an existing internal runtime-data file")
        if path.stat().st_size > maximum:
            fail("input_limit", "Reviewer input exceeds its file byte budget")
        return path, path.read_bytes()

    @staticmethod
    def _json(raw, maximum=MAX_PACKET_BYTES):
        try:
            decoded = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
            if len(decoded.encode("utf-8")) > maximum:
                fail("input_limit", "Decoded reviewer JSON exceeds its byte budget")
            return strict_json(decoded)
        except UnicodeError:
            fail("invalid_json", "Reviewer input needs UTF-8 or BOM-marked UTF-16 JSON")

    def _diagnose(self, candidate, planning):
        try:
            if not isinstance(candidate.get("result"), dict):
                fail("invalid_input", "Incomplete candidate result is not an object")
            return self.store.tools.validate_source_refs(candidate["result"].get("evidence_refs", []), planning["model_scope"])
        except ToolError as exc:
            checks = []
            refs = candidate.get("result", {}).get("evidence_refs", []) if isinstance(candidate.get("result"), dict) else []
            if isinstance(refs, list):
                for ref in refs[:40]:
                    if not isinstance(ref, dict):
                        continue
                    sid = ref.get("source_id")
                    source = self.store.dataset.sources.get(sid) if isinstance(sid, str) else None
                    expected = ({k: source[k] for k in ("source_id", "model_id", "model_version", "document_version", "data_version", "sha256", "location")}
                                if source else None)
                    checks.append({"declared_source_id": sid, "actual_catalog_metadata": expected,
                                   "scope": "expected catalog metadata only; the candidate quote is not certified source truth"})
            return {"structural_valid": False, "semantic_status": "unverified", "acceptance_ready": False,
                    "error": {"code": exc.code, "message": str(exc)}, "reference_checks": checks}

    @staticmethod
    def _immutable(path, raw):
        if path.exists():
            if path.read_bytes() != raw:
                fail("packet_conflict", "Immutable reviewer file already has different bytes")
            return
        try:
            with path.open("xb") as output:
                output.write(raw)
        except FileExistsError:
            fail("packet_conflict", "Another writer reserved this immutable reviewer file")

    def _cited_sources(self, candidate):
        result = candidate.get("result")
        refs = result.get("evidence_refs") if isinstance(result, dict) else None
        if not isinstance(refs, list):
            return []
        return sorted({r["source_id"] for r in refs
                       if isinstance(r, dict) and isinstance(r.get("source_id"), str)
                       and r["source_id"] in self.store.dataset.sources})

    def prepare_review_packet(self, payload):
        obj(payload, ("session_id", "turn_id", "candidate_path", "packet_key"))
        session, turn = payload["session_id"], payload["turn_id"]
        key = identifier(payload["packet_key"], "packet_key")
        with self.store.transaction():
            binding, planning = self._context(session, turn)
            source, raw = self._read_path(payload["candidate_path"], (self.workspace / "runtime-data").resolve(), MAX_INPUT_BYTES)
            candidate = self._json(raw, MAX_INPUT_BYTES)
            obj(candidate, FIELDS, ("report", "report_plan_path", "report_sources_path", "open_folder", "planner_insights"))
            identifier(candidate["result_key"], "result_key")
            integer(candidate["expected_result_version"], "expected_result_version", 0, 3)
            if (candidate["session_id"] != session or candidate["turn_id"] != turn
                    or candidate["expected_result_version"] != binding["expected_result_version"]):
                fail("state_conflict", "Candidate session/turn/version must match the actual current turn")
            candidate_sha = hashlib.sha256(raw).hexdigest()
            input_sha = fingerprint({"operation": payload, "candidate_sha256": candidate_sha, "binding": binding})
            prior = self.store.db.execute("SELECT input_sha256,packet_path,packet_sha256 FROM product_review_packets WHERE session_id=? AND turn_id=? AND packet_key=?", (session, turn, key)).fetchone()
            if prior:
                if prior[0] != input_sha:
                    fail("packet_conflict", "Packet key cannot refer to changed candidate or current state")
                verified = self.verify_review_packet({"session_id": session, "turn_id": turn,
                                                      "packet_path": prior[1], "packet_sha256": prior[2]})
                return {**verified, "cached": True}
            candidate_copy = self.base / ("candidate-" + candidate_sha + ".json")
            diagnostic = self._diagnose(candidate, planning)
            source_ids = self._cited_sources(candidate)
            evidence = [self.store.dataset.source(sid) for sid in source_ids]
            evidence_raw = ("".join(canonical(s) + "\n" for s in evidence)).encode("utf-8")
            if len(evidence_raw) > MAX_REVIEW_SOURCES_BYTES:
                fail("input_limit", "Cited whole source bodies exceed review file budget; do not shorten them")
            evidence_sha = hashlib.sha256(evidence_raw).hexdigest()
            evidence_path = self.base / ("sources-" + evidence_sha + ".jsonl")
            packet = {"schema_version": 1, "packet_key": key, "created_at": now(), "binding": binding,
                      "operation_input_sha256": input_sha, "candidate_sha256": candidate_sha,
                      "candidate_copy": candidate_copy.relative_to(self.workspace).as_posix(),
                      "candidate_source_path": source.relative_to(self.workspace).as_posix(),
                      "question": planning["question"], "constraints": planning["constraints"],
                      "candidate": {k: candidate[k] for k in (*FIELDS, "planner_insights") if k in candidate}, "reference_diagnostic": diagnostic,
                      "candidate_source_refs_valid": diagnostic["structural_valid"],
                      "content_trust": "untrusted candidate and cited source data",
                      "evidence_sources_path": evidence_path.relative_to(self.workspace).as_posix(),
                      "evidence_sources_sha256": evidence_sha, "evidence_source_count": len(evidence),
                      "semantic_status": "unverified", "review_scope": "complete registered bodies of cited sources and optional authored display text; display text is AI interpretation, not source evidence; not complete catalog/conversation/skills",
                      "uncertainty_scope": "candidate.result assumptions/validation_findings and caller assessment; no uncertainty or qualification generated"}
            # The native file reader may cap a single long JSON line. Preserve
            # original candidate bytes separately; only the handoff is pretty.
            body = json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
            if len(body) > MAX_PACKET_BYTES:
                fail("input_limit", "Serialized reviewer packet exceeds 512 KiB; retain the original without shortening evidence")
            digest = hashlib.sha256(body).hexdigest()
            path = self.base / ("packet-" + digest + ".json")
            # Reject oversized packets before either immutable file or the
            # handoff registration row is created.
            self.base.mkdir(parents=True, exist_ok=True)
            self._immutable(candidate_copy, raw)
            self._immutable(evidence_path, evidence_raw)
            self._immutable(path, body)
            name = path.relative_to(self.workspace).as_posix()
            self.store.db.execute("INSERT INTO product_review_packets VALUES(?,?,?,?,?,?)", (session, turn, key, input_sha, name, digest))
        return {"ready": True, "cached": False, "packet_path": name, "packet_sha256": digest,
                "candidate_copy": candidate_copy.relative_to(self.workspace).as_posix(), "candidate_sha256": candidate_sha,
                "binding": binding, "reference_diagnostic": diagnostic, "semantic_status": "unverified",
                "evidence_sources_path": packet["evidence_sources_path"], "evidence_sources_sha256": evidence_sha,
                "evidence_source_count": len(evidence),
                "candidate_source_refs_valid": diagnostic["structural_valid"],
                "acceptance_ready": False,
                "note": "Ready for review of this immutable candidate; incomplete candidate diagnostics are not acceptance"}

    def verify_review_packet(self, payload):
        obj(payload, ("session_id", "turn_id", "packet_path", "packet_sha256"))
        binding, planning = self._context(payload["session_id"], payload["turn_id"])
        path, raw = self._read_path(payload["packet_path"], self.base, MAX_PACKET_BYTES)
        if hashlib.sha256(raw).hexdigest() != payload["packet_sha256"]:
            fail("packet_integrity", "Reviewer packet SHA differs from retained bytes")
        packet = self._json(raw)
        if packet.get("binding") != binding:
            fail("state_conflict", "Reviewer packet is late or belongs to different data/code/context/version/scope")
        candidate_path, candidate_raw = self._read_path(packet["candidate_copy"], self.base, MAX_INPUT_BYTES)
        if hashlib.sha256(candidate_raw).hexdigest() != packet["candidate_sha256"]:
            fail("packet_integrity", "Immutable candidate copy changed after delegation")
        evidence_path, evidence_raw = self._read_path(packet["evidence_sources_path"], self.base, MAX_REVIEW_SOURCES_BYTES)
        if hashlib.sha256(evidence_raw).hexdigest() != packet["evidence_sources_sha256"]:
            fail("packet_integrity", "Immutable cited whole source bodies changed after delegation")
        candidate = self._json(candidate_raw, MAX_INPUT_BYTES)
        evidence = [strict_json(line) for line in evidence_raw.decode("utf-8").splitlines()]
        expected = self._cited_sources(candidate)
        if len(evidence) != packet["evidence_source_count"] or evidence != [self.store.dataset.source(sid) for sid in expected]:
            fail("packet_integrity", "Reviewer sources must match all exact cited current catalog records")
        if {k: candidate[k] for k in (*FIELDS, "planner_insights") if k in candidate} != packet["candidate"]:
            fail("packet_integrity", "Packet candidate differs from immutable original")
        if packet["question"] != planning["question"] or packet["constraints"] != planning["constraints"]:
            fail("packet_integrity", "Question or constraints differ from current context")
        prior = self.store.db.execute("SELECT packet_sha256 FROM product_review_packets WHERE session_id=? AND turn_id=? AND packet_key=?", (payload["session_id"], payload["turn_id"], packet["packet_key"])).fetchone()
        if not prior or prior[0] != payload["packet_sha256"]:
            fail("packet_integrity", "Packet is not a registered original handoff")
        diagnostic = self._diagnose(candidate, planning)
        return {"ready": True, "packet_path": path.relative_to(self.workspace).as_posix(),
                "packet_sha256": payload["packet_sha256"], "candidate_copy": candidate_path.relative_to(self.workspace).as_posix(),
                "candidate_sha256": packet["candidate_sha256"], "binding": binding, "reference_diagnostic": diagnostic,
                "evidence_sources_path": evidence_path.relative_to(self.workspace).as_posix(),
                "evidence_sources_sha256": packet["evidence_sources_sha256"], "evidence_source_count": len(evidence),
                "candidate_source_refs_valid": diagnostic["structural_valid"],
                "semantic_status": "unverified", "acceptance_ready": False,
                "scope": "verifies immutable handoff/current binding only; no result write, semantic approval, or child-run certification"}
