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
            concepts = [{k: c[k] for k in ("id", "text", "source_ids", "assumptions", "work_draft") if k in c}
                        for c in result["concepts"]]
            notes = result.get("decision_notes", [])
            refs = result["evidence_refs"]
            # These are the sources actually linked by the saved result, not
            # every item delivered from the selected catalog.
            used = list(dict.fromkeys(s for key in ("pains", "existing_features", "remaining_pains", "concepts")
                                     for claim in result[key] for s in claim["source_ids"]))
            used = list(dict.fromkeys(used + [s for note in notes for s in note["source_ids"]]))
            displayed = list(dict.fromkeys([s for c in concepts for s in c["source_ids"]] +
                                          [s for note in notes for s in note["source_ids"]]))
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
            if notes:
                lines.append("판단에 사용한 근거와 한계:")
                labels = {"source_fact": "원문 근거로 기록한 판단(AI 분류)",
                          "ai_interpretation": "AI 해석", "unverified": "미확인"}
                lines.extend(labels[note["basis"]] + ": " + note["text"] for note in notes)
            if displayed:
                lines.append("기획과 판단에 연결한 출처:")
                by_id = {ref["source_id"]: ref for ref in refs}
                for source_id in displayed:
                    ref = by_id[source_id]
                    location = source_id + " · " + ref["location"]
                    url = ref["origin"]["source_url"]
                    lines.append(location + (" · " + url if url else " · 합성 시험자료"))
            if failures:
                lines.append("조사 중 일부 자료에 접근하지 못했습니다. 해당 실패 자체를 성공한 자료로 처리하지 않았습니다.")
            # New authored decisions give a concise human delivery. Keep the
            # complete notes, refs and draft in the artifact, never rewrite
            # source meaning by deleting words from model-authored text.
            decision = result.get("planning_decision")
            if decision is not None:
                lines = [decision["summary"]]
                lines.extend(str(i + 1) + ". " + c["text"] for i, c in enumerate(concepts))
                selected = set(decision["selected_concept_ids"])
                selected_concepts = [c for c in result["concepts"] if c["id"] in selected]
                for concept in selected_concepts:
                    if concept.get("work_draft"):
                        lines.append("업무 초안: " + concept["work_draft"]["title"])
                    if concept.get("implementation_steps"):
                        lines.append("다음 할 일: " + concept["implementation_steps"][0])
                conditions = list(dict.fromkeys(result["assumptions"] +
                    [v for c in concepts for v in c["assumptions"]]))
                if conditions:
                    lines.append("적용 조건: " + " / ".join(conditions))
                lines.extend(result["validation_findings"])
            binding = {"session_id": session, "turn_id": turn, "result_version": version,
                       "result_sha256": fingerprint(result), "context_sha256": current["context_fingerprint"],
                       "code_sha256": self.store.code_hash, "data_sha256": self.store.dataset.fingerprint,
                       "workflow_audit_hash": audit.report_audit_hash(research) if audit.active(research) else None}
            body = {"contract_version": "product-completion-v1", "binding": binding,
                    "status": current["status"], "text": "\n\n".join(lines), "concepts": concepts,
                    **({"planning_decision": decision} if decision is not None else {}),
                    "assumptions": result["assumptions"], "validation_findings": result["validation_findings"],
                    "decision_notes": notes, "evidence_refs": refs, "source_ids": used,
                    "text_source_ids": displayed,
                    "decision_basis_scope": "exact stored model-reported labels; not official quote or semantic certification",
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
