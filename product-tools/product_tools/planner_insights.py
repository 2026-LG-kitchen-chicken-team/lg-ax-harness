"""Persist authored display text against a reviewed result; never generate prose."""
import hashlib
import os
import sqlite3
import uuid

from .contracts import canonical, fail, fingerprint, obj, strict_json, text

MISSING = object()


class PlannerInsights:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = workspace

    def _authored(self, value, binding, result):
        obj(value, (), ("session_id", "turn_id", "binding", "concept_titles", "summaries"))
        for key in ("session_id", "turn_id", "binding"):
            if key in value and value[key] != (binding if key == "binding" else binding[key]):
                fail("planner_insights_binding", "Authored display text must match the current saved result binding")
        ids = {c["id"] for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in result.get(key, [])}
        concepts = {c["id"] for c in result.get("concepts", [])}
        authored = {}
        for key, allowed, limit in (("concept_titles", concepts, 120), ("summaries", ids, 1000)):
            mapping = value.get(key, {})
            if not isinstance(mapping, dict) or set(mapping) - allowed:
                fail("planner_insights_items", key + " must refer only to current saved item IDs")
            for item, content in mapping.items():
                text(content, key + "." + item, limit)
            authored[key] = mapping
        if len(canonical(authored).encode("utf-8")) > 32768:
            fail("planner_insights_limit", "Authored display text exceeds 32 KiB; keep full evidence in the saved result")
        return authored

    def prepare(self, binding, result, supplied=MISSING):
        """Display failure is separate from successful result/web delivery."""
        try:
            return self._prepare(binding, result, supplied)
        except (OSError, ValueError, sqlite3.Error) as exc:
            return {"ready": False, "status": "failed", "error": {
                "code": getattr(exc, "code", "planner_insights_failed"), "message": str(exc)[:512]}}

    def _prepare(self, binding, result, supplied):
        if supplied is not MISSING and not any(self._authored(supplied, binding, result).values()):
            supplied = MISSING  # The blank candidate template is not authored display text.
        self.store.db.execute("""CREATE TABLE IF NOT EXISTS planner_insights(
            turn_id TEXT NOT NULL REFERENCES turns(turn_id), result_version INTEGER NOT NULL,
            result_sha256 TEXT NOT NULL, content_sha256 TEXT NOT NULL, content TEXT NOT NULL,
            PRIMARY KEY(turn_id,result_version))""")
        row = self.store.db.execute("SELECT * FROM planner_insights WHERE turn_id=? AND result_version=?",
                                    (binding["turn_id"], binding["result_version"])).fetchone()
        if supplied is MISSING and row is None:
            return {"ready": False, "status": "not_provided"}
        if row is not None:
            stored = strict_json(row["content"])
            if row["result_sha256"] != binding["result_sha256"] or fingerprint(stored) != row["content_sha256"]:
                fail("planner_insights_integrity", "Saved display text no longer matches its reviewed result")
            authored = self._authored(stored, binding, result)
            if supplied is not MISSING and self._authored(supplied, binding, result) != authored:
                fail("planner_insights_conflict", "Display text is immutable for this saved result; revise the candidate in the same turn")
        else:
            authored = self._authored(supplied, binding, result)
            self.store.db.execute("INSERT INTO planner_insights VALUES(?,?,?,?,?)", (
                binding["turn_id"], binding["result_version"], binding["result_sha256"], fingerprint(authored), canonical(authored)))
        body = {"session_id": binding["session_id"], "turn_id": binding["turn_id"], "binding": binding, **authored}
        raw = canonical(body).encode("utf-8")
        directory = (self.workspace / "runtime-data/visual-viewer").resolve()
        if not directory.is_relative_to(self.workspace):
            fail("invalid_path", "Display text must remain in this workspace")
        directory.mkdir(parents=True, exist_ok=True)
        target = (directory / ("insights-" + fingerprint(binding) + ".json")).resolve()
        if not target.is_relative_to(directory):
            fail("invalid_path", "Display text must remain in visual-viewer")
        reused = target.exists()
        if reused and target.read_bytes() != raw:
            fail("planner_insights_integrity", "An immutable display sidecar was changed; do not overwrite it")
        if not reused:
            temporary = directory / (".insights-" + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_bytes(raw)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        return {"ready": True, "status": "ready", "path": target.relative_to(self.workspace).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(), "binding": binding, "reused": reused,
                "concept_title_count": len(authored["concept_titles"]), "summary_count": len(authored["summaries"]),
                "semantic_status": "unverified"}
