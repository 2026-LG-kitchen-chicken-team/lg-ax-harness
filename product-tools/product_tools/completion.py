"""Copy a current reviewed result into a short final delivery; never calls AI."""
import hashlib
from pathlib import Path

from .contracts import canonical, fail, fingerprint, identifier, integer, obj, strict_json


def access_failures(events):
    """Keep diagnostics in the audit, without turning arbitrary reason text into links."""
    failed = []
    latest = {}
    for event in events:
        if event.get("kind") == "source_scan":
            latest[event.get("data", {}).get("source_url")] = event
    for event in events:
        data = event.get("data", {})
        if event.get("kind") != "source_scan" or data.get("status") != "inaccessible":
            continue
        key = data.get("source_url")
        if latest.get(key) is not event:
            continue
        failed.append({"source_url": key, "page_label": data.get("page_label", "자료"),
                       "status": "inaccessible", "message": "이 자료에 접근하지 못했습니다.",
                       "diagnostic_link_required": False,
                       "http_status": None,
                       "scope": "recorded access failure; HTTP status is not inferred from free-form reason"})
    return failed


class CompletionSummary:
    def __init__(self, store, workspace):
        self.store = store
        self.workspace = Path(workspace).resolve()

    def get_completion_summary(self, payload):
        obj(payload, ("session_id", "turn_id", "expected_result_version"))
        session = identifier(payload["session_id"], "session_id")
        turn = identifier(payload["turn_id"], "turn_id")
        version = integer(payload["expected_result_version"], "expected_result_version", 1)
        with self.store.transaction():
            current = self.store.get_turn(session, turn)
            if (current["result_version"] != version or not current["valid"]
                    or current["status"] not in ("completed", "held", "needs_input")
                    or current["latest_result"] is None):
                fail("current_state_changed", "Final summary needs the current valid saved result")
            row = self.store.db.execute(
                "SELECT validation_json FROM results WHERE turn_id=? AND result_version=?",
                (turn, version)).fetchone()
            validation = strict_json(row[0])
            if (validation.get("review_required") is not True
                    or validation.get("review", {}).get("can_finalize_reported_result") is not True):
                fail("completion_review_required", "Final summary needs the stored reviewed-result contract")
            result = current["latest_result"]
            from .workflow import WorkflowAudit
            audit = WorkflowAudit(self.store.db, self.workspace)
            research = "research-" + fingerprint([session, current["request_key"]])
            events = audit.events(research) if audit.active(research) else []
            failures = access_failures(events)
            concepts = [{k: c[k] for k in ("id", "text", "source_ids", "assumptions")}
                        for c in result["concepts"]]
            # Exact stored text preserves its qualifications. Never invent a
            # source location/medium, a measured effect or a replacement claim.
            lines = []
            if concepts:
                lines.append("다음 방향의 상품기획을 제안합니다." if current["status"] == "completed"
                             else "다음은 추가 확인이 필요한 상품기획안입니다.")
                lines.extend(str(i + 1) + ". " + c["text"] for i, c in enumerate(concepts))
                assumptions = list(dict.fromkeys(result["assumptions"] +
                                   [v for c in concepts for v in c["assumptions"]]))
                if assumptions:
                    lines.append("적용 전에 확인할 조건: " + " / ".join(assumptions))
                lines.append("실제 제품 구현과 효과 측정 전의 기획안입니다.")
            else:
                lines.append("현재 자료로 확정하지 못한 부분은 다음과 같습니다.")
            if result["validation_findings"]:
                if concepts:
                    lines.append("확정하지 못한 부분과 추가 확인 사항:")
                lines.extend(result["validation_findings"])
            if failures:
                lines.append("조사 중 일부 자료에 접근하지 못했습니다. 해당 실패 자체를 성공한 자료로 처리하지 않았습니다.")
            binding = {"session_id": session, "turn_id": turn, "result_version": version,
                       "result_sha256": fingerprint(result), "context_sha256": current["context_fingerprint"],
                       "code_sha256": self.store.code_hash, "data_sha256": self.store.dataset.fingerprint,
                       "workflow_audit_hash": audit.report_audit_hash(research) if audit.active(research) else None}
            body = {"contract_version": "product-completion-v1", "binding": binding,
                    "status": current["status"], "text": "\n\n".join(lines), "concepts": concepts,
                    "assumptions": result["assumptions"], "validation_findings": result["validation_findings"],
                    "source_ids": list(dict.fromkeys(s for c in concepts for s in c["source_ids"])),
                    "access_failures": failures, "diagnostic_links_required": False,
                    "generation": "exact stored result projection; no model call",
                    "semantic_status": "unverified", "acceptance_ready": False,
                    "scope": "Stops this tool adding new final facts; native free-text replies are not intercepted"}
            raw = canonical(body).encode("utf-8")
            directory = (self.workspace / "runtime-data/completion").resolve()
            if not directory.is_relative_to(self.workspace / "runtime-data"):
                fail("invalid_path", "Completion artifact must stay inside runtime-data")
            directory.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(raw).hexdigest()
            target = directory / ("completion-" + digest + ".json")
            if target.exists():
                if target.read_bytes() != raw:
                    fail("completion_integrity", "An immutable completion artifact changed")
            else:
                with target.open("xb") as output:
                    output.write(raw)
            return {"ready": True, "path": target.relative_to(self.workspace).as_posix(),
                    "sha256": digest, "binding": binding, "text": body["text"],
                    "diagnostic_links_required": False, "access_failure_count": len(failures),
                    "scope": body["scope"]}
