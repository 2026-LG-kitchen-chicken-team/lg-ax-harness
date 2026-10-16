"""Build reader reports from saved planning data and verified source originals.

This module neither researches evidence nor invokes a model. Source identity is
checked here; layout and structural report validation belong to the renderer.
"""
import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import uuid

from .contracts import ToolError, canonical, evidence_ref, fail, identifier, origin, text
from .paths import real_path


SOURCE_FIELDS = {"id", "kind", "title", "text", "url", "location", "model", "synthetic"}
IDENTITY_FIELDS = ("model_id", "model_version", "document_version", "data_version",
                   "location", "sha256", "synthetic", "origin")
CLAIM_SECTIONS = (("pains", "확인된 고객 불편"), ("existing_features", "현재 기능 검토"),
                  ("remaining_pains", "남은 불편"))
STATUS_LABELS = {"completed": "기획 초안 완료", "held": "기획 보류", "needs_input": "추가 입력 필요",
                 "failed": "실패", "cancelled": "취소"}
BASIS_LABELS = {"source_fact": "출처 기반 판단", "ai_interpretation": "AI 해석", "unverified": "미확인"}


def _source_records(sources):
    if isinstance(sources, dict):
        records = list(sources.values())
    elif isinstance(sources, (list, tuple)):
        records = list(sources)
    else:
        fail("invalid_report_sources", "sources must be original source records")
    normalized, originals = [], {}
    for record in records:
        if not isinstance(record, dict):
            fail("invalid_report_sources", "Each source must be an object")
        raw = "source_id" in record
        sid = identifier(record.get("source_id") if raw else record.get("id"), "source id")
        if sid in originals:
            fail("invalid_report_sources", "Duplicate source identity: " + sid)
        if raw:
            for key in (*IDENTITY_FIELDS, "kind", "text"):
                if key not in record:
                    fail("invalid_report_sources", "Original source is missing " + key)
            for key in ("model_id", "model_version", "document_version", "data_version"):
                identifier(record[key], key)
            text(record["text"], "source text", 4000)
            text(record["location"], "source location", 200)
            if type(record["synthetic"]) is not bool:
                fail("invalid_report_sources", "Original source synthetic must be explicit")
            origin(record["origin"], record["synthetic"])
            digest = hashlib.sha256(record["text"].encode("utf-8")).hexdigest()
            if record["sha256"] != digest:
                fail("report_source_integrity", "Original source text fingerprint differs: " + sid)
            kind = "product_document" if record["kind"] == "product_fact" else record["kind"]
            item = {"id": sid, "kind": kind,
                    "title": record["model_id"] + " · " + record["location"],
                    "text": record["text"], "location": record["location"],
                    "model": "모델 {model_id} / 모델 버전 {model_version} / 문서 버전 {document_version} / 자료 버전 {data_version}".format(**record),
                    "synthetic": record["synthetic"]}
            provenance = record["origin"]
            labels = {True: "확인", False: "아님", None: "미확인"}
            item["model"] += (" / 관찰일: " + (provenance["retrieved_date"] or "미확인")
                              + " / 게시일: " + (provenance["published_date"] or "미확인")
                              + " / 표현: " + provenance["representation"]
                              + " / 모델 연결: " + (provenance["model_matching"] or "미확인")
                              + " / 구매 인증: " + labels[provenance["purchase_verified"]]
                              + " / 협찬: " + labels[provenance["sponsorship"]])
            if provenance.get("commercial_disclosure"):
                item["model"] += " / 상업성 표시: " + provenance["commercial_disclosure"]
            if record["origin"]["source_url"] is not None:
                item["url"] = record["origin"]["source_url"]
        else:
            # Canonical sources are useful for genuinely supplied survey,
            # interview or other evidence not represented by the model catalog.
            if not {"id", "kind", "title", "text"} <= record.keys() or record.keys() - SOURCE_FIELDS:
                fail("invalid_report_sources", "Unexpected canonical source fields")
            item = copy.deepcopy(record)
            if "synthetic" in item and type(item["synthetic"]) is not bool:
                fail("invalid_report_sources", "Source synthetic must be boolean when supplied")
        for key in ("kind", "title", "text"):
            text(item[key], "source " + key, 1000000)
        for key in ("url", "location", "model"):
            if key in item:
                text(item[key], "source " + key, 1000000)
        normalized.append(item)
        originals[sid] = copy.deepcopy(record)
    return normalized, originals


