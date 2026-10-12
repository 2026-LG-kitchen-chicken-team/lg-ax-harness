"""File-backed bounded import; keeps originals and partial progress, no AI calls."""
import hashlib
from pathlib import Path
from .contracts import ToolError, canonical, fail, fingerprint, identifier, obj, strict_json, text
from .dataset import Dataset
from .workflow import WorkflowAudit
from .state import code_fingerprint


MAX_IMPORT_BYTES = 16 * 1024 * 1024


class BulkImporter:
    def __init__(self, web):
        self.web = web
        self.web.db.execute("CREATE TABLE IF NOT EXISTS bulk_import_jobs(import_key TEXT PRIMARY KEY, input_sha256 TEXT NOT NULL, base_sha256 TEXT NOT NULL, result TEXT NOT NULL)")
        self.web.db.commit()

    def run(self, dataset, payload):
        obj(payload, ("input_path", "import_key"), ("data_version",))
        key = identifier(payload["import_key"], "import_key")
        runtime = (self.web.workspace / "runtime-data").resolve()
        text(payload["input_path"], "input_path", 2000)
        path = (self.web.workspace / payload["input_path"]).resolve()
        if not path.is_relative_to(runtime) or not path.is_file():
            fail("invalid_path", "Bulk originals must be existing files inside runtime-data")
        if path.stat().st_size > MAX_IMPORT_BYTES:
            fail("input_limit", "Bulk original JSON exceeds 16 MiB")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        old = self.web.db.execute("SELECT input_sha256,base_sha256,result FROM bulk_import_jobs WHERE import_key=?", (key,)).fetchone()
        if old:
            if old[0] != digest or old[1] != dataset.fingerprint:
                fail("import_conflict", "Import key is bound to its original bytes and starting catalog")
            result = strict_json(old[2])
            if result.get("code_sha256") != code_fingerprint() or result.get("operation_input_sha256") != fingerprint(payload):
                fail("import_conflict", "Import replay cannot reuse changed code or operation parameters")
            if hashlib.sha256((self.web.workspace / result["original_copy"]).read_bytes()).hexdigest() != digest:
                fail("input_integrity", "Preserved original bytes changed")
            if result.get("last_valid_catalog"):
                check = Dataset(self.web.workspace / result["last_valid_catalog"])
                if check.fingerprint != result["last_valid_fingerprint"]:
                    fail("dataset_integrity", "Retained import catalog changed")
            return {**result, "status": "interrupted" if result["status"] == "running" else result["status"],
                    "cached": True, "next_action": "Retain prior success/failure; no automatic restart or retry"}
        try:
            original = strict_json(raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"))
        except UnicodeError:
            fail("invalid_json", "Bulk original must be UTF-8 or BOM-marked UTF-16 JSON")
        obj(original, ("data_version", "observations"), ("new_models", "research_id"))
        version = identifier(payload.get("data_version", original["data_version"]), "data_version")
        if len(version) > 80:
            fail("invalid_input", "Bulk version prefix must fit immutable batch suffixes (<=80 chars)")
        observations = original["observations"]
        models = original.get("new_models", [])
        if not isinstance(observations, list) or not 1 <= len(observations) <= 1000 or not isinstance(models, list) or len(models) > 20:
            fail("invalid_input", "Bulk requires 1..1000 observations and at most 20 exact new scopes")
        ids = [identifier(entry.get("source_id"), "source_id") for entry in observations if isinstance(entry, dict)]
        if len(ids) != len(observations) or len(set(ids)) != len(ids):
            fail("invalid_input", "Bulk source IDs must be distinct objects")
        research = original.get("research_id")
        if research:
            audit = WorkflowAudit(self.web.db, self.web.workspace)
            audit.request(research)
        else:
            audit = None
        for model in models:
            if not isinstance(model, dict):
                fail("invalid_input", "Each new model must be an object")
            identifier(model.get("spec_source_id"), "spec_source_id")
        identities = {model["spec_source_id"]: model for model in models}
        if len(identities) != len(models) or not set(identities) <= set(ids):
            fail("identity_mismatch", "Each new exact scope needs its own original identity observation")
        ordered = [i for i, entry in enumerate(observations) if entry["source_id"] in identities]
        ordered += [i for i, entry in enumerate(observations) if entry["source_id"] not in identities]
        folder = runtime / "bulk-imports"
        if not folder.resolve().is_relative_to(runtime):
            fail("invalid_path", "Audit directory escapes runtime-data")
        folder.mkdir(parents=True, exist_ok=True)
        audit_path = folder / ("import-" + fingerprint(key) + ".json")
        original_copy = folder / ("original-" + digest + ".json")
        if original_copy.exists() and hashlib.sha256(original_copy.read_bytes()).hexdigest() != digest:
            fail("input_integrity", "Preserved original copy changed")
        if not original_copy.exists():
            original_copy.write_bytes(raw)
        result = {"import_key": key, "input_sha256": digest, "code_sha256": code_fingerprint(),
                  "operation_input_sha256": fingerprint(payload), "input_path": path.relative_to(self.web.workspace).as_posix(),
                  "original_copy": original_copy.relative_to(self.web.workspace).as_posix(),
                  "audit_path": audit_path.relative_to(self.web.workspace).as_posix(), "input_count": len(observations),
                  "completed_count": 0, "unprocessed_count": len(observations), "failed_source_ids": [],
                  "status": "running", "cached": False, "last_valid_catalog": None,
                  "last_valid_fingerprint": dataset.fingerprint, "last_valid_data_version": dataset.version,
                  "semantic_status": "unverified", "acceptance_ready": False,
                  "counts_are": "source records, not distinct customers or semantic sufficiency"}
        history = []
        def persist():
            body = {**result, "research_id": research, "base_fingerprint": dataset.fingerprint,
                    "input_order_source_ids": ids, "registration_order_input_indices": ordered,
                    "batches": history, "ordering": "identity sources first; other originals retain their relative input order"}
            temp = audit_path.with_suffix(".tmp")
            temp.write_text(canonical(body), encoding="utf-8")
            temp.replace(audit_path)
            self.web.db.execute("INSERT OR REPLACE INTO bulk_import_jobs VALUES(?,?,?,?)", (key, digest, dataset.fingerprint, canonical(result)))
            self.web.db.commit()
        current, cursor = dataset, 0
        persist()
        while cursor < len(ordered):
            selected = []
            batch_number = len(history)+1
            batch = {"data_version": version + "-b" + str(batch_number).zfill(4), "observations": [], "new_models": []}
            if research:
                batch["research_id"] = research
            try:
                if audit:
                    request = audit.request(research)
                    if request[2] is not None:
                        turn = self.web.db.execute("SELECT status FROM turns WHERE turn_id=?", (request[2],)).fetchone()
                        if turn and turn[0] in ("cancelled", "failed"):
                            fail("terminal_turn", "The original turn is cancelled/failed; do not import into a replacement request")
                    if audit.active(research):
                        status = audit.status(research)
                        if status["expired"] or status["finished_at"]:
                            fail("workflow_expired", "Expired/finished original workflow cannot start another registration batch")
                # Register manufacturer identities before touching dependent
                # reviews/manual observations; a late bad review cannot discard
                # an already-valid identity catalog.
                end = min(cursor+10, len(identities)) if cursor < len(identities) else cursor+10
                for index in ordered[cursor:end]:
                    entry = observations[index]
                    batch["observations"].append(entry)
                    model = identities.get(entry["source_id"])
                    if model:
                        batch["new_models"].append(model)
                    if len(canonical(batch).encode("utf-8")) > 64000:
                        batch["observations"].pop()
                        if model:
                            batch["new_models"].pop()
                        break
                    selected.append(index)
                if not selected:
                    fail("input_limit", "One original source exceeds the single-import contract; original text was not shortened")
                imported = self.web.import_evidence(current, batch)
                current = Dataset(self.web.workspace / imported["data_path"])
                history.append({"status": "completed", "input_indices": selected, "source_ids": [ids[i] for i in selected],
                                "batch_sha256": fingerprint(batch), **imported, "dataset_fingerprint": current.fingerprint})
                cursor += len(selected)
                result.update(completed_count=cursor, unprocessed_count=len(ordered)-cursor,
                              last_valid_catalog=imported["data_path"], last_valid_fingerprint=current.fingerprint,
                              last_valid_data_version=current.version)
                persist()
            except (ToolError, OSError) as exc:
                code = exc.code if isinstance(exc, ToolError) else "io_error"
                failed = selected or [ordered[cursor]]
                result.update(status="partial_failure" if cursor else "failed", failed_source_ids=[ids[i] for i in failed],
                              failed_source_id_precision="failed atomic batch; exact offending record may be unobserved",
                              error={"code": code, "message": str(exc)[:512]},
                              next_action="Preserve the last valid catalog and original request; inspect failed batch audit before explicit correction")
                history.append({"status": "failed", "input_indices": failed, "source_ids": [ids[i] for i in failed],
                                "batch_sha256": fingerprint(batch), "error": result["error"]})
                persist()
                return result
        result.update(status="completed", next_action="Use last_valid_catalog with the same request's resolve_request_bundle; inspect inventory, then review all original records")
        persist()
        return result