def _verify_saved_evidence(planning, result, originals):
    scopes = {canonical(s) for s in planning.get("model_scope", [])}
    for record in originals.values():
        if "source_id" not in record:
            continue
        exact = {key: record[key] for key in ("model_id", "model_version", "document_version")}
        if scopes and canonical(exact) not in scopes:
            fail("report_source_scope", "Source falls outside the saved planning scope")
        if planning.get("data_version") is not None and record["data_version"] != planning["data_version"]:
            fail("report_source_scope", "Source data version differs from saved planning")
    seen = set()
    for ref in result.get("evidence_refs", []):
        evidence_ref(ref)
        sid = ref["source_id"]
        if sid in seen:
            fail("report_source_integrity", "Duplicate saved evidence reference")
        seen.add(sid)
        record = originals.get(sid)
        if record is None or "source_id" not in record:
            fail("report_source_integrity", "Saved evidence has no matching original source: " + sid)
        if any(ref[key] != record[key] for key in IDENTITY_FIELDS):
            fail("report_source_integrity", "Saved evidence identity differs from original: " + sid)
        if ref["quote"] not in record["text"]:
            fail("report_source_integrity", "Saved quote is not an exact original excerpt: " + sid)
    for key in ("pains", "existing_features", "remaining_pains", "concepts", "decision_notes"):
        for record in result.get(key, []):
            if not set(record.get("source_ids", [])) <= seen:
                fail("report_source_integrity", "Saved claim has no validated evidence reference")


def _verify_plan_links(plan, available, planning):
    required = {"title", "summary", "sources", "sections"}
    if not isinstance(plan, dict) or not required <= plan.keys() or plan.keys() - required - {"unfulfilled_requests"}:
        fail("invalid_report_plan", "Expected title, summary, sources and sections")
    text(plan["title"], "report title", 1000000)
    if not isinstance(plan["summary"], list) or not isinstance(plan["sections"], list) or not isinstance(plan["sources"], list):
        fail("invalid_report_plan", "Report summary, sources and sections must be arrays")
    for paragraph in plan["summary"]:
        text(paragraph, "summary paragraph", 1000000)
    seen = set()
    for supplied in plan["sources"]:
        if not isinstance(supplied, dict) or not {"id", "kind", "title", "text"} <= supplied.keys() or supplied.keys() - SOURCE_FIELDS:
            fail("invalid_report_plan", "Expected exact source schema")
        sid = supplied["id"]
        if not isinstance(sid, str) or sid not in available or sid in seen:
            fail("report_source_integrity", "Authored report added an unknown or duplicate original source")
        seen.add(sid)
        original = available[sid]
        if any(key not in original or value != original[key] for key, value in supplied.items()):
            fail("report_source_integrity", "Authored source differs from verified original: " + sid)
    for section in plan["sections"]:
        if not isinstance(section, dict) or set(section) != {"title", "blocks"} or not isinstance(section["blocks"], list):
            fail("invalid_report_plan", "Expected section title and blocks")
        text(section["title"], "section title", 1000000)
        for block in section["blocks"]:
            if not isinstance(block, dict) or block.get("type") not in ("paragraph", "table", "chart"):
                fail("invalid_report_plan", "Unknown report block")
            ids = block.get("source_ids", [])
            if not isinstance(ids, list) or any(not isinstance(s, str) or s not in available for s in ids) or len(set(ids)) != len(ids):
                fail("report_source_integrity", "Report block must cite verified original sources")
    requests = plan.get("unfulfilled_requests", [])
    if not isinstance(requests, list):
        fail("invalid_report_plan", "unfulfilled_requests must be an array")
    for item in requests:
        if not isinstance(item, dict) or set(item) != {"request", "reason"}:
            fail("invalid_report_plan", "Expected unfulfilled request and reason")
        text(item["request"], "unfulfilled request", 1000000)
        text(item["reason"], "unfulfilled reason", 1000000)
        if item["request"] not in planning.get("question", ""):
            fail("invalid_report_plan", "An unfulfilled request must quote the actual saved request")


def _paragraph(value, source_ids=None):
    block = {"type": "paragraph", "text": value}
    if source_ids:
        block["source_ids"] = copy.deepcopy(source_ids)
    return block


def _default_plan(planning, result, normalized):
    status = STATUS_LABELS.get(result.get("status"), result.get("status", ""))
    summary = ["저장된 업무 결과: " + status]
    sections = []
    request = [_paragraph(planning["question"])]
    for key, label in (("target_customer", "대상 고객"), ("context", "업무 맥락")):
        if planning.get(key):
            request.append(_paragraph(label + ": " + planning[key]))
    if planning.get("model_scope"):
        request.append({"type": "table", "title": "검토 대상과 자료 버전",
                        "columns": ["모델", "모델 버전", "문서 버전", "자료 버전"],
                        "rows": [[s["model_id"], s["model_version"], s["document_version"], planning.get("data_version", "")]
                                 for s in planning["model_scope"]]})
    sections.append({"title": "업무 요청", "blocks": request})
    for key, title in CLAIM_SECTIONS:
        records = result.get(key, [])
        if records:
            sections.append({"title": title, "blocks": [_paragraph(c["text"], c["source_ids"]) for c in records]})
    for number, concept in enumerate(result.get("concepts", []), 1):
        blocks = [_paragraph(concept["text"], concept["source_ids"])]
        for key, label in (("requirements", "요구 조건"), ("implementation_steps", "구현 단계"), ("assumptions", "제안의 전제")):
            if concept.get(key):
                blocks.append({"type": "table", "title": label, "columns": [label], "rows": [[v] for v in concept[key]],
                               "source_ids": copy.deepcopy(concept["source_ids"])})
        validation = concept.get("validation_plan")
        if validation:
            names = (("metric", "지표"), ("baseline", "기준선"), ("method", "측정 방법"),
                     ("success_criterion", "성공 기준"), ("business_value", "기대 업무 가치"))
            blocks.append({"type": "table", "title": "효과 검증 계획 (미측정)", "columns": ["항목", "계획"],
                           "rows": [[label, validation[key]] for key, label in names if key in validation],
                           "source_ids": copy.deepcopy(concept["source_ids"])})
        sections.append({"title": "제안 " + str(number), "blocks": blocks})
    notes = result.get("decision_notes", [])
    if notes:
        sections.append({"title": "판단과 보류 사유", "blocks": [
            _paragraph(BASIS_LABELS.get(n["basis"], n["basis"]) + ": " + n["text"], n["source_ids"]) for n in notes]})
    for key, title in (("assumptions", "기획 전제"), ("validation_findings", "검토 결과")):
        if result.get(key):
            sections.append({"title": title, "blocks": [_paragraph(v) for v in result[key]]})
    return {"title": "상품기획 검토 보고서", "summary": summary, "sources": normalized, "sections": sections}


def build_report_plan(planning, result, sources, authored_plan=None):
    """Preserve saved content or authored sections, never create source facts.

    ``sources`` must come from validated originals. Authored source entries may
    omit optional metadata; supplied metadata must agree exactly. Full originals
    are rebuilt into the report, including explicit synthetic and version labels.
    Detailed block/layout validation is performed by ``render_report``.
    """
    if not isinstance(planning, dict) or not isinstance(result, dict):
        fail("invalid_report_plan", "Saved planning and result objects are required")
    text(planning.get("question"), "saved question", 1000000)
    normalized, originals = _source_records(sources)
    _verify_saved_evidence(planning, result, originals)
    available = {s["id"]: s for s in normalized}
    plan = copy.deepcopy(authored_plan) if authored_plan is not None else _default_plan(planning, result, normalized)
    _verify_plan_links(plan, available, planning)
    plan["sources"] = normalized
    return plan


def _open_in_explorer(directory):
    if sys.platform != "win32" or os.name != "nt":
        return False, None
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not system_root:
        return False, {"code": "folder_open_failed", "message": "Windows system directory is unavailable"}
    executable = Path(system_root) / "explorer.exe"
    try:
        if not executable.is_file():
            raise OSError("Windows Explorer executable is unavailable")
        subprocess.Popen([str(executable), str(directory)], shell=False)
        return True, None
    except OSError as exc:
        return False, {"code": "folder_open_failed", "message": str(exc)[:512]}


def _failure(directory, code, message):
    errors = [{"code": code, "message": str(message)[:512]}]
    return {"ready": False, "directory": str(directory) if directory else None, "files": [],
            "checks": {"errors": errors, "structure_verified": False}, "errors": errors,
            "folder_opened": False, "folder_open_error": None}


def create_deliverables(workspace, planning, result, sources, authored_plan=None, open_folder=True):
    """Publish a new report folder and return actual renderer success/errors.

    Current-version/cancellation and replay checks remain the caller's job. An
    error here does not undo the caller's saved planning result.
    """
    destination = None
    try:
        plan = build_report_plan(planning, result, sources, authored_plan)
        root = real_path(workspace)
        if not root.is_dir():
            fail("invalid_path", "Report workspace must be a directory")
        base = (root / "runtime-data" / "deliverables").resolve()
        metadata = (root / "runtime-data" / "deliverable-metadata").resolve()
        if not base.is_relative_to(root) or not metadata.is_relative_to(root):
            fail("invalid_path", "Report paths must stay inside the workspace runtime-data")
        base.mkdir(parents=True, exist_ok=True)
        metadata.mkdir(parents=True, exist_ok=True)
        for _ in range(10):
            name = "report-" + uuid.uuid4().hex
            candidate = base / name
            plan_path = metadata / (name + ".json")
            if not candidate.exists() and not plan_path.exists():
                destination = candidate
                break
        if destination is None:
            fail("report_directory_collision", "Could not allocate a fresh report directory")
        # Exclusive creation protects existing internal metadata too. No report
        # JSON is placed in the reader's deliverables directory.
        with plan_path.open("x", encoding="utf-8") as handle:
            handle.write(canonical({"report_plan": plan, "planning": planning,
                                    "result_sha256": hashlib.sha256(canonical(result).encode("utf-8")).hexdigest()}))
        from .reporting import render_report
        rendered = render_report(plan, destination)
        if (not isinstance(rendered, dict) or type(rendered.get("ready")) is not bool
                or not isinstance(rendered.get("files"), list) or not isinstance(rendered.get("checks"), dict)
                or not isinstance(rendered.get("directory"), str)
                or Path(rendered["directory"]).resolve() != destination):
            fail("invalid_report_response", "Renderer returned an invalid result")
        response = copy.deepcopy(rendered)
        errors = response.get("errors", response.get("checks", {}).get("errors", []))
        response.update(errors=errors, folder_opened=False, folder_open_error=None,
                        plan_path=plan_path.relative_to(root).as_posix())
        if response["ready"]:
            files = response["files"]
            for file in files:
                if not isinstance(file, dict) or not isinstance(file.get("path"), str):
                    fail("invalid_report_response", "Renderer returned an invalid file record")
                path = Path(file["path"]).resolve()
                if not path.is_relative_to(destination) or not path.is_file():
                    fail("report_files_missing", "Renderer did not publish its declared file inside the new report folder")
            if not files or not {".docx", ".pdf"} <= {Path(f["path"]).suffix.lower() for f in files}:
                fail("report_files_missing", "Final Word and PDF files were not both published")
            if open_folder:
                response["folder_opened"], response["folder_open_error"] = _open_in_explorer(destination)
        return response
    except ToolError as exc:
        return _failure(destination, exc.code, str(exc))
    except ImportError as exc:
        return _failure(destination, "report_dependency_unavailable", str(exc))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return _failure(destination, "report_generation_failed", str(exc))
