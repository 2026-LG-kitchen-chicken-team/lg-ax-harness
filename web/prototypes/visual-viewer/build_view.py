"""하네스 세션 export를 시각자료 뷰어(index.html)가 읽는 view-data.js로 바꾼다.

    python build_view.py \
        --export <하네스 runtime-data/exports의 세션 JSON> \
        --insights insights-<model>.json \
        [--focus dashboard] [--standalone report.html] [--open]

    # export 전, 작업 중간에 모델이 쓴 화면만 보여줄 때
    python build_view.py --insights <pages가 있는 JSON> --focus <화면 id>

    # 하네스 안의 자동 갱신(hook.py)·수동 열기(viewer.py open)는 이 모듈의 generate()를 부른다.

Python 3.10 이상, 표준 라이브러리만 쓴다. 하네스 폴더에서는 `uv run python`으로 실행해도 된다.

- export: export_session이 만든 세션 기록. 상태·근거·사용량·검토 기록은 여기서 그대로 읽는다.
- insights: CLI의 모델이 쓴 해석(의견 묶음, 단계 자막, 제외 사유 등)과 직접 쓴 화면(pages). 묶음 건수는 source_id 목록 길이로 센다.
- 이 스크립트는 생성·판단을 하지 않는다. 읽고, 세고, 화면 블록으로 배치만 한다. 형식은 README.md에 있다.
- 브라우저에 뷰어를 열어 둔 채 다시 실행하면 화면이 2초 안에 새 데이터로 바뀐다(로컬 파일일 때).
- 현재 결과는 저장 도구가 승인한 결과(state.latest_result)다. 거절 후보는 사유와 함께 기록에만 둔다.
- insights는 session_id와(있으면) turn_id가 맞고 가리키는 근거 ID가 현재 결과에 있을 때만 쓴다. 아니면 근거
  대시보드에 의견 묶음에는 insights가 필요하다는 안내를 넣는다. 화면 생성 경고는 화면에도 보인다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import webbrowser
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))

TYPE_LABEL = {"REVIEW": "후기", "REV": "후기", "MANUAL": "설명서", "SPEC": "스펙", "PART": "소모품", "DOC": "문서"}
# 하네스가 근거마다 종류(kind)를 넣으면 그 값을 먼저 쓴다(이슈 #8 제안: review / product_fact / manual 등).
# 모르는 값은 그대로 '미지원(값)'으로 두고 후기로 세지 않는다.
KIND_LABEL = {"review": "후기", "product_fact": "제품 사실", "manual": "설명서", "spec": "스펙", "part": "소모품", "document": "문서"}
# source_id 접두어가 하네스 관례가 아니면 원문 표현(origin.representation)으로만 나눈다. 후기라고 단정하지 않는다.
REPRESENTATION_TYPE = {"factual_summary": "제품 사실", "excerpt": "원문 발췌"}
TYPE_ORDER = ("후기", "설명서", "스펙", "소모품", "문서", "제품 사실", "원문 발췌", "기타")
TYPE_TONE = {"후기": "blue", "설명서": "purple", "스펙": "green", "소모품": "orange", "문서": "purple", "제품 사실": "green",
             "원문 발췌": "gray", "기타": "gray"}
STATUS_TONE = {"completed": "green", "held": "orange", "needs_input": "orange", "failed": "red", "cancelled": "gray",
               "needs_revision": "orange", "pending": "gray", "research_required": "orange"}
STATUS_LABEL = {"completed": "기획 초안 완료", "held": "보류", "needs_input": "입력 필요", "failed": "실패", "cancelled": "취소",
                "needs_revision": "수정 필요", "pending": "진행 중", "research_required": "조사 필요"}
SCOPE_MODE = {"exact_model": "정확 모델", "family_catalog": "제품군 카탈로그"}
SCOPE_SHORT = {"exact_model": "모델 지정", "family_catalog": "제품군"}  # 개요의 큰 글씨 칸용. 원래 이름은 설명 줄에 둔다.
USAGE_STATUS = {"unknown": "미측정", "measured": "측정", "partially_measured": "일부 측정"}
FAMILY = {"refrigerator": ("냉장고", "🧊"), "microwave": ("전자레인지", "🍲"), "dishwasher": ("식기세척기", "🍽️")}
PLAN_STATUS = {"planned_not_measured": "실측 전"}
PLAN_FIELDS = [("metric", "지표"), ("baseline", "기준선"), ("method", "방법"), ("success_criterion", "성공 기준"), ("business_value", "사업 가치")]
CLAIM_TONE = {"P": "red", "F": "blue", "RP": "orange", "C": "purple"}
CLAIM_KIND = {"P": "현재 불편", "F": "기존 기능", "RP": "남은 불편", "C": "제안"}
MATCHING_LABEL = {"explicit_model_verified": "모델 명시 확인", "product_page_association": "제품 페이지 연관", "fictional": "가상(합성)"}
BASIS = {"source_fact": ("원문 사실", "green"), "ai_interpretation": ("AI 해석", "purple"), "unverified": ("미확인", "orange")}
INSIGHTS_HINT = "runtime-data/visual-viewer/insights-<이름>.json"
INSIGHTS_WHY = {
    "missing": "이 세션과 session_id가 같은 insights 파일이 없습니다.",
    "mismatch": "insights 파일의 session_id가 이 export와 달라 쓰지 않았습니다.",
    "other_turn": "같은 세션의 insights는 있지만 다른 turn(turn_id)용이라 쓰지 않았습니다.",
    "stale": "insights가 현재 결과에 없는 근거 ID를 가리켜(다른 turn용으로 보임) 쓰지 않았습니다.",
    "unbound": "같은 세션의 insights는 있지만 turn_id가 없고 이 세션에 turn이 여러 개라, 어느 turn의 해석인지 알 수 없어 쓰지 않았습니다.",
    "invalid": "insights 파일의 형식이 README의 insights 형식과 달라 쓰지 않았습니다.",
    "unverified_binding": "현재 결과의 버전·코드·자료·조사 지문과 같은 binding이 없어 해석을 적용하지 않았습니다.",
    "unverified_delivery": "현재 웹 전달을 검증하지 못해 해석을 적용하지 않았습니다.",
}
# 기획자에게 보이는 이유(한 줄). 파일·ID가 든 자세한 이유(INSIGHTS_WHY)는 접힌 운영 안내에 둔다.
INSIGHTS_WHY_PLAIN = {
    "missing": "이 결과에 맞는 AI 해석 파일이 없습니다.",
    "mismatch": "AI 해석 파일이 다른 세션의 것이라 쓰지 않았습니다.",
    "other_turn": "AI 해석 파일이 같은 세션의 다른 질문용이라 쓰지 않았습니다.",
    "stale": "AI 해석 파일이 이 결과에 없는 근거를 가리켜(다른 질문용으로 보임) 쓰지 않았습니다.",
    "unbound": "AI 해석 파일에 어느 질문용인지 적혀 있지 않고 이 세션에는 질문이 여러 개라 쓰지 않았습니다.",
    "invalid": "AI 해석 파일의 형식이 맞지 않아 쓰지 않았습니다.",
    "unverified_binding": "현재 결과와 같은 버전·조사 기록의 해석인지 확인하지 못했습니다.",
    "unverified_delivery": "현재 전달이 검증되지 않아 해석을 적용하지 않았습니다.",
}
INSIGHTS_APPLIED = {"matched": "turn_id 일치", "single_turn": "turn이 하나뿐인 세션", "given": "직접 지정",
                    "unverified_turn": "직접 지정 · turn 미확인"}
SEMANTIC_LABEL = {"unverified": "의미 검토 전"}
RESOLUTION_LABEL = {"resolved": "해소", "partially_resolved": "일부 해소", "unresolved": "미해소", "uncertain": "불확실"}
RESOLUTION_TONE = {"resolved": "green", "partially_resolved": "blue", "unresolved": "red", "uncertain": "orange"}
SUPPORT_LABEL = {"supported": "뒷받침됨", "partially_supported": "일부 뒷받침", "unsupported": "뒷받침 안 됨", "uncertain": "불확실"}
SUPPORT_TONE = {"supported": "green", "partially_supported": "blue", "unsupported": "red", "uncertain": "orange"}
SCOPE_RELATION_LABEL = {"current_model": "현재 모델", "unclear": "모델 불명확", "other_model": "다른 모델"}

HARNESS_STEPS = [
    {"icon": "📚", "title": "자료 조회", "text": "선택한 모델의 저장된 리뷰·공식 사양·설명서를 정확한 버전으로 조회합니다. `evidence-retrieval`"},
    {"icon": "🌐", "title": "웹 근거 수집", "text": "저장 근거가 부족하거나 갱신이 필요할 때 실제 후기 원문과 공식 자료를 확보합니다. `web-evidence-collection`"},
    {"icon": "🧩", "title": "불편 구조화", "text": "후기에서 현재 제품의 불편·사용 맥락·상충 의견을 원문 근거에 연결합니다. `needs-structuring`"},
    {"icon": "⚖️", "title": "기능 대조", "text": "불편을 같은 모델의 기존 기능·사용 조건과 대조해 남은 문제를 판단합니다. `feature-comparison`"},
    {"icon": "💡", "title": "콘셉트 작성", "text": "근거 있는 남은 불편에만 조건을 지키는 제안을 씁니다. `concept-writing`"},
    {"icon": "✅", "title": "검토·저장", "text": "원문 의미·모델·기능 중복·가정·제약을 검토하고 최초 1회와 수정 최대 2회를 저장합니다. `review-and-revise`"},
]

DEFAULT_CAPTIONS = {
    "story": ("한눈에: 질문에서 제안까지", "저장된 결과만 보여주며 모델이나 업무를 다시 실행하지 않습니다."),
    "overview": ("입력: 모델과 질문, 저장 제약을 확인합니다", "질문 원문과 저장된 실행 제약을 구분해 보여줍니다."),
    "dashboard": ("근거: 결과에 쓴 근거 {evidence}건과 검토 판단을 셉니다", "관측 건수이며 발생률이나 시장 수요가 아닙니다."),
    "screening": ("선별: 결과에 쓴 원문 근거", "인용은 저장된 원문 그대로이며 화면이 고치지 않습니다."),
    "compare": ("대조: 불편을 같은 모델의 기존 기능과 맞춰 봅니다", "기능이 있다고 불편이 해소된 것은 아닙니다."),
    "concepts": ("제안: 남은 불편에 연결한 제안", "효과·비용은 측정 전 미확정입니다."),
    "history": ("기록: 질문 {turns}개의 상태와 근거 수 변화", "보류 {held}건, 기획 초안 완료 {completed}건."),
    "evidence": ("원문: 결과에 쓴 근거 {evidence}건의 인용과 위치", "저장할 때 인용문과 위치를 원문과 대조했습니다. 인용이 주장을 뒷받침하는지는 따로 검토합니다."),
    "export": ("산출물: 세션 기록을 결과 파일(export)로 남겼습니다", "검토 통과는 원문 의미·효과의 자동 증명이 아닙니다."),
}

PAGES = [
    # id, nav, nav icon, title, title icon
    ("story", "한눈에 보기", "✨", "한눈에 보기", "✨"),
    ("overview", "요청·개요", "🏠", None, None),
    ("dashboard", "근거 대시보드", "📊", "근거 대시보드", "📊"),
    ("screening", "후기 선별", "🔎", "후기 선별과 원문 비교", "🔎"),
    ("compare", "기능 대조", "⚖️", "불편과 기존 기능 대조", "⚖️"),
    ("concepts", "제안", "💡", "제안", "💡"),
    ("history", "업무 기록", "📈", "업무 기록 재생", "📈"),
    ("evidence", "근거 원문", "🗄️", "등록 근거 원문", "🗄️"),
    ("export", "내보내기", "📦", "세션 내보내기", "📦"),
]

warnings: list[str] = []


class IntegrityError(ValueError):
    """설치 때 고정한 파일 지문과 다르다. 훅은 이 export를 실패로 묶어 두지 않고 다시 설치를 기다린다."""


def warn(msg: str) -> None:
    if msg not in warnings:
        warnings.append(msg)


def load_json(path: Path) -> dict:
    # PowerShell 5.1의 UTF-8 저장은 BOM을 붙인다.
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def kst(ts: str | None, fmt: str = "%m/%d %H:%M") -> str:
    if not ts:
        return "미기록"
    return datetime.fromisoformat(ts).astimezone(KST).strftime(fmt)


def version_label(data_version: str | None) -> str:
    m = re.search(r"-v(\d+)(?:-|$)", data_version or "")
    return f"v{m.group(1)}" if m else (data_version or "미기록")


def src_type(source_id: str) -> str:
    return TYPE_LABEL.get(source_id.split("-")[0], "기타")


def ev_type(ref: dict) -> str:
    """근거 종류. read_turns가 출처 메타데이터에서 붙인 kind(원문 지문이 맞을 때만)가 먼저다. 메타데이터는 있는데 지문이
    맞지 않은 이전 export는 kind가 None이라 '기타'다(접두어로 후기라고 짐작하지 않는다). kind 키가 없으면 origin.kind,
    source_id 접두어(하네스 관례), 원문 표현(원문 발췌·제품 사실) 순으로 나눈다. 모르는 kind는 '미지원(이름)'으로 보인다."""
    if "kind" in ref:
        kind = ref["kind"]
        return KIND_LABEL.get(kind, f"미지원({kind})") if isinstance(kind, str) and kind else "기타"
    kind = (ref.get("origin") or {}).get("kind")
    if isinstance(kind, str) and kind:
        return KIND_LABEL.get(kind, f"미지원({kind})")
    by_prefix = TYPE_LABEL.get(ref.get("source_id", "").split("-")[0])
    if by_prefix:
        return by_prefix
    return REPRESENTATION_TYPE.get((ref.get("origin") or {}).get("representation"), "기타")


def untyped(t: str) -> bool:
    """후기인지 아닌지 알 수 없는 근거 종류(원문 발췌·기타·모르는 kind)."""
    return t in ("원문 발췌", "기타") or t.startswith("미지원(")


def type_order(types) -> list[str]:
    known = [t for t in TYPE_ORDER if t in types]
    return known + sorted(t for t in types if t not in TYPE_ORDER)


def claim_prefix(claim_id: str) -> str:
    m = re.match(r"[A-Z]+", claim_id)
    return m.group(0) if m else claim_id


def duplicate_chip(link: dict) -> dict:
    value = link.get("duplicates_existing")
    if value is True:
        return {"text": "기존 기능 중복: 확정 중복", "tone": "red"}
    if value is False:
        return {"text": "기존 기능 중복: 확정 비중복", "tone": "green"}
    return {"text": "기존 기능 중복: 미확인", "tone": "orange"}


def stored_hardware_label(constraints: dict) -> str:
    value = constraints.get("hardware_allowed")
    return "허용" if value is True else "제외" if value is False else "미기록"


def compress_ids(ids: list[str]) -> str:
    groups: dict[str, list[str]] = {}
    for sid in ids:
        head, _, tail = sid.rpartition("-")
        groups.setdefault(head, []).append(tail)
    return " · ".join(f"{head}-{','.join(tails)}" for head, tails in groups.items())


def human_size(n: int) -> str:
    return f"{n / 1024:.1f}KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f}MB"


def fill(template: str, values: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), template)


def status_text(status: str | None) -> str:
    return f"{STATUS_LABEL[status]}({status})" if status in STATUS_LABEL else (status or "미기록")


def status_plain(status: str | None) -> str:
    """사이드바 칩·지표 설명처럼 짧은 자리에 쓰는 한국어 상태. 원래 값은 칩의 tip으로 남긴다."""
    return STATUS_LABEL.get(status, status or "미기록")


def semantic_chip(export: dict) -> dict:
    sem = export.get("semantic_status")
    ready = export.get("acceptance_ready")
    text = SEMANTIC_LABEL.get(sem, f"의미 검토 {sem or '미기록'}") + ("" if ready else " · 인수 전")
    return {"text": text, "tone": "orange", "tip": f"semantic_status: {sem or '미기록'} · acceptance_ready: {str(ready).lower()}"}


def family_label(family: str | None) -> str:
    if family in FAMILY:
        return FAMILY[family][0]
    return f"미지원({family})" if family else "미기록"


def https(url: str | None) -> str | None:
    return url if isinstance(url, str) and url.startswith("https://") else None


def clip(text: str, n: int = 220) -> str:
    return text if len(text) <= n else text[:n] + "…"


# ---------------------------------------------------------------- export reading

def accepted(cand: dict) -> bool:
    """저장 도구가 승인한 후보. 거절 후보도 export에 남지만(contract_valid=false, error) 현재 결과가 아니다."""
    v = cand.get("validation") or {}
    if v.get("error"):
        return False
    return (v.get("contract_valid") is True and v.get("review_required") is True
            and isinstance(v.get("assessment"), dict)
            and (v.get("review") or {}).get("can_finalize_reported_result") is True)


BINDING_KEYS = {"session_id", "turn_id", "request_key", "result_version", "result_sha256", "context_sha256",
                "code_sha256", "data_sha256", "data_version", "workflow_audit_hash"}


def digest_json(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def current_export_turn(export: dict) -> dict:
    return (export.get("turns") or [{}])[-1]


def load_web_result(export: dict, export_path: Path, web_result_path: Path | None = None,
                    web_result_sha256: str | None = None, file_metadata: dict | None = None) -> tuple[dict, str]:
    """Join immutable bytes to the latest export snapshot; never use mtime as a binding."""
    if file_metadata is not None:
        file_metadata.clear()
    turn = current_export_turn(export)
    st, expected = turn.get("state") or {}, turn.get("web_binding") or {}
    result = st.get("latest_result")
    candidate = next((c for c in reversed(turn.get("candidates") or [])
                      if c.get("result_version") == st.get("result_version") and c.get("result") == result), {})
    if (not st.get("valid") or st.get("status") not in ("completed", "held", "needs_input")
            or not result or not accepted(candidate)):
        return {}, "not_reviewed_current"
    if (set(expected) != BINDING_KEYS or expected.get("session_id") != export.get("session_id")
            or any(expected.get(k) != st.get(k) for k in ("turn_id", "request_key", "result_version"))
            or expected.get("context_sha256") != st.get("context_fingerprint")
            or expected.get("result_sha256") != digest_json(result)):
        return {}, "unbound"
    for key in ("result_sha256", "context_sha256", "code_sha256", "data_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected.get(key) or "")):
            return {}, "unbound"
    if expected["workflow_audit_hash"] is not None and not re.fullmatch(r"[0-9a-f]{64}", str(expected["workflow_audit_hash"])):
        return {}, "unbound"
    paths = [Path(web_result_path)] if web_result_path else sorted((export_path.parent.parent / "web-deliveries").glob("web-*.json"))
    mismatch = False
    for path in paths:
        try:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if len(raw) > 16 * 1024 * 1024 or path.name != f"web-{digest}.json" or (web_result_sha256 and digest != web_result_sha256):
                mismatch = True
                continue
            body = json.loads(raw)
            if (body.get("contract_version") != "product-web-result-v1" or body.get("binding") != expected
                    or body.get("result") != result or body.get("status") != st.get("status")
                    or body.get("input") != st.get("input") or body.get("validation") != candidate.get("validation")
                    or not accepted({"validation": body.get("validation")})):
                mismatch = True
                continue
            if body.get("evidence_history") != turn.get("evidence_coverage_history"):
                mismatch = True
                continue
            sources, refs = body.get("sources"), body.get("source_references")
            if not isinstance(sources, list) or not isinstance(refs, list) or len(sources) != len(refs):
                mismatch = True
                continue
            by_id = {s.get("source_id"): s for s in sources if isinstance(s, dict)}
            if len(by_id) != len(sources):
                mismatch = True
                continue
            keys = ("source_id", "model_id", "model_version", "document_version", "data_version", "sha256", "location", "origin")
            if any(not isinstance(r, dict) or not isinstance(by_id.get(r.get("source_id")), dict)
                   or any(r.get(k) != by_id[r["source_id"]].get(k) for k in keys)
                   or r.get("quote") != by_id[r["source_id"]].get("text")
                   or hashlib.sha256(str(r.get("quote", "")).encode("utf-8")).hexdigest() != r.get("sha256") for r in refs):
                mismatch = True
                continue
            if any(r not in refs for r in result.get("evidence_refs") or []):
                mismatch = True
                continue
            if file_metadata is not None:
                file_metadata.update(name=path.name, sha256=digest)
            return body, "verified_binding"
        except (OSError, ValueError, TypeError, AttributeError):
            mismatch = True
    return {}, "mismatch" if mismatch else "missing"


def rejection_of(cand: dict) -> dict | None:
    if not cand or accepted(cand):
        return None
    v = cand.get("validation") or {}
    if v.get("contract_valid") is True and not v.get("error"):
        return {"code": "stored_unreviewed", "message": "구조 저장 승인 · 현재 웹 전달을 위한 검토 기록 미확인", "findings": []}
    err = v.get("error") or {}
    return {"code": err.get("code") or "rejected", "message": err.get("message") or "",
            "findings": [str(f) for f in (v.get("review") or {}).get("findings") or []]}


def rejection_text(rej: dict) -> str:
    text = f"`{rej['code']}` {rej['message']}".strip()
    return text + (f" (검토 지적: {', '.join(rej['findings'])})" if rej["findings"] else "")


def known_sum(usage: list[dict], field: str) -> tuple[int | None, int]:
    """기록된 값만 더한다. 값이 없는(미측정) 호출 수를 함께 돌려준다. 미측정을 0으로 바꾸지 않는다."""
    known = [u.get(field) for u in usage if isinstance(u.get(field), (int, float))]
    return (sum(known) if known else None), len(usage) - len(known)


def family_request(req_input: dict, inp: dict) -> bool:
    scope = inp.get("model_scope") or []
    return inp.get("scope_mode") == "family_catalog" or (len(scope) > 1 and not req_input.get("model_id"))


def model_label(req_input: dict, inp: dict) -> str:
    scope = inp.get("model_scope") or []
    if family_request(req_input, inp):
        return f"{family_label(inp.get('product_family'))} 제품군 {len(scope)}개 모델"
    return req_input.get("model_id") or (scope[0].get("model_id") if scope else None) or "미기록"


def read_turns(export: dict) -> list[dict]:
    """export_session이 created_at 순으로 준 turn 순서를 그대로 쓴다(후보가 없는 turn도 제자리)."""
    import copy
    export = copy.deepcopy(export)
    identity_keys = ("source_id", "model_id", "model_version", "document_version", "data_version", "sha256")
    def matches(ref, item):
        if not isinstance(item, dict):
            return False
        if not all(ref.get(k) == item.get(k) for k in identity_keys):
            return False
        fingerprint = item.get("reference_fingerprint")
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            return False
        raw = json.dumps(ref, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest() == fingerprint
    def attach_kind(ref, metadata):
        items = metadata if isinstance(metadata, list) else []
        kind = next((item.get("kind") for item in items if matches(ref, item)), None)
        ref["kind"] = kind if kind in ("review", "product_fact") else None
    for turn in export.get("turns") or []:
        latest = (turn.get("state") or {}).get("latest_result")
        latest_metadata = turn.get("source_metadata")
        latest_typed = "source_metadata" in turn
        if latest_metadata is None:
            matching_candidate = next((c for c in reversed(turn.get("candidates") or []) if c.get("result") == latest), {})
            latest_metadata = matching_candidate.get("source_metadata", [])
            latest_typed = latest_typed or "source_metadata" in matching_candidate
        for candidate in turn.get("candidates") or []:
            metadata = candidate.get("source_metadata") or []
            for ref in (candidate.get("result") or {}).get("evidence_refs") or []:
                if not isinstance(ref, dict):
                    continue
                if "source_metadata" in candidate:
                    attach_kind(ref, metadata)
        state = turn.get("state") or {}
        for ref in (state.get("latest_result") or {}).get("evidence_refs") or []:
            if not isinstance(ref, dict):
                continue
            if latest_typed:
                attach_kind(ref, latest_metadata)
    requests = {r.get("turn_id"): r for r in export.get("requests") or [] if r.get("turn_id")}
    rows = []
    for t in export.get("turns") or []:
        st = t.get("state") or {}
        inp = st.get("input") or {}
        cands = t.get("candidates") or []
        good = [c for c in cands if accepted(c)]
        if "latest_result" in st:
            result = st.get("latest_result") or {}
            current = next((c for c in reversed(good) if c.get("result") == result), None) if result else None
        else:  # latest_result가 없는 이전 형식: 마지막 승인 후보
            current = good[-1] if good and st.get("status") != "cancelled" else None
            result = (current or {}).get("result") or {}
        last = cands[-1] if cands else {}
        accepted_result = good[-1].get("result") or {} if good else {}
        # 무효 turn에 보여줄 결과: 마지막 후보가 승인된 경우만(그 뒤에 거절된 후보가 있으면 승인 결과가 없던 것이다).
        last_ok = bool(last) and accepted(last) and st.get("status") != "cancelled"
        history = st.get("result_history") or []
        req_input = (requests.get(st.get("turn_id")) or {}).get("input") or {}
        usage = t.get("usage") or []
        out, out_unknown = known_sum(usage, "output_tokens")
        rows.append({
            "turn_id": st.get("turn_id"),
            "created": (history[0].get("created_at") if history else None) or (st.get("cancellation") or {}).get("recorded_at"),
            "question": req_input.get("question") or inp.get("question") or "",
            "model": model_label(req_input, inp),
            "family_request": family_request(req_input, inp),
            "family": inp.get("product_family"),
            "scope": inp.get("model_scope") or [],
            "scope_mode": inp.get("scope_mode"),
            "candidates": cands,
            "cands": len(cands),
            "status": st.get("status"),
            "valid": bool(st.get("valid")),
            "invalidation": st.get("invalidation_reason"),
            "cancellation": st.get("cancellation"),
            "revisions": st.get("revision_count") or 0,
            "data_version": inp.get("data_version"),
            "constraints": inp.get("constraints") or {},
            "result": result,
            "accepted_result": accepted_result,
            "invalid_result": (last.get("result") or {}) if last_ok else {},
            "invalid_validation": (last.get("validation") or {}) if last_ok else {},
            "validation": (current or {}).get("validation") or {},
            "last_result": last.get("result") or {},
            "last_accepted": bool(last) and accepted(last),
            "last_validation": last.get("validation") or {},
            "rejection": rejection_of(last),
            "evidence": len(accepted_result.get("evidence_refs") or []),
            "calls": len(usage),
            "out": out,
            "out_unknown": out_unknown,
            "invocations": len(t.get("invocations") or []),
            "state": st,
            "web_binding": t.get("web_binding"),
        })
    for i, r in enumerate(rows, 1):
        r["n"] = i
    return rows


def current_row(rows: list[dict]) -> dict:
    # A cancelled or stale latest turn must never resurrect a previous one.
    return rows[-1]


def turnless_requests(export: dict, rows: list[dict]) -> list[dict]:
    """turn을 만들지 못하고 멈춘 요청(needs_input·research_required·held 등).

    export에는 요청 시각이 없고 requests 순서도 시간 순서가 아니다(request_key 순). 그래서 prior_turn_id가 마지막
    turn인 요청만 '마지막 turn 뒤'라고 말할 수 있고, 나머지는 순서를 모른다고 표시한다. 어느 것이 최신인지 고르지 않는다.
    """
    last_turn = rows[-1]["turn_id"] if rows else None
    number = {r["turn_id"]: f"T{r['n']}" for r in rows}
    found = []
    for r in export.get("requests") or []:
        if r.get("turn_id"):
            continue
        inp = r.get("input") or {}
        resp = r.get("response") if isinstance(r.get("response"), dict) else {}
        reason = resp.get("reason") if isinstance(resp.get("reason"), dict) else {}
        events = r.get("events") or []
        event_reason = next((str((e.get("input") or {}).get("reason")) for e in reversed(events) if (e.get("input") or {}).get("reason")), "")
        model = inp.get("model_id") or (family_label(inp.get("product_family")) if inp.get("product_family") else "미지정")
        prior = inp.get("prior_turn_id")
        after_last = bool(last_turn) and prior == last_turn
        if not rows:
            where = "turn 없음 · 요청 순서 미확인"
        elif after_last:
            where = f"마지막 turn({number[last_turn]}) 뒤"
        else:
            where = f"prior_turn_id {number.get(prior, prior or '없음')} · 순서 미확인"
        found.append({"question": inp.get("question") or "", "model": model, "status": resp.get("status") or "pending",
                      "code": reason.get("code") or "", "reason": reason.get("message") or event_reason,
                      "events": events, "after_last": after_last, "where": where})
    return found


def turnless_chip(reqs: list[dict]) -> dict:
    after = sum(1 for r in reqs if r["after_last"])
    statuses = ", ".join(f"{STATUS_LABEL.get(s, s)} {sum(1 for r in reqs if r['status'] == s)}" for s in dict.fromkeys(r["status"] for r in reqs))
    text = (f"마지막 결과 뒤 멈춘 요청 {after}건" + (f" 외 {len(reqs) - after}건" if len(reqs) > after else "")
            if after else f"결과 없이 멈춘 요청 {len(reqs)}건 · 순서 미확인")
    return {"text": f"{text} ({statuses})", "tone": "orange",
            "tip": "업무 turn을 만들지 못하고 멈춘 요청(requests[]의 turn_id 없음). export에 요청 시각이 없어 순서는 prior_turn_id로만 판단합니다."}


def insights_shape_errors(ins) -> list[str]:
    """README의 insights 형식과 다른 부분. 형식이 다른 파일은 화면을 깨뜨리지 않도록 쓰지 않는다."""
    if not isinstance(ins, dict):
        return ["최상위"]
    errors = []

    def dict_list(value, keys=()):
        return isinstance(value, list) and all(isinstance(x, dict) and all(k in x for k in keys) for x in value)

    groups = ins.get("groups")
    if groups is not None and not (dict_list(groups, ("key", "label")) and all(isinstance(g.get("source_ids", []), list) for g in groups)):
        errors.append("groups")
    facet = ins.get("facet")
    if facet is not None and not (isinstance(facet, dict) and isinstance(facet.get("values", {}), dict) and isinstance(facet.get("order", []), list)):
        errors.append("facet")
    for key, keys in (("kpis", ()), ("funnel", ("label",)), ("excluded", ("kind", "ids", "text")), ("pages", ())):
        if ins.get(key) is not None and not dict_list(ins[key], keys):
            errors.append(key)
    for key in ("keywords", "unresolved"):
        if ins.get(key) is not None and not isinstance(ins[key], list):
            errors.append(key)
    for key in ("node_titles", "concept_titles", "feature_tags", "concept_channels"):
        if ins.get(key) is not None and not isinstance(ins[key], dict):
            errors.append(key)
    if ins.get("captions") is not None and not (isinstance(ins["captions"], dict) and all(isinstance(v, dict) for v in ins["captions"].values())):
        errors.append("captions")
    if ins.get("summaries") is not None and not (isinstance(ins["summaries"], dict) and all(isinstance(v, str) for v in ins["summaries"].values())):
        errors.append("summaries")
    steps = ins.get("concept_steps")
    if steps is not None and not (isinstance(steps, dict) and all(dict_list(v) for v in steps.values())):
        errors.append("concept_steps")
    return errors


def classify_insights(export: dict | None, insights: dict) -> str:
    """matched: 같은 turn, single_turn: turn_id는 없지만 turn이 하나뿐인 세션, unbound: turn_id 없이 turn이 여럿,
    other_turn·mismatch: 다른 turn·세션, given: export 없이 직접 준 파일."""
    if export is None:
        return "given"
    sid = insights.get("session_id")
    if sid and sid != export.get("session_id"):
        return "mismatch"
    rows = read_turns(export)
    turn = insights.get("turn_id")
    if turn:
        if not rows or turn != current_row(rows)["turn_id"]:
            return "other_turn"
    elif len(rows) > 1:
        return "unbound"
    binding = current_export_turn(export).get("web_binding")
    return "matched" if (isinstance(binding, dict) and set(binding) == BINDING_KEYS
                         and insights.get("binding") == binding) else "unverified_binding"


def pick_insights(insights_dir: Path, export: dict) -> tuple[Path | None, dict, str]:
    """같은 세션의 insights-*.json 중 turn_id가 현재 turn과 같은 것을 고른다. turn_id가 없는 파일은 turn이 하나뿐인
    세션에만 쓴다(turn이 여럿이면 어느 turn의 해석인지 알 수 없다). 형식이 다른 파일은 경고하고 건너뛴다."""
    best = None
    seen = set()
    for path in sorted(Path(insights_dir).glob("insights-*.json")):
        try:
            data = load_json(path)
        except (OSError, ValueError) as exc:
            warn(f"insights {path.name}를 읽지 못했습니다: {type(exc).__name__}")
            continue
        if not isinstance(data, dict) or data.get("session_id") != export.get("session_id"):
            continue
        shape = insights_shape_errors(data)
        if shape:
            warn(f"insights {path.name}의 형식이 README와 달라 쓰지 않았습니다: {', '.join(shape)}")
            seen.add("invalid")
            continue
        state = classify_insights(export, data)
        if state != "matched":
            seen.add(state)
            continue
        rank = 0 if state == "matched" else 1
        if best is None or rank < best[0]:
            best = (rank, path, data, state)
    if best:
        return best[1], best[2], best[3]
    for state in ("unverified_binding", "unbound", "other_turn", "invalid"):
        if state in seen:
            return None, {}, state
    return None, {}, "missing"


# ---------------------------------------------------------------- context

# ---------------------------------------------------------------- web result (product-web-result-v1)
# The harness (product v0.11+) also writes runtime-data/web-deliveries/web-<SHA-256>.json when a reviewed result is saved:
# the same current result plus every selected registered source, coverage counts, the investigation journal and access
# failures. The viewer reads it only when the file name is its own SHA-256 and it binds to the session, turn and result
# shown with the complete current export binding and stored review; anything else is left out and said so. Its text is untrusted data and is shown, never executed.
SCAN_STATUS = {"observed": "관측", "inaccessible": "접근 실패", "not_applicable": "해당 없음"}
STOP_LABEL = {"completion_time_reserve": "마감 시간 확보", "sources_exhausted": "자료 소진", "sufficient_evidence": "근거 충분",
              "access_failure": "접근 실패", "insufficient_evidence": "근거 부족", "whole_budget_expired": "전체 시간 소진"}
EVENT_LABEL = {"research_plan": "조사 계획", "source_scan": "자료 훑기", "analysis_scope": "분석 범위", "research_stop": "조사 멈춤"}
COVERAGE_PLAN = {"positive": "긍정", "negative": "불편", "long_term": "장기 사용", "conditions": "사용 조건", "counterexamples": "반례"}


class Ctx:
    def __init__(self, export: dict, export_path: Path, insights: dict, insights_state: str = "given",
                 insights_file: str | None = None, web_result: dict | None = None, delivery_state: str = "missing",
                 web_file: dict | None = None):
        self.export = export
        self.export_path = export_path
        self.web_file = web_file or {}
        self.rows = read_turns(export)
        if not self.rows:
            raise SystemExit("export에 turn이 없습니다.")
        self.cur = current_row(self.rows)
        self.turnless = turnless_requests(export, self.rows)
        # 요청 순서를 알 수 없으므로 turn 없이 멈춘 요청은 모두 앞에 드러낸다(마지막 turn 뒤인지는 아는 것만 표시).
        self.pending = self.turnless
        self.invalid = not self.cur["valid"]
        self.web = web_result or {}
        self.delivery_state = delivery_state
        if self.cur["status"] == "cancelled":
            self.result, self.validation = {}, {}
        elif self.invalid:  # 무효 표시와 함께, 무효 직전에도 승인 결과였던 것만 보여준다
            self.result, self.validation = self.cur["invalid_result"], self.cur["invalid_validation"]
        else:
            self.result, self.validation = ((self.cur["result"], self.cur["validation"]) if self.web else ({}, {}))
        if not self.web:
            insights, insights_state = {}, "unverified_delivery" if insights else insights_state
        self.has_result = bool(self.result)
        self.evidence = self.result.get("evidence_refs") or []
        self.ev = {e["source_id"]: e for e in self.evidence}
        # 합성 자료 표시는 보여주는 결과뿐 아니라 모든 후보·자료 버전에서 찾는다(거절·취소·진행 중이어도 표시).
        all_refs = [e for r in self.rows for cand in r["candidates"] for e in (cand.get("result") or {}).get("evidence_refs") or []]
        self.synthetic = (any(e.get("synthetic") or (e.get("origin") or {}).get("representation") == "synthetic" for e in all_refs)
                          or any("synthetic" in (r["data_version"] or "") for r in self.rows))
        self.claims = []
        self.claim_kind: dict[str, str] = {}  # 항목 종류는 ID 접두어가 아니라 결과의 어느 목록에 있는지로 정한다
        for key, kind in (("pains", "P"), ("existing_features", "F"), ("remaining_pains", "RP"), ("concepts", "C")):
            self.claims.extend(self.result.get(key) or [])
            for cl in self.result.get(key) or []:
                self.claim_kind.setdefault(cl.get("id"), kind)
        self.links: dict[str, list[str]] = {}
        for c in self.claims:
            for sid in c.get("source_ids") or []:
                self.links.setdefault(sid, []).append(c["id"])
        self.notes = self.result.get("decision_notes") or []
        for i, note in enumerate(self.notes, 1):
            for sid in note.get("source_ids") or []:
                self.links.setdefault(sid, []).append(f"D{i}")
        # insights가 가리키는 근거 ID가 현재 결과에 없으면 다른 turn용으로 보고 통째로 쓰지 않는다.
        referenced = [s for g in insights.get("groups") or [] for s in g.get("source_ids") or []]
        referenced += list(((insights.get("facet") or {}).get("values") or {}).keys())
        missing = sorted({s for s in referenced if s not in self.ev})
        if insights and missing:
            warn(f"insights {insights_file or ''}가 현재 결과에 없는 근거를 가리켜 쓰지 않았습니다: {', '.join(missing[:8])}"
                 + (" 외" if len(missing) > 8 else ""))
            insights, insights_state = {}, "stale"
        if insights_state == "unverified_turn":
            warn(f"insights {insights_file or ''}에 turn_id가 없어 이 turn의 해석인지 확인하지 못했습니다(turn이 여러 개인 세션). "
                 "제목·지표·단계가 다른 turn의 것일 수 있습니다.")
        self.ins = insights
        self.insights_state = insights_state
        self.insights_file = insights_file if insights else None
        self.groups = {g["key"]: g for g in insights.get("groups") or []}
        self.assumption_text = " ".join(self.result.get("assumptions") or [])
        statuses = [r["status"] for r in self.rows]
        self.values = {
            "turns": len(self.rows),
            "held": statuses.count("held"),
            "completed": statuses.count("completed"),
            "evidence": len(self.evidence),
            "reviews": sum(1 for e in self.evidence if ev_type(e) == "후기"),
            "model": self.cur["model"],
            "family": family_label(self.cur["family"]),
            "version": version_label(self.cur["data_version"]),
        }
        for key, g in self.groups.items():
            self.values[f"g_{key}"] = len(g.get("source_ids") or [])

    def kind_of(self, claim_id: str) -> str:
        return self.claim_kind.get(claim_id) or claim_prefix(claim_id)

    def claim_tone(self, claim_id: str) -> str:
        return CLAIM_TONE.get(self.kind_of(claim_id), "gray")

    def type_of(self, sid: str) -> str:
        return ev_type(self.ev[sid]) if sid in self.ev else src_type(sid)

    def chips_for(self, ids: list[str]) -> list[dict]:
        by_type: dict[str, list[str]] = {}
        for sid in ids:
            by_type.setdefault(self.type_of(sid), []).append(sid)
        return [{"text": f"{t} {len(v)}", "tone": TYPE_TONE.get(t, "gray"), "tip": ", ".join(v)} for t, v in by_type.items()]

    def resolve(self, item: dict) -> int | str | None:
        """kpi·funnel 항목의 값을 근거 목록에서 센다. 고정 숫자가 결과 원문에 없으면 그리지 않고 경고한다."""
        if "group" in item:
            g = self.groups.get(item["group"])
            if not g:
                warn(f"묶음 '{item['group']}'이 insights에 없습니다.")
                return None
            return len(g.get("source_ids") or [])
        if item.get("evidence") == "all":
            return len(self.evidence)
        if "evidence_prefix" in item:
            return sum(1 for e in self.evidence if e["source_id"].startswith(item["evidence_prefix"] + "-"))
        value = item.get("value")
        if item.get("verify_in") == "assumptions" and isinstance(value, (int, float)):
            plain, comma = str(value), f"{value:,}"
            if plain not in self.assumption_text and comma not in self.assumption_text:
                warn(f"'{item.get('label')}' 값 {value}가 결과 assumptions 원문에 없어 그리지 않았습니다.")
                return None
        return value


# ---------------------------------------------------------------- shared blocks

def turn_reason(c: Ctx) -> str:
    """현재 turn이 완료가 아닌 이유: 취소 기록 → 마지막 후보 거절 → 결과(또는 마지막 후보)의 validation_findings 순."""
    cur = c.cur
    if cur["cancellation"]:
        cx = cur["cancellation"]
        return (f"취소 사유: {cx.get('reason') or '미기록'} (취소 전 상태 {status_text(cx.get('prior_status'))}"
                + (", 실행 중단은 확인 안 됨" if cx.get("native_execution_controlled") is False else "") + ")")
    if cur["rejection"]:
        return f"저장 도구가 마지막 후보를 거절했습니다: {rejection_text(cur['rejection'])}"
    findings = c.result.get("validation_findings") or cur["last_result"].get("validation_findings") or []
    if findings:
        return f"결과에 적힌 사유: {clip(str(findings[0]))}"
    if not cur["cands"]:
        return "아직 저장된 후보가 없습니다."
    return "결과에 사유가 기록되지 않았습니다."


def no_result_blocks(c: Ctx, what: str) -> list[dict]:
    """승인된 현재 결과가 없을 때(거절·취소·보류 전 등) 그 화면 대신 보여준다."""
    rejected = any(not accepted(cand) for cand in c.cur["candidates"])
    return [{"type": "callout", "tone": "warning",
             "text": f"현재 승인된 결과가 없어 이 화면({what})은 비워 두었습니다. 상태: **{status_text(c.cur['status'])}**"
                     + (" · 무효" if c.invalid else "") + f". {turn_reason(c)}"
                     + (" 거절된 후보는 '업무 기록' 화면의 후보 표에 사유와 함께 있습니다." if rejected else "")}]


def stale_blocks(c: Ctx) -> list[dict]:
    if not c.invalid or not c.has_result:
        return []
    return [{"type": "callout", "tone": "warning",
             "text": f"**무효 처리된 결과입니다.** T{c.cur['n']}의 결과는 `{c.cur['invalidation'] or '사유 미기록'}`로 무효가 됐습니다. "
                     "현재 결과로 쓰지 말고 다시 질문해 새 결과를 받으세요."}]


def status_blocks(c: Ctx) -> list[dict]:
    """요청·개요 맨 위의 상태 안내: turn 없는 최근 요청, 무효, 거절·취소·보류 사유, 합성 자료."""
    blocks: list[dict] = []
    cur = c.cur
    if c.pending:
        after = [r for r in c.pending if r["after_last"]]
        unknown = len(c.pending) - len(after)
        parts = []
        if after:
            parts.append(f"**마지막 turn(T{c.rows[-1]['n']}) 뒤에 turn 없이 멈춘 요청 {len(after)}건이 있습니다.** 아래 turn 결과는 그 요청의 답이 아닙니다.")
        if unknown:
            parts.append(f"**turn 없이 멈춘 요청 {unknown}건이 있습니다.** export에는 요청 시각이 없어 이 요청이 마지막 turn보다 "
                         "나중인지 알 수 없습니다. 아래 turn 결과가 최신 요청의 답이 아닐 수 있습니다.")
        blocks.append({"type": "callout", "tone": "warning", "text": " ".join(parts)})
        blocks.append({"type": "table", "count": False, "columns": [
            {"key": "q", "label": "질문", "kind": "wide"}, {"key": "model", "label": "모델", "kind": "mono"},
            {"key": "status", "label": "상태", "kind": "pill"}, {"key": "why", "label": "멈춘 이유", "kind": "wide"},
            {"key": "where", "label": "위치"}],
            "rows": [{"q": r["question"], "model": r["model"], "status": {"text": status_text(r["status"]), "tone": STATUS_TONE.get(r["status"], "gray")},
                      "why": (f"`{r['code']}` " if r["code"] else "") + (r["reason"] or "사유 미기록"), "where": r["where"]} for r in c.pending],
            "source": "requests[] 중 turn_id가 없는 요청 · export 순서는 시간 순서가 아닙니다(마지막 turn 뒤 여부는 prior_turn_id로만 판단)"})
    if c.invalid:
        blocks.append({"type": "callout", "tone": "warning",
                       "text": f"**현재 유효한 결과가 없습니다.** 마지막 turn T{cur['n']}은 무효입니다(사유 `{cur['invalidation'] or '미기록'}`). "
                               + ("화면은 무효 처리 전 마지막 승인 결과를 보여주며 현재 결과로 쓰면 안 됩니다." if c.has_result
                                  else "무효 처리 전에도 승인된 결과가 없어 보여줄 결과가 없습니다.")})
    if cur["status"] != "completed" or not c.has_result:
        blocks.append({"type": "callout", "tone": "warning",
                       "text": f"{'마지막 turn' if c.pending else '현재 결과'}는 **{status_text(cur['status'])}** 상태입니다. {turn_reason(c)}"
                               + (" (검토 메모 전체는 '후기 선별' 화면에 있습니다)" if c.result.get("validation_findings") else "")})
    if c.synthetic:
        blocks.append({"type": "callout", "tone": "info", "text": "이 세션의 근거 자료는 **합성 시험 자료(synthetic)**입니다. 실제 고객·제품 근거가 아닙니다."})
    return blocks


def decision_note_blocks(c: Ctx) -> list[dict]:
    """결과의 decision_notes(판단 메모). basis는 모델이 붙인 구분이며 공식 인용·의미 검증이 아니다."""
    if not c.notes:
        return []
    rows = []
    for i, note in enumerate(c.notes, 1):
        label, tone = BASIS.get(note.get("basis"), (f"미지원({note.get('basis')})", "gray"))
        rows.append({"id": f"D{i}", "basis": {"text": label, "tone": tone}, "text": note.get("text", ""),
                     "src": [{"text": s, "tone": TYPE_TONE.get(c.type_of(s), "gray")} for s in note.get("source_ids") or []]
                     or [{"text": "근거 없음", "tone": "orange"}]})
    return [
        {"type": "heading", "icon": "🧭", "text": f"판단 메모 {len(rows)}개"},
        {"type": "table", "count": False,
         "columns": [{"key": "id", "label": "메모", "kind": "mono"}, {"key": "basis", "label": "구분(모델 보고)", "kind": "pill"},
                     {"key": "text", "label": "내용", "kind": "wide"}, {"key": "src", "label": "근거", "kind": "chips"}],
         "rows": rows,
         "source": "현재 결과의 decision_notes · 구분은 모델이 붙인 라벨이며 공식 인용이나 의미 검증이 아닙니다"},
    ]


def insights_notice(c: Ctx) -> list[dict]:
    """의견 묶음을 그리지 못한 이유(insights 없음·다른 세션·다른 turn·근거 불일치)와 만드는 방법을 알린다.
    insights를 썼다면 어느 파일을 어떤 근거로 붙였는지 보여준다."""
    if c.insights_file and c.insights_state in INSIGHTS_APPLIED:
        return [{"type": "chips", "items": [{"text": f"insights {c.insights_file} · {INSIGHTS_APPLIED[c.insights_state]} · 모델 해석",
                                             "tone": "orange" if c.insights_state == "unverified_turn" else "purple"}]}]
    if c.insights_state not in INSIGHTS_WHY:
        return []
    return [{"type": "callout", "tone": "info", "text": (
        f"**의견 묶음 차트는 없습니다.** 후기를 비슷한 의견끼리 묶는 일은 AI 해석이라 저장된 결과에 들어 있지 않습니다. "
        f"{INSIGHTS_WHY_PLAIN[c.insights_state]} 아래 숫자와 차트는 저장된 결과의 항목을 그대로 센 것입니다.")}]


def insights_howto(c: Ctx) -> list[dict]:
    """의견 묶음을 그리는 방법(파일 위치·session_id·turn_id). 기획자 화면을 가리지 않도록 대시보드 맨 아래에 접어 둔다."""
    if c.insights_file or c.insights_state not in INSIGHTS_WHY:
        return []
    sid = str(c.export.get("session_id") or "")
    return [{"type": "expander", "icon": "🛠️", "title": "의견 묶음 차트를 그리려면 (운영 안내)", "blocks": [
        {"type": "text", "text": f"{INSIGHTS_WHY[c.insights_state]} 의견 묶음 도넛·구분별 막대·후기 원문 비교는 export에 없는 모델 해석이라 "
                                 "insights 파일이 있어야 그립니다."},
        {"type": "steps", "items": [
            f"`{INSIGHTS_HINT}` 파일에 groups(묶음 이름과 근거 ID 목록)를 씁니다(README의 insights 형식).",
            "같은 파일에 아래 session_id와 turn_id를 그대로 적습니다. 다른 질문용 파일은 쓰지 않습니다.",
            "다음 export 때나 `viewer.py open --latest`로 다시 만들 때 반영됩니다.",
        ]},
        {"type": "files", "items": [{"label": "session_id", "value": sid}, {"label": "turn_id", "value": c.cur["turn_id"]}]},
    ]}]


# ---------------------------------------------------------------- pages

def model_display(c: Ctx) -> dict:
    """큰 글씨 칸에 쓸 짧은 모델 값. 제품군 질문이면 결과 근거 모델이 하나일 때 그 모델, 아니면 모델 수를 쓴다."""
    cur = c.cur
    family = family_label(cur["family"])
    if not cur["family_request"]:
        return {"value": cur["model"], "note": family}
    cited = {e.get("model_id") for e in c.evidence}
    scope_ids = [s.get("model_id") for s in cur["scope"]]
    cited_scope = [m for m in scope_ids if m in cited]
    if len(cited_scope) == 1:
        return {"value": cited_scope[0], "note": f"{family} 제품군 질문 · 결과 근거 모델"}
    return {"value": f"{len(scope_ids)}개", "note": f"{family} 제품군 질문 · 대상 모델 수"}


def site_of(url: str | None) -> str:
    host = (urlparse(url).hostname or "") if url else ""
    return host[4:] if host.startswith("www.") else host


def quote_items(c: Ctx, ids: list[str], limit: int = 2) -> list[dict]:
    """항목에 연결된 근거 원문(앞의 몇 건). 인용은 저장된 그대로이며 길면 자른다."""
    out = []
    for sid in ids[:limit]:
        e = c.ev.get(sid)
        if not e:
            continue
        url = https((e.get("origin") or {}).get("source_url"))
        t = ev_type(e)
        out.append({"quote": clip(e.get("quote", ""), 200), "source_id": sid, "site": site_of(url), "href": url,
                    "type": t, "type_tone": TYPE_TONE.get(t, "gray")})
    return out


def summary_of(c: Ctx, item_id) -> str | None:
    """insights summaries: the model's short summary of one item (P1, F1, RP1, C1 …), shown beside the saved text."""
    s = (c.ins.get("summaries") or {}).get(item_id)
    return clip(s.strip(), 300) if isinstance(s, str) and s.strip() else None


def claim_items(c: Ctx, claims: list[dict]) -> list[dict]:
    items = []
    for cl in claims:
        ids = cl.get("source_ids") or []
        chips = [{"text": f"근거 {len(ids)}건" + (f" · 앞의 2건만 표시" if len(ids) > 2 else ""), "tone": "gray", "tip": ", ".join(ids)}]
        items.append({"id": cl.get("id"), "text": cl.get("text", ""), "summary": summary_of(c, cl.get("id")),
                      "quotes": quote_items(c, ids), "chips": chips})
    return items


def page_story(c: Ctx) -> list[dict]:
    """한눈에 보기: 질문 → 현재 불편 → 기존 기능 대조 → 연결 → 제안 → 한계. 결과와 검토 기록에 적힌 것만 배치한다."""
    cur, res = c.cur, c.result
    md = model_display(c)
    eyebrow = " · ".join(x for x in (
        family_label(cur["family"]) + (" 제품군 질문" if cur["family_request"] else ""), f"모델 {md['value']}",
        f"자료 {version_label(cur['data_version'])}", "저장된 실행 결과") if x)
    chips = [{"text": status_plain(cur["status"]), "tone": STATUS_TONE.get(cur["status"], "gray"), "tip": f"status: {cur['status']}"},
             {"text": "유효" if cur["valid"] else "무효", "tone": "green" if cur["valid"] else "red"}, semantic_chip(c.export)]
    if c.synthetic:
        chips.append({"text": "합성 시험 자료", "tone": "purple"})
    pains, features = res.get("pains") or [], res.get("existing_features") or []
    remaining, concepts = res.get("remaining_pains") or [], res.get("concepts") or []
    hero = {"type": "hero", "eyebrow": eyebrow, "title": cur["question"] or "질문 원문 미기록",
            "subtitle": "하네스가 근거 자료에서 불편을 찾아 같은 모델의 기존 기능과 대조하고, 남은 불편에 연결한 제안을 저장했습니다."
                        + (" **합성 시험 자료**입니다." if c.synthetic else ""),
            "chips": chips,
            "stats": [{"label": "근거", "value": len(c.evidence), "unit": "건", "tone": "blue"},
                      {"label": "현재 불편", "value": len(pains), "unit": "개", "tone": "red"},
                      {"label": "남은 불편", "value": len(remaining), "unit": "개", "tone": "orange"},
                      {"label": "제안", "value": len(concepts), "unit": "개", "tone": "purple"}] if c.has_result else []}
    blocks = [hero, *status_blocks(c), *stale_blocks(c)]
    if not c.has_result:
        return blocks + no_result_blocks(c, "한눈에 보기")
    assessment = c.validation.get("assessment") or {}
    matches = assessment.get("feature_matches") or []
    links = assessment.get("concept_links") or []
    checks = assessment.get("claim_checks") or []

    blocks.append({"type": "story", "key": "problem", "label": "Problem · 현재 불편", "tone": "red", "title": f"근거에서 찾은 현재 불편 {len(pains)}가지",
                   "text": "후기·자료 원문에 연결된 현재 제품의 불편입니다. 관측한 것이며 발생률이나 시장 수요가 아닙니다.",
                   "blocks": [{"type": "claims", "kind_label": "현재 불편", "tone": "red", "items": claim_items(c, pains)}] if pains
                   else [{"type": "callout", "tone": "warning", "text": "결과에 현재 불편이 없습니다."}]})

    match_items = [{"from": {"text": fm.get("pain_id"), "tone": "red"}, "to": {"text": fm.get("remaining_pain_id"), "tone": "orange"},
                    "label": RESOLUTION_LABEL.get(fm.get("resolution"), fm.get("resolution") or "미기록"),
                    "tone": RESOLUTION_TONE.get(fm.get("resolution"), "gray"), "text": clip(fm.get("rationale", ""), 320)} for fm in matches]
    check_blocks = [{"type": "claims", "kind_label": "기존 기능", "tone": "blue", "items": claim_items(c, features)}] if features else []
    check_blocks.append({"type": "matches", "items": match_items, "source": "검토 기록 feature_matches · 모델이 쓴 판단이며 저장 도구는 형식만 검사"}
                        if match_items else {"type": "callout", "tone": "info", "text": "검토 기록에 기존 기능 대조 판단이 없습니다."})
    blocks.append({"type": "story", "key": "check", "label": "Check · 기존 기능 대조", "tone": "blue",
                   "title": f"같은 모델의 기존 기능 {len(features)}개와 맞춰 봤습니다",
                   "text": "기능이 있다고 불편이 해소된 것은 아닙니다. 대조 판단(해소·일부 해소·미해소·불확실)은 검토 기록에 적힌 그대로입니다.",
                   "blocks": check_blocks})

    ids = {"pain": [x.get("id") for x in pains], "remaining": [x.get("id") for x in remaining], "concept": [x.get("id") for x in concepts]}
    nodes = [{"id": x.get("id"), "column": col, "tone": tone_, "text": x.get("text", ""), "summary": summary_of(c, x.get("id"))}
             for col, items, tone_ in (("pain", pains, "red"), ("remaining", remaining, "orange"), ("concept", concepts, "purple")) for x in items]
    flow_links = [{"from": fm.get("pain_id"), "to": fm.get("remaining_pain_id"),
                   "label": RESOLUTION_LABEL.get(fm.get("resolution"), fm.get("resolution") or ""), "tone": RESOLUTION_TONE.get(fm.get("resolution"), "gray")}
                  for fm in matches if fm.get("pain_id") in ids["pain"] and fm.get("remaining_pain_id") in ids["remaining"]]
    flow_links += [{"from": rp, "to": link.get("concept_id"), "label": "", "tone": "purple"}
                   for link in links for rp in link.get("remaining_pain_ids") or []
                   if rp in ids["remaining"] and link.get("concept_id") in ids["concept"]]
    blocks.append({"type": "story", "key": "flow", "label": "Flow · 연결", "tone": "orange", "title": "불편에서 제안까지 이어진 연결",
                   "blocks": [{"type": "flow", "columns": [{"key": "pain", "title": "현재 불편", "tone": "red"},
                                                           {"key": "remaining", "title": "남은 불편", "tone": "orange"},
                                                           {"key": "concept", "title": "제안", "tone": "purple"}],
                               "nodes": nodes, "links": flow_links,
                               "note": "선과 화살표는 검토 기록(feature_matches·concept_links)에 적힌 연결만 그렸습니다. 연결이 적히지 않은 항목은 선 없이 둡니다."}]})

    cons = cur["constraints"]
    by_concept = {l.get("concept_id"): l for l in links}
    titles = c.ins.get("concept_titles") or {}
    sol = []
    for i, cl in enumerate(concepts, 1):
        link = by_concept.get(cl.get("id")) or {}
        chips_ = [{"text": "새 부품 없음" if not cl.get("requires_hardware") else "하드웨어 필요", "tone": "green" if not cl.get("requires_hardware") else "red"}]
        if link:
            chips_.append(duplicate_chip(link))
            if link.get("geometry_required"):
                chips_.append({"text": "내부 치수 필요", "tone": "orange"})
        plan = cl.get("validation_plan")
        sol.append({"id": cl.get("id"), "n": i, "title": titles.get(cl.get("id")), "text": cl.get("text", ""),
                    "summary": summary_of(c, cl.get("id")), "chips": chips_,
                    "requirements": cl.get("requirements") or [], "steps": cl.get("implementation_steps") or [],
                    "plan": {"status": PLAN_STATUS.get(plan.get("status"), plan.get("status") or "상태 미기록"),
                             "rows": [{"k": label, "v": plan.get(key) or "미작성"} for key, label in PLAN_FIELDS]} if plan else None,
                    "links": [{"text": rp, "tone": "orange"} for rp in link.get("remaining_pain_ids") or []],
                    "sources": [{"text": s, "mono": True} for s in cl.get("source_ids") or []]})
    blocks.append({"type": "story", "key": "solution", "label": "Solution · 제안", "tone": "purple", "title": f"남은 불편에 연결한 제안 {len(concepts)}가지",
                   "text": f"저장된 실행 제약: 하드웨어 추가 {stored_hardware_label(cons)} · 제안 최대 {cons.get('max_concepts', '미기록')}개. "
                           "저장 입력의 기본값·후속 설정을 포함하며 요청 원문에 명시된 조건으로 추정하지 않습니다. "
                           "효과·비용은 측정 전 미확정입니다.",
                   "blocks": [{"type": "solutions", "items": sol}] if sol else [{"type": "callout", "tone": "warning", "text": "결과에 제안이 없습니다."}]})

    supported = sum(1 for ch in checks if ch.get("support_status") == "supported")
    unclear = sum(1 for ch in checks if ch.get("scope_relation") not in (None, "current_model"))
    sites = {site_of(https((e.get("origin") or {}).get("source_url"))) or "링크 없음" for e in c.evidence}
    untyped_n = sum(1 for e in c.evidence if untyped(ev_type(e)))
    usage = c.export.get("usage_summary") or {}
    tiles = []
    if checks:
        tiles.append({"label": "근거가 뒷받침한 항목", "value": f"{supported} / {len(checks)}", "tone": "green" if supported == len(checks) else "orange",
                      "note": f"나머지 {len(checks) - supported}개는 불확실 등" if supported < len(checks) else "검토 기록 기준"})
    if unclear:
        tiles.append({"label": "모델이 불명확한 근거", "value": unclear, "unit": "건", "tone": "orange", "note": "다른 모델·페이지일 수 있음"})
    tiles.append({"label": "출처 사이트", "value": len(sites), "unit": "곳", "tone": "blue", "note": ", ".join(sorted(sites))[:60]})
    if untyped_n:
        tiles.append({"label": "후기 여부 미기록", "value": untyped_n, "unit": "건", "tone": "gray", "note": "원문 발췌를 후기로 세지 않음"})
    tiles.append({"label": "의미 검토", "value": "검토 전" if c.export.get("semantic_status") == "unverified" else (c.export.get("semantic_status") or "미기록"),
                  "tone": "orange", "note": "사람이 원문으로 확인해야 함"})
    tiles.append({"label": "사용량", "value": usage["recorded_calls"] if usage.get("recorded_calls") else "미측정",
                  "unit": "건" if usage.get("recorded_calls") else "", "tone": "gray", "note": "기록 없음은 0이 아님" if not usage.get("recorded_calls") else "기록된 호출"})
    trust = [{"type": "tiles", "items": tiles}]
    if c.notes:
        basis = Counter(BASIS.get(n.get("basis"), (f"미지원({n.get('basis')})", "gray"))[0] for n in c.notes)
        trust.append({"type": "chips", "title": f"판단 메모 {len(c.notes)}개 (원문은 '요청·개요' 화면)",
                      "items": [{"text": f"{k} {v}", "tone": dict(BASIS.values()).get(k, "gray")} for k, v in basis.items()]})
    trust.append({"type": "callout", "tone": "warning", "text": "검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정이며, 검토 기록은 모델이 쓰고 저장 도구는 형식만 검사했습니다."})
    blocks.append({"type": "story", "key": "trust", "label": "Trust · 한계", "tone": "gray", "title": "믿을 수 있는 정도와 한계", "blocks": trust})
    return blocks


def page_overview(c: Ctx) -> list[dict]:
    first, cur = c.rows[0], c.cur
    cons = cur["constraints"]
    statuses = ", ".join(f"{STATUS_LABEL.get(s, s)} {sum(1 for r in c.rows if r['status'] == s)}" for s in dict.fromkeys(r["status"] for r in c.rows))
    follow_rows = [{
        "t": f"T{r['n']}", "time": kst(r["created"]), "model": r["model"], "q": r["question"],
        "status": {"text": status_text(r["status"]), "tone": STATUS_TONE.get(r["status"], "gray")},
    } for r in c.rows[1:]]
    cited = {e.get("model_id") for e in c.evidence}
    excluded = cons.get("exclude_pains") or []
    model_metric = {"label": "모델", **model_display(c)}
    scope_note = (f"{SCOPE_MODE[cur['scope_mode']]} · " if cur["scope_mode"] in SCOPE_MODE else "") + f"대상 모델 {len(cur['scope'])}개"
    blocks = [
        {"type": "lead", "text": c.ins.get("lead") or "하네스가 저장한 결과 파일(export)을 읽어 근거·불편·기존 기능·제안 연결을 그린 화면입니다. 화면은 **저장된 실행 결과**만 보여주고 모델이나 업무를 다시 실행하지 않습니다."},
        *status_blocks(c),
        {"type": "divider"},
        {"type": "heading", "icon": "🗂️", "text": "요청과 저장된 실행 제약"},
        {"type": "metrics", "items": [
            model_metric,
            {"label": "범위", "value": SCOPE_SHORT.get(cur["scope_mode"], cur["scope_mode"] or "미기록"), "note": scope_note},
            {"label": "제안 상한", "value": cons.get("max_concepts", "미기록"), "unit": "개" if "max_concepts" in cons else "",
             "note": "저장된 실행 제약 · 기본값·후속 설정 포함"},
            {"label": "하드웨어 추가", "value": stored_hardware_label(cons), "note": "저장된 실행 제약 · 기본값·후속 설정 포함"},
            {"label": "자료 버전", "value": version_label(cur["data_version"]), "note": cur["data_version"] or ""},
            {"label": "질문(turn)", "value": len(c.rows), "unit": "개", "note": statuses},
        ]},
        {"type": "chips", "title": "대상 모델", "items": [
            {"text": s.get("model_id", "?") + (" · 결과 근거" if s.get("model_id") in cited else ""), "mono": True,
             "tone": "blue" if s.get("model_id") in cited else "gray",
             "tip": f"model_version {s.get('model_version')} · document_version {s.get('document_version')}"} for s in cur["scope"]]
         or [{"text": "기록 없음", "tone": "gray"}]},
        {"type": "chips", "title": "제외한 불편 (저장된 실행 제약)",
         "items": [{"text": p, "tone": "orange"} for p in excluded] or [{"text": "없음", "tone": "gray"}]},
        {"type": "quotes", "items": [{
            "quote": first["question"],
            "chips": [{"text": "T1 요청 원문", "tone": "blue"}, {"text": status_text(first["status"]), "tone": STATUS_TONE.get(first["status"], "gray")}],
            "meta": f"{kst(first['created'])} KST · {first['model']}",
        }]},
    ]
    blocks += decision_note_blocks(c)
    if follow_rows:
        blocks.append({"type": "expander", "icon": "💬", "title": f"후속 질문 {len(follow_rows)}개", "blocks": [{
            "type": "table",
            "columns": [{"key": "t", "label": "turn", "kind": "mono"}, {"key": "time", "label": "시각(KST)", "kind": "mono"},
                        {"key": "model", "label": "모델", "kind": "mono"}, {"key": "q", "label": "질문", "kind": "wide"},
                        {"key": "status", "label": "상태", "kind": "pill"}],
            "rows": follow_rows,
        }]})
    blocks += [
        {"type": "heading", "icon": "🚀", "text": "하네스 단계"},
        {"type": "text", "text": "출품 업무 Skill 6개의 구조 정의입니다. 이번 세션에서 각 Skill이 실행됐다는 기록은 아니며, Agent 수를 뜻하지도 않습니다."},
        {"type": "features", "items": HARNESS_STEPS},
        {"type": "expander", "icon": "📋", "title": "이 화면 쓰는 법 (설치·운영 안내)", "blocks": [
            {"type": "steps", "items": [
                "CLI(Claude Code·Codex)에서 질문하면 하네스가 결과를 `runtime-data/exports`에 결과 파일(export)로 저장합니다.",
                "뷰어를 설치했다면 새 결과가 저장될 때 이 화면을 다시 만들고, CLI 세션마다 처음 한 번 브라우저를 엽니다.",
                f"의견 묶음·자막·제외 사유는 결과 파일에 없는 AI 해석입니다. 같은 session_id·turn_id로 `{INSIGHTS_HINT}`를 쓰면 함께 그립니다.",
                "브라우저를 열어 둔 채면 2초 안에 새 데이터로 바뀝니다. 화면을 닫았다면 아래 명령으로 직접 엽니다.",
                "공유할 때는 `build_view.py --standalone`으로 데이터가 들어 있는 HTML 한 파일을 만듭니다.",
            ]},
            {"type": "code", "text": "# 하네스 폴더에서 실행 (표준 라이브러리만 사용, 모델·업무 호출 없음)\n"
                                     "uv run python web/prototypes/visual-viewer/viewer.py open --latest"},
        ]},
        {"type": "expander", "icon": "🆔", "title": "세션 정보", "blocks": [{"type": "files", "items": [
            {"label": "session_id", "value": c.export.get("session_id", "미기록")},
            {"label": "현재 turn", "value": cur["turn_id"]},
            {"label": "자료 버전", "value": cur["data_version"] or "미기록"},
            {"label": "규칙 버전", "value": (cur["state"].get("input", {}).get("workflow") or {}).get("rules_version", "미기록")},
        ]}]},
    ]
    return blocks


TYPE_SOURCE = "근거 종류(kind)가 있으면 그 값, 없으면 ID 규칙(REVIEW·SPEC 등), 그것도 없으면 원문을 옮긴 방식(원문 발췌·제품 사실)"


def review_kpi(c: Ctx, untyped_types: list[str]) -> dict:
    """후기 근거 수. 종류를 모르는 근거만 있으면 '미확인'을 크게 쓰지 않고, 아는 것(원문 발췌 N건)과 모르는 것(후기 여부)을 나눠 적는다."""
    reviews = c.values["reviews"]
    if reviews or not untyped_types:
        return {"label": "후기 근거", "value": reviews, "unit": "건", "tone": "purple",
                "note": f"후기로 분류된 근거 · 종류 미기록 {len(untyped_types)}건 별도" if untyped_types else "후기로 분류된 근거",
                "source": TYPE_SOURCE}
    label = "원문 발췌" if set(untyped_types) == {"원문 발췌"} else "종류 미기록 근거"
    return {"label": label, "value": len(untyped_types), "unit": "건", "tone": "gray", "note": "후기인지 기록 없음",
            "source": "결과에 근거 종류(kind)가 없어 후기 수를 세지 않았습니다"}


def type_note(c: Ctx) -> list[dict]:
    """종류를 모르는 근거가 있으면 왜 후기 수를 세지 않았는지 쉬운 말로 적는다."""
    n = sum(1 for e in c.evidence if untyped(ev_type(e)))
    if not n:
        return []
    return [{"type": "callout", "tone": "info", "text": (
        f"근거 {n}건은 후기인지 공식 자료인지가 결과에 저장되지 않았습니다. 그래서 원문을 그대로 옮긴 **원문 발췌**와 사실을 요약한 "
        "**제품 사실**로만 나눴고, 원문 발췌를 고객 후기로 세지 않았습니다.")}]


def count_items(values: list, labels: dict, tones: dict, notes: dict | None = None) -> list[dict]:
    """값별 건수 막대. 처음 나온 순서가 아니라 라벨 표의 순서, 모르는 값은 원래 값 그대로 뒤에 둔다."""
    counts = Counter(values)
    order = [k for k in labels if k in counts] + [k for k in counts if k not in labels]
    return [{"label": labels.get(k, str(k) if k else "미기록"), "value": counts[k], "tone": tones.get(k, "gray"),
             "note": (notes or {}).get(k, "")} for k in order]


def judgment_blocks(c: Ctx) -> list[dict]:
    """검토 기록(assessment)에 적힌 판단을 센다. 모델이 쓰고 저장 도구가 형식을 검사한 기록이며 의미 검증이 아니다."""
    assessment = c.validation.get("assessment") or {}
    matches = assessment.get("feature_matches") or []
    checks = assessment.get("claim_checks") or []
    links = assessment.get("concept_links") or []
    if not (matches or checks or links):
        return []
    cols = []
    if matches:
        notes: dict[str, list[str]] = {}
        for fm in matches:
            notes.setdefault(fm.get("resolution"), []).append(f"{fm.get('pain_id')}→{fm.get('remaining_pain_id')}")
        cols.append({"span": 1, "blocks": [{
            "type": "hbars", "title": "기존 기능과 대조한 결과", "unit": "건",
            "items": count_items([fm.get("resolution") for fm in matches], RESOLUTION_LABEL, RESOLUTION_TONE,
                                 {k: ", ".join(v) for k, v in notes.items()}),
            "source": "검토 기록 feature_matches · 불편→남은 불편 쌍마다 모델이 쓴 판단"}]})
    if checks:
        notes = {}
        for ch in checks:
            notes.setdefault(ch.get("support_status"), []).append(str(ch.get("claim_id")))
        cols.append({"span": 1, "blocks": [{
            "type": "hbars", "title": "항목별 근거 확인", "unit": "건",
            "items": count_items([ch.get("support_status") for ch in checks], SUPPORT_LABEL, SUPPORT_TONE,
                                 {k: ", ".join(v) for k, v in notes.items()}),
            "source": "검토 기록 claim_checks · 항목마다 근거가 뒷받침하는지 모델이 쓴 판단"}]})
    blocks: list[dict] = [{"type": "section", "text": "대조·검토 판단"}]
    if cols:
        blocks.append({"type": "row", "cols": cols})
    remaining = [r.get("id") for r in c.result.get("remaining_pains") or []]
    if links:
        linked = {rp for link in links for rp in link.get("remaining_pain_ids") or []}
        duplicates = sum(1 for link in links if link.get("duplicates_existing") is True)
        nonduplicates = sum(1 for link in links if link.get("duplicates_existing") is False)
        unknown = len(links) - duplicates - nonduplicates
        chips = [{"text": f"남은 불편 {len(remaining)}개 중 제안과 연결 {sum(1 for r in remaining if r in linked)}개", "tone": "blue"},
                 {"text": f"확정 중복 제안 {duplicates}개", "tone": "red" if duplicates else "gray"},
                 {"text": f"확정 비중복 제안 {nonduplicates}개", "tone": "green" if nonduplicates else "gray"},
                 {"text": f"중복 여부 미확인 제안 {unknown}개", "tone": "orange" if unknown else "gray"},
                 {"text": f"내부 치수가 필요한 제안 {sum(1 for link in links if link.get('geometry_required'))}개", "tone": "gray"}]
        blocks.append({"type": "chips", "items": chips, "source": "검토 기록 concept_links"})
    if checks and any(ch.get("scope_relation") not in (None, "current_model") for ch in checks):
        scope = Counter(SCOPE_RELATION_LABEL.get(ch.get("scope_relation"), ch.get("scope_relation") or "미기록") for ch in checks)
        blocks.append({"type": "chips", "title": "근거가 가리키는 모델", "items": [
            {"text": f"{k} {v}건", "tone": "green" if k == "현재 모델" else "orange"} for k, v in scope.items()]})
    blocks.append({"type": "callout", "tone": "info",
                   "text": "위 판단은 모델이 검토 기록에 쓴 것이고 저장 도구는 형식만 검사했습니다. 의미가 맞는지는 사람이 원문으로 확인해야 합니다."})
    return blocks


def source_site_block(c: Ctx) -> dict:
    """근거 원문 주소(HTTPS)의 사이트 이름별 건수. 사이트 이름만 세며 후기 여부를 뜻하지 않는다."""
    sites: dict[str, list[str]] = {}
    for e in c.evidence:
        url = https((e.get("origin") or {}).get("source_url"))
        host = (urlparse(url).hostname or "") if url else ""
        host = host[4:] if host.startswith("www.") else host
        sites.setdefault(host or "링크 없음", []).append(e["source_id"])
    items = [{"label": k, "value": len(v), "tone": "gray" if k == "링크 없음" else "blue", "note": compress_ids(v)}
             for k, v in sorted(sites.items(), key=lambda kv: (kv[0] == "링크 없음", -len(kv[1]), kv[0]))]
    return {"type": "hbars", "title": "출처 사이트별 근거", "unit": "건", "items": items,
            "source": "근거 원문 주소(source_url, HTTPS만) · 사이트 이름만 셉니다"}


def evidence_fact_chips(c: Ctx) -> dict:
    """모델 연결 방식·게시일 범위·수집일. 값이 없으면 미기재·미기록으로 센다."""
    origins = [e.get("origin") or {} for e in c.evidence]
    matching = Counter(MATCHING_LABEL.get(o.get("model_matching"), o.get("model_matching") or "모델 연결 미기록") for o in origins)
    published = sorted(o["published_date"] for o in origins if o.get("published_date"))
    retrieved = sorted({o["retrieved_date"] for o in origins if o.get("retrieved_date")})
    chips = [{"text": f"{k} {v}건", "tone": "blue"} for k, v in matching.items()]
    if published:
        span = published[0] if published[0] == published[-1] else f"{published[0]} ~ {published[-1]}"
        chips.append({"text": f"게시일 {span} ({len(published)}건)", "tone": "gray"})
    if len(published) < len(origins):
        chips.append({"text": f"게시일 미기재 {len(origins) - len(published)}건", "tone": "gray"})
    if retrieved:
        chips.append({"text": "수집일 " + (retrieved[0] if len(retrieved) == 1 else f"{retrieved[0]} ~ {retrieved[-1]}"), "tone": "gray"})
    return {"type": "chips", "items": chips, "source": "evidence_refs의 origin (model_matching·published_date·retrieved_date)"}


def page_dashboard(c: Ctx) -> list[dict]:
    if not c.has_result:
        return no_result_blocks(c, "근거 대시보드")
    ins = c.ins
    kpis = []
    for k in ins.get("kpis") or []:
        value = c.resolve(k)
        if value is None:
            continue
        kpis.append({key: k[key] for key in ("label", "unit", "tone", "emoji", "note") if key in k} | {"value": value})
    kpi_source = ins.get("kpi_source") or "export 결과의 evidence_refs와 assumptions"
    untyped_types = [ev_type(e) for e in c.evidence if untyped(ev_type(e))]
    if not kpis:
        res = c.result
        kpis = [
            {"label": "등록 근거", "value": len(c.evidence), "unit": "건", "tone": "blue", "note": "결과에 쓴 인용 근거", "source": "evidence_refs"},
            review_kpi(c, untyped_types),
            {"label": "현재 불편", "value": len(res.get("pains") or []), "unit": "개", "tone": "red", "note": "근거에서 찾은 불편", "source": "pains"},
            {"label": "기존 기능", "value": len(res.get("existing_features") or []), "unit": "개", "tone": "green", "note": "대조한 같은 모델 기능",
             "source": "existing_features"},
            {"label": "제안", "value": len(res.get("concepts") or []), "unit": "개", "tone": "orange", "note": status_plain(c.cur["status"]),
             "source": f"concepts · 상태 {c.cur['status']}"},
        ]
        kpi_source = "저장된 결과의 항목 수 (AI 해석 없이 센 값)"
    groups = list(c.groups.values())
    blocks = stale_blocks(c) + insights_notice(c) + [{"type": "section", "text": "핵심 지표"}, {"type": "kpis", "items": kpis, "source": kpi_source}]
    if groups:
        all_ids = [s for g in groups for s in g.get("source_ids") or []]
        donut = {"type": "donut", "title": (ins.get("groups_title") or "의견 묶음") + " (모델 해석)", "unit": "건", "center_label": "관측 의견",
                 "items": [{"label": g["label"], "value": len(g.get("source_ids") or []), "tone": g.get("tone", "blue"),
                            "note": compress_ids(g.get("source_ids") or [])} for g in groups],
                 "source": "묶음은 insights의 모델 해석, 건수는 ID 목록 길이 · " + compress_ids(all_ids)}
        cols = [{"span": 2, "blocks": [donut]}]
        facet = ins.get("facet")
        if facet:
            order = facet.get("order") or []
            fvals = facet.get("values") or {}
            for sid in all_ids:
                if fvals.get(sid) not in order:
                    warn(f"{sid}의 구분값이 facet.order에 없습니다: {fvals.get(sid)}")
            cols.append({"span": 3, "blocks": [{
                "type": "bars", "title": facet.get("title") or "구분별 의견", "unit": "건", "categories": order,
                "series": [{"name": g["label"], "tone": g.get("tone", "blue"),
                            "values": [sum(1 for s in g.get("source_ids") or [] if fvals.get(s) == cat) for cat in order]}
                           for g in groups],
                "source": "묶음·구분값은 모델 해석 · 구분 근거: " + (facet.get("source") or "후기 원문·위치 표기"),
            }]})
        blocks += [{"type": "section", "text": ins.get("groups_title") or "의견 묶음"}, {"type": "row", "cols": cols}]
        blocks.append({"type": "callout", "tone": "info", "text": ins.get("count_note") or "관측 건수입니다. 발생률이나 시장 수요를 뜻하지 않습니다."})
    by_type: dict[str, int] = {}
    for e in c.evidence:
        by_type[ev_type(e)] = by_type.get(ev_type(e), 0) + 1
    type_items = [{"label": t, "value": by_type[t], "tone": TYPE_TONE.get(t, "gray")} for t in type_order(by_type)]
    claim_items = [{"label": f"{cl['id']} {CLAIM_KIND.get(c.kind_of(cl['id']), '')}".strip(),
                    "value": len(cl.get("source_ids") or []), "tone": c.claim_tone(cl["id"]),
                    "note": compress_ids(cl.get("source_ids") or [])} for cl in c.claims]
    blocks += judgment_blocks(c)
    blocks.append({"type": "section", "text": "근거 출처"})
    if not type_items:
        blocks.append({"type": "callout", "tone": "warning", "text": f"현재 결과에 등록된 근거가 없습니다. 상태: **{status_text(c.cur['status'])}**"})
        return blocks
    claim_block = ({"type": "hbars", "title": "항목별 연결 근거", "unit": "건", "items": claim_items,
                    "source": "pains·existing_features·remaining_pains·concepts의 source_ids"}
                   if claim_items else {"type": "callout", "tone": "info", "text": "근거와 연결된 항목이 없습니다."})
    blocks.append({"type": "row", "cols": [
        {"span": 1, "blocks": [source_site_block(c)]},
        {"span": 1, "blocks": [{"type": "hbars", "title": "유형별 등록 근거", "unit": "건", "items": type_items,
                                 "source": TYPE_SOURCE}] + type_note(c)},
    ]})
    blocks.append(evidence_fact_chips(c))
    blocks += [{"type": "section", "text": "불편·기능·제안과 근거"}, claim_block]
    return blocks + insights_howto(c)


def page_screening(c: Ctx) -> list[dict]:
    if not c.has_result:
        return no_result_blocks(c, "후기 선별")
    ins = c.ins
    blocks: list[dict] = stale_blocks(c)
    funnel = []
    for f in ins.get("funnel") or []:
        value = c.resolve(f)
        if value is not None:
            funnel.append({"label": f["label"], "value": value, "tone": f.get("tone", "blue")})
    if funnel:
        blocks += [{"type": "section", "text": "선별 단계"},
                   {"type": "hbars", "title": "후기에서 근거까지", "unit": "건", "items": funnel,
                    "source": ins.get("funnel_source") or "결과 assumptions와 evidence_refs"}]
    if ins.get("keywords"):
        blocks.append({"type": "chips", "title": "검색어", "items": [{"text": k, "tone": "blue"} for k in ins["keywords"]],
                       "source": ins.get("keywords_note")})
    facet_vals = (ins.get("facet") or {}).get("values") or {}

    def quote_block(key: str) -> dict:
        g = c.groups[key]
        items = []
        for sid in g.get("source_ids") or []:
            e = c.ev.get(sid)
            if not e:
                continue
            rid = re.search(r"review-id (\d+)", e.get("location", ""))
            chips = [{"text": facet_vals[sid], "tone": "gray"}] if sid in facet_vals else []
            chips.append({"text": sid, "mono": True})
            items.append({"quote": e.get("quote", ""), "chips": chips,
                          "meta": f"review-id {rid.group(1)}" if rid else e.get("location", ""),
                          "href": https((e.get("origin") or {}).get("source_url"))})
        return {"type": "quotes", "title": f"{g['label']} {len(items)}건", "chip": {"text": "●", "tone": g.get("tone", "blue")}, "items": items}

    columns = ins.get("quote_columns") or [[k] for k in c.groups]
    cols = []
    for keys in columns:
        col_blocks = [quote_block(k) for k in keys if k in c.groups]
        if col_blocks:
            cols.append({"span": 1, "blocks": col_blocks})
    if cols:
        blocks += [{"type": "section", "text": "후기 원문 비교"}, {"type": "row", "cols": cols}]
    else:
        reviews = [e for e in c.evidence if ev_type(e) == "후기"]
        excerpts = [e for e in c.evidence if untyped(ev_type(e))]
        blocks.append({"type": "section", "text": "등록 후기"})
        shown = reviews or excerpts
        if shown:
            title = (f"등록 후기 {len(reviews)}건 (의견 묶음 없이 등록 순서대로)" if reviews
                     else f"후기인지 기록되지 않은 원문 근거 {len(excerpts)}건 (결과에 근거 종류가 없음)")
            blocks.append({"type": "quotes", "title": title, "items": [{
                "quote": e.get("quote", ""),
                "chips": [{"text": e["source_id"], "mono": True},
                          {"text": MATCHING_LABEL.get((e.get("origin") or {}).get("model_matching"), "모델 매칭 미기록"), "tone": "gray"}],
                "meta": e.get("location", ""), "href": https((e.get("origin") or {}).get("source_url")),
            } for e in shown]})
            if reviews and excerpts:
                blocks.append({"type": "callout", "tone": "info", "text": f"후기인지 기록되지 않은 원문 근거 {len(excerpts)}건은 '근거 원문' 화면에 있습니다."})
        else:
            blocks.append({"type": "callout", "tone": "warning", "text": f"현재 결과에 후기나 원문 발췌 근거가 없습니다. 상태: **{status_text(c.cur['status'])}**"})
    if ins.get("excluded"):
        blocks += [{"type": "section", "text": "제외·분리·정정한 후기"}, {
            "type": "table",
            "columns": [{"key": "kind", "label": "구분", "kind": "pill"}, {"key": "ids", "label": "review-id", "kind": "mono"},
                        {"key": "text", "label": "내용", "kind": "wide"}],
            "rows": [{"kind": {"text": x["kind"], "tone": x.get("tone", "gray")}, "ids": x["ids"], "text": x["text"]} for x in ins["excluded"]],
            "source": ins.get("excluded_source") or "결과 validation_findings",
        }]
    findings = c.result.get("validation_findings") or []
    assumptions = c.result.get("assumptions") or []
    if findings:
        blocks.append({"type": "expander", "icon": "🧾", "title": f"검토 메모 원문 {len(findings)}개 (validation_findings)",
                       "open": not ins.get("excluded"), "blocks": [{"type": "list", "items": findings}]})
    if assumptions:
        blocks.append({"type": "expander", "icon": "📌", "title": f"결과 가정 {len(assumptions)}개 (assumptions)",
                       "blocks": [{"type": "list", "items": assumptions}]})
    return blocks


def page_compare(c: Ctx) -> list[dict]:
    if not c.has_result:
        return no_result_blocks(c, "기능 대조")
    ins = c.ins
    titles = ins.get("node_titles") or {}
    tags = ins.get("feature_tags") or {}

    def node(cl: dict) -> dict:
        return {"id": cl["id"], "title": titles.get(cl["id"], ""), "tone": c.claim_tone(cl["id"]),
                "text": cl.get("text", ""), "tags": (tags.get(cl["id"]) or []) + c.chips_for(cl.get("source_ids") or [])}

    res = c.result
    concept_nodes = [{"id": cl["id"], "title": titles.get(cl["id"], ""), "tone": "purple",
                      "text": (ins.get("concept_titles") or {}).get(cl["id"], ""), "tags": c.chips_for(cl.get("source_ids") or [])}
                     for cl in res.get("concepts") or []]
    blocks: list[dict] = stale_blocks(c)
    if ins.get("compare_lead"):
        blocks.append({"type": "lead", "text": ins["compare_lead"]})
    blocks.append({"type": "chain", "columns": [
        {"title": "현재 불편", "nodes": [node(x) for x in res.get("pains") or []]},
        {"title": "기존 기능", "nodes": [node(x) for x in res.get("existing_features") or []]},
        {"title": "남은 불편", "nodes": [node(x) for x in res.get("remaining_pains") or []]},
        {"title": "제안", "nodes": concept_nodes},
    ], "source": "열 사이 화살표는 업무 순서입니다. 항목 사이의 연결은 아래 검토 기록(feature_matches·concept_links)에 적힌 것만 보여줍니다. 칩에 마우스를 올리면 근거 ID가 보입니다."})
    assessment = (c.validation.get("assessment") or {})
    matches = assessment.get("feature_matches") or []
    if matches:
        blocks.append({"type": "section", "text": "검토 기록의 대조 판단"})
        for fm in matches:
            label = RESOLUTION_LABEL.get(fm.get("resolution"), fm.get("resolution", ""))
            blocks.append({"type": "callout", "tone": "info",
                           "text": f"**{fm.get('pain_id')} → {fm.get('remaining_pain_id')} · {label}** {fm.get('rationale', '')}"})
    checks = assessment.get("claim_checks") or []
    if checks:
        blocks.append({"type": "expander", "icon": "🧾", "title": f"주장별 검토 기록 {len(checks)}개", "blocks": [{
            "type": "table",
            "columns": [{"key": "id", "label": "항목", "kind": "mono"}, {"key": "status", "label": "판정", "kind": "pill"},
                        {"key": "scope", "label": "범위"}, {"key": "why", "label": "근거 요약", "kind": "wide"}],
            "rows": [{"id": ch.get("claim_id"), "status": {"text": SUPPORT_LABEL.get(ch.get("support_status"), ch.get("support_status") or "미기록"),
                      "tone": "green" if ch.get("support_status") == "supported" else "orange", "tip": ch.get("support_status") or ""},
                      "scope": SCOPE_RELATION_LABEL.get(ch.get("scope_relation"), ch.get("scope_relation")),
                      "why": ch.get("rationale", "")} for ch in checks],
        }]})
    return blocks


def page_concepts(c: Ctx) -> list[dict]:
    if not c.has_result:
        return no_result_blocks(c, "제안")
    ins = c.ins
    res = c.result
    concepts = res.get("concepts") or []
    cons = c.cur["constraints"]
    links = {l.get("concept_id"): l for l in (c.validation.get("assessment") or {}).get("concept_links") or []}
    blocks: list[dict] = stale_blocks(c)
    if not concepts:
        return blocks + [{"type": "callout", "tone": "warning", "text": f"현재 결과에 제안이 없습니다. 상태: **{status_text(c.cur['status'])}**"}]
    for i, cl in enumerate(concepts, 1):
        cid = cl["id"]
        chips = [{"text": "새 부품 없음" if not cl.get("requires_hardware") else "하드웨어 필요",
                  "tone": "green" if not cl.get("requires_hardware") else "red"}]
        chips += [{"text": ch, "tone": "blue"} for ch in (ins.get("concept_channels") or {}).get(cid, [])]
        chips.append({"text": f"저장 제약: 제안 {i} / 최대 {cons.get('max_concepts', '?')}"})
        blocks += [{"type": "heading", "icon": "💡", "text": f"{cid} · {(ins.get('concept_titles') or {}).get(cid, '제안')}"},
                   {"type": "chips", "items": chips}]
        steps = (ins.get("concept_steps") or {}).get(cid)
        if steps:
            off = [s.get("title", "") for s in steps if s.get("text", "") not in cl.get("text", "")]
            if off:
                warn(f"{cid} 단계 카드 {', '.join(off)}의 문장이 제안 원문과 달라 그리지 않았습니다.")
            else:
                blocks.append({"type": "cards", "numbered": True, "items": steps})
        blocks.append({"type": "expander", "icon": "📝", "title": "제안 원문", "blocks": [{"type": "text", "text": cl.get("text", "")}]})
        impl = cl.get("implementation_steps")
        if impl:
            blocks.append({"type": "list", "title": f"구현 단계 {len(impl)}", "items": impl})
        else:
            blocks.append({"type": "callout", "tone": "info", "text": "구현 단계: **미작성** (이 결과에는 implementation_steps가 없습니다)"})
        plan = cl.get("validation_plan")
        if plan:
            plan_status = plan.get("status")
            blocks.append({"type": "table", "title": "검증 계획 · " + PLAN_STATUS.get(plan_status, plan_status or "상태 미기록"), "count": False,
                           "columns": [{"key": "k", "label": "항목", "kind": "mono"}, {"key": "v", "label": "내용", "kind": "wide"}],
                           "rows": [{"k": label, "v": plan.get(key) or "미작성"} for key, label in PLAN_FIELDS]})
        else:
            blocks.append({"type": "callout", "tone": "info", "text": "검증 계획: **미작성** (이 결과에는 validation_plan이 없습니다)"})
        blocks.append({"type": "row", "cols": [
            {"span": 1, "blocks": [{"type": "list", "title": f"요구사항 {len(cl.get('requirements') or [])}", "items": cl.get("requirements") or []}]},
            {"span": 1, "blocks": [{"type": "list", "title": f"가정 {len(cl.get('assumptions') or [])}", "items": cl.get("assumptions") or []}]},
        ]})
        link = links.get(cid)
        if link:
            blocks.append({"type": "chips", "title": "검토 기록", "items": [
                duplicate_chip(link),
                {"text": "내부 치수 필요 " + ("예" if link.get("geometry_required") else "아니오"), "tone": "orange" if link.get("geometry_required") else "green"},
                {"text": "연결된 남은 불편 " + ", ".join(link.get("remaining_pain_ids") or []), "tone": "orange"},
            ]})
        blocks.append({"type": "chips", "title": f"근거 {len(cl.get('source_ids') or [])}건",
                       "items": [{"text": s, "mono": True} for s in cl.get("source_ids") or []]})
    blocks.append({"type": "callout", "tone": "warning", "text": "검토 통과는 효과의 증명이 아닙니다. 효과·비용·시장성은 측정 전 미확정입니다."})
    return blocks


def turn_note(c: Ctx, r: dict) -> str:
    if r is c.cur:
        return "현재 turn" + ("" if r["valid"] else f" · 무효({r['invalidation'] or '사유 미기록'})")
    if r["invalidation"]:
        return f"역사적 기록 · 무효({r['invalidation']})"
    return "역사적 기록"


def investigation_blocks(c: Ctx) -> list[dict]:
    """The investigation journal and access failures from the web result (what was planned, opened, failed, stopped)."""
    if not c.web:
        return []
    inv = c.web.get("investigation") if isinstance(c.web.get("investigation"), dict) else {}
    events = [e for e in c.web.get("investigation_events") or [] if isinstance(e, dict)]
    failures = [f for f in c.web.get("access_failures") or [] if isinstance(f, dict)]
    if not inv.get("tracked") and not events and not failures:
        return [{"type": "section", "text": "조사 과정 (웹 전달 파일)"},
                {"type": "callout", "tone": "info", "text": "이 결과에는 조사 과정 기록이 없습니다(업무 시계를 쓰지 않은 요청)."}]
    counts = inv.get("counts") if isinstance(inv.get("counts"), dict) else {}
    budget = inv.get("budget_seconds")
    stop = inv.get("stop") if isinstance(inv.get("stop"), dict) else {}
    chips = [{"text": f"업무 시계 {budget // 60}분" if isinstance(budget, int) else "업무 시계 미기록", "tone": "gray"},
             {"text": f"시작 {kst(inv.get('started_at'))}", "tone": "gray", "mono": True}]
    if inv.get("research_stopped_at"):
        chips.append({"text": f"조사 멈춤 {kst(inv['research_stopped_at'])} · {STOP_LABEL.get(stop.get('code'), stop.get('code') or '사유 미기록')}", "tone": "orange"})
    if isinstance(counts.get("analysed_source_record_count"), int):
        chips.append({"text": f"분석 범위로 신고한 원문 {counts['analysed_source_record_count']}건", "tone": "blue"})
    rows = []
    for e in events:
        d = e.get("data") if isinstance(e.get("data"), dict) else {}
        kind = e.get("kind")
        if kind == "research_plan":
            plan = "·".join(COVERAGE_PLAN.get(x, x) for x in d.get("coverage") or [])
            what = f"{d.get('product_name') or '제품명 미기록'} · 살필 범위 {plan or '미기록'} · 자료 계획 {len(d.get('source_plan') or [])}개"
            state = {"text": "계획", "tone": "gray"}
        elif kind == "source_scan":
            url = https(d.get("source_url"))
            host = re.sub(r"^https://([^/]+).*$", r"\1", url) if url else "주소 없음"
            reviews = d.get("reviews") if isinstance(d.get("reviews"), list) else []
            what = f"{d.get('page_label') or '페이지 이름 미기록'} · {host}" + (f" · 후기 {len(reviews)}건" if reviews else "")
            st = d.get("status")
            state = {"text": SCAN_STATUS.get(st, st or "미기록"), "tone": "green" if st == "observed" else "red" if st == "inaccessible" else "gray"}
        elif kind == "analysis_scope":
            what = f"분석 범위 원문 {len(d.get('source_ids') or [])}건 · {clip(d.get('scope_note') or '', 160)}"
            state = {"text": "범위", "tone": "blue"}
        else:
            remaining = d.get("remaining_scope") or []
            what = clip(d.get("basis") or "근거 미기록", 200) + (f" · 남은 범위 {len(remaining)}개" if remaining else "")
            state = {"text": STOP_LABEL.get(d.get("code"), d.get("code") or "미기록"), "tone": "orange"}
        rows.append({"time": kst(e.get("observed_at")), "step": EVENT_LABEL.get(kind, kind or "미기록"), "state": state, "what": what})
    blocks = [{"type": "section", "text": "조사 과정 (웹 전달 파일)"}, {"type": "chips", "items": chips}]
    if failures:
        lines = []
        for f in failures[:8]:
            url = https(f.get("source_url"))
            host = re.sub(r"^https://([^/]+).*$", r"\1", url) if url else "주소 없음"
            lines.append(f"{f.get('page_label') or '페이지 이름 미기록'} ({host})")
        blocks.append({"type": "callout", "tone": "warning",
                       "text": f"**접근하지 못한 자료 {len(failures)}건**: " + ", ".join(lines) + (" 외" if len(failures) > 8 else "")
                               + ". 접근 실패 관측이며 이 자료의 내용을 분석 근거로 확보했다는 뜻은 아닙니다."})
    if rows:
        blocks.append({"type": "table", "columns": [
            {"key": "time", "label": "시각(KST)", "kind": "mono"}, {"key": "step", "label": "단계"},
            {"key": "state", "label": "상태", "kind": "pill"}, {"key": "what", "label": "내용", "kind": "wide"}],
            "rows": rows, "source": "웹 전달 파일의 investigation_events · 하네스 작업 일지에 적힌 그대로 · 조사 폭·대표성의 증명이 아닙니다"})
    return blocks


def page_history(c: Ctx) -> list[dict]:
    return history_blocks(c) + investigation_blocks(c)


def history_blocks(c: Ctx) -> list[dict]:
    rows = c.rows
    x = [f"T{r['n']} {kst(r['created'], '%H:%M')}\n{r['model']}" for r in rows]
    usage = c.export.get("usage_summary") or {}
    blocks = [
        {"type": "section", "text": "turn별 등록 근거"},
        {"type": "line", "title": "turn별 등록 근거 수(마지막 승인 후보)", "unit": "건", "x": x, "series": [{
            "name": "등록 근거", "tone": "blue", "values": [r["evidence"] for r in rows],
            "point_tones": [STATUS_TONE.get(r["status"], "gray") for r in rows],
            "point_notes": [f"{status_text(r['status'])} · 자료 {version_label(r['data_version'])}" for r in rows],
        }], "source": "turns[].candidates 중 승인된 마지막 후보의 evidence_refs · 점 색은 상태 · 순서는 export의 turn 순서"},
        {"type": "chips", "items": [{"text": f"● {STATUS_LABEL.get(s, s)}", "tone": STATUS_TONE.get(s, "gray")} for s in dict.fromkeys(r["status"] for r in rows)]},
        {"type": "section", "text": "관측 사용량"},
    ]
    # 사용량 기록이 없거나 출력 토큰이 미측정인 호출이 있으면 그리지 않는다(미측정은 0이 아니다).
    if rows and all(r["calls"] and not r["out_unknown"] for r in rows):
        blocks.append({"type": "row", "cols": [
            {"span": 1, "blocks": [{"type": "line", "title": "turn별 출력 토큰", "x": [f"T{r['n']}" for r in rows], "height": 260,
                                     "series": [{"name": "출력 토큰", "tone": "purple", "values": [r["out"] for r in rows], "area": True}],
                                     "source": "turns[].usage[].output_tokens 합계(모든 호출 측정)"}]},
            {"span": 1, "blocks": [{"type": "bars", "title": "turn별 기록 호출", "unit": "회", "categories": [f"T{r['n']}" for r in rows],
                                     "series": [{"name": "기록 호출", "tone": "orange", "values": [r["calls"] for r in rows]}],
                                     "source": "turns[].usage 건수"}]},
        ]})
    else:
        none = ", ".join(f"T{r['n']}" for r in rows if not r["calls"])
        partial = ", ".join(f"T{r['n']}({r['out_unknown']}/{r['calls']}건)" for r in rows if r["calls"] and r["out_unknown"])
        parts = ([f"사용량 기록이 없는 turn {none}"] if none else []) + ([f"출력 토큰 미측정 호출이 있는 turn {partial}"] if partial else [])
        blocks.append({"type": "callout", "tone": "warning",
                       "text": f"{' · '.join(parts)}이 있어 사용량 차트를 그리지 않았습니다. 기록이 없는 값은 0이 아니라 **미측정**입니다."})
    recorded = usage.get("recorded_calls")
    default_note = (f"기록된 호출 {recorded}건 기준입니다(상태 {USAGE_STATUS.get(usage.get('status'), usage.get('status', '미기록'))}, "
                    f"{usage.get('coverage', '범위 미기록')}). 비용·reasoning 토큰은 기록이 없으면 미측정입니다.") if recorded else (
                   f"이 세션에는 사용량 기록이 없습니다(상태 {usage.get('status', '미기록')}). 실제 호출이 0이라는 뜻이 아니라 미측정입니다.")
    events = sum(r["invocations"] for r in rows)
    blocks += [
        {"type": "callout", "tone": "info", "text": c.ins.get("usage_note") or default_note},
        {"type": "callout", "tone": "info",
         "text": f"이 화면은 저장된 업무 기록의 재생입니다. export의 도구 사건(invocations)은 {events}건이며, "
                 + ("실제 Agent·Skill·Tool 호출 사건은 표시하지 않습니다." if not events else "도구 사건은 아래 목록의 건수로만 표시합니다.")},
        {"type": "section", "text": "turn 목록"},
        {"type": "table", "columns": [
            {"key": "t", "label": "turn", "kind": "mono"}, {"key": "time", "label": "시각(KST)", "kind": "mono"},
            {"key": "model", "label": "모델", "kind": "mono"}, {"key": "q", "label": "질문", "kind": "wide"},
            {"key": "status", "label": "상태", "kind": "pill"}, {"key": "ver", "label": "자료", "kind": "mono"},
            {"key": "cands", "label": "후보", "kind": "num"}, {"key": "ev", "label": "근거", "kind": "num"},
            {"key": "calls", "label": "기록 호출", "kind": "num"}, {"key": "note", "label": "비고"},
        ], "rows": [{
            "t": f"T{r['n']}", "time": kst(r["created"]), "model": r["model"], "q": r["question"],
            "status": {"text": status_text(r["status"]), "tone": STATUS_TONE.get(r["status"], "gray")},
            "ver": version_label(r["data_version"]), "cands": r["cands"], "ev": r["evidence"],
            "calls": r["calls"] if r["calls"] else "기록 없음", "note": turn_note(c, r),
        } for r in rows]},
    ]
    if c.turnless:
        blocks += [{"type": "section", "text": f"turn 없는 요청 {len(c.turnless)}건"}, {"type": "table", "columns": [
            {"key": "q", "label": "질문", "kind": "wide"}, {"key": "model", "label": "모델", "kind": "mono"},
            {"key": "status", "label": "상태", "kind": "pill"}, {"key": "why", "label": "멈춘 이유", "kind": "wide"},
            {"key": "when", "label": "위치"}],
            "rows": [{"q": r["question"], "model": r["model"], "status": {"text": status_text(r["status"]), "tone": STATUS_TONE.get(r["status"], "gray")},
                      "why": (f"`{r['code']}` " if r["code"] else "") + (r["reason"] or "사유 미기록"),
                      "when": r["where"]} for r in c.turnless],
            "source": "requests[] 중 turn_id가 없는 요청 · export에 요청 시각이 없어 순서는 prior_turn_id가 마지막 turn인 경우만 압니다"}]
    cand_rows = []
    for r in rows:
        for cand in r["candidates"]:
            res, ok = cand.get("result") or {}, accepted(cand)
            rej = rejection_of(cand)
            shown = ok and r is c.cur and c.has_result and res == c.result
            stored_only = rej and rej["code"] == "stored_unreviewed"
            note = ("무효 결과(현재 아님)" if c.invalid else "현재 결과") if shown else ("역사적 기록" if ok else "구조 저장 이력(현재 전달 아님)" if stored_only else "거절 후보(현재 결과 아님)")
            cand_rows.append({
                "t": f"T{r['n']}", "v": f"v{cand.get('result_version', '?')}", "key": cand.get("result_key", ""),
                "status": {"text": status_text(res.get("status")), "tone": STATUS_TONE.get(res.get("status"), "gray") if ok else "gray"},
                "check": {"text": "승인" if ok else "구조 저장 · 검토 미확인" if stored_only else f"거절 · {rej['code']}", "tone": "green" if ok else "orange" if stored_only else "red"},
                "why": "" if ok else rejection_text(rej),
                "ev": len(res.get("evidence_refs") or []),
                "note": note,
            })
    if cand_rows:
        blocks.append({"type": "expander", "icon": "🗂️", "title": f"저장된 후보 {len(cand_rows)}개 (거절·수정 후보 포함)",
                       "open": any(row["check"]["tone"] == "red" for row in cand_rows), "blocks": [{
            "type": "table",
            "columns": [{"key": "t", "label": "turn", "kind": "mono"}, {"key": "v", "label": "버전", "kind": "mono"},
                        {"key": "key", "label": "result_key", "kind": "mono"}, {"key": "status", "label": "모델이 쓴 상태", "kind": "pill"},
                        {"key": "check", "label": "저장 판정", "kind": "pill"}, {"key": "why", "label": "거절 사유", "kind": "wide"},
                        {"key": "ev", "label": "근거", "kind": "num"}, {"key": "note", "label": "비고"}],
            "rows": cand_rows,
            "source": "turns[].candidates · 저장 판정은 validation.contract_valid·error · 승인도 의미 품질 통과가 아닙니다",
        }]})
    if c.web:
        blocks += [{"type": "section", "text": "현재 버전의 검토·조사 이력"}]
        for label, key in (("근거 범위", "coverage"), ("근거 검토·전달 이력", "evidence_history"),
                           ("조사 상태", "investigation"), ("조사 사건", "investigation_events")):
            blocks.append({"type": "expander", "title": label, "blocks": [
                {"type": "table", "columns": [{"key": "record", "label": "저장 기록", "kind": "wide"}],
                 "rows": [{"record": json.dumps(c.web.get(key), ensure_ascii=False, indent=2)}],
                 "source": "검토된 현재 결과와 동일한 버전·조사 지문의 불변 웹 자료"}]})
    return blocks


def web_source_blocks(c: Ctx) -> list[dict]:
    """Every selected registered source from the web result, with whether the result cites it."""
    if not c.web:
        return []
    sources = [s for s in c.web.get("sources") or [] if isinstance(s, dict)]
    cov = c.web.get("coverage") if isinstance(c.web.get("coverage"), dict) else {}
    kind_label = {"review": "후기", "product_fact": "제품 사실"}
    rows = []
    for s in sources:
        sid = s.get("source_id") or ""
        origin = s.get("origin") if isinstance(s.get("origin"), dict) else {}
        url = https(origin.get("source_url"))
        t = kind_label.get(s.get("kind"), "기타")
        cited = sid in c.ev
        rows.append({"id": sid, "type": {"text": t, "tone": TYPE_TONE.get(t, "gray")},
                     "cited": {"text": "결과에 인용" if cited else "인용 안 함", "tone": "blue" if cited else "gray"},
                     "quote": s.get("text") or "", "loc": s.get("location") or "",
                     "url": {"href": url, "text": re.sub(r"^https://([^/]+).*$", r"\1", url)} if url else None})
    count = lambda key: cov.get(key) if isinstance(cov.get(key), int) else "미기록"
    return [
        {"type": "section", "text": f"등록 원문 전체 {len(sources)}건 (웹 전달 파일)"},
        {"type": "metrics", "items": [
            {"label": "선택한 원문", "value": count("selected_count")}, {"label": "전달", "value": count("delivered_count")},
            {"label": "검토 신고", "value": count("caller_reviewed_count")}, {"label": "제외 신고", "value": count("caller_excluded_count")},
            {"label": "전달 누락", "value": count("missing_delivery_count")}, {"label": "결과에 인용", "value": sum(1 for s in sources if s.get("source_id") in c.ev)}]},
        {"type": "table", "search": True, "search_placeholder": "원문·위치·ID 검색", "filter": "type",
         "columns": [{"key": "id", "label": "ID", "kind": "mono"}, {"key": "type", "label": "유형", "kind": "pill"},
                     {"key": "cited", "label": "결과", "kind": "pill"}, {"key": "quote", "label": "등록 원문", "kind": "wide"},
                     {"key": "loc", "label": "위치", "kind": "mid"}, {"key": "url", "label": "원문", "kind": "link"}],
         "rows": rows,
         "source": "웹 전달 파일의 sources · 인용한 원문만이 아니라 선택한 등록 원문 전체 · 원문은 저장된 그대로이며 화면이 고치지 않습니다 · "
                   "건수는 등록 기록 수이며 고객 수나 대표성이 아닙니다 · 검토 신고는 모델이 신고한 처리이며 독립 인증이 아닙니다"},
    ]


def page_evidence(c: Ctx) -> list[dict]:
    return evidence_blocks(c) + web_source_blocks(c)


def evidence_blocks(c: Ctx) -> list[dict]:
    if not c.has_result:
        return no_result_blocks(c, "근거 원문")
    matching: dict[str, int] = {}
    for e in c.evidence:
        m = (e.get("origin") or {}).get("model_matching") or "미기록"
        matching[m] = matching.get(m, 0) + 1
    doc_versions = sorted({e.get("document_version") or "미기록" for e in c.evidence})
    if not c.evidence and not c.web:
        return [{"type": "callout", "tone": "warning", "text": f"현재 결과에 등록된 근거가 없습니다. 상태: **{status_text(c.cur['status'])}**"}]
    representation = {"excerpt": "원문 발췌", "factual_summary": "사실 요약", "synthetic": "합성"}
    rows = []
    for e in c.evidence:
        sid = e["source_id"]
        t = ev_type(e)
        origin = e.get("origin") or {}
        url = https(origin.get("source_url"))
        purchase, sponsor = origin.get("purchase_verified"), origin.get("sponsorship")
        pv = f"구매 {'미확인' if purchase is None else purchase}\n협찬 {'미확인' if sponsor is None else sponsor}"
        if origin.get("commercial_disclosure"):
            pv += f"\n상업 고지: {origin['commercial_disclosure']}"
        rows.append({
            "id": sid, "type": {"text": t, "tone": TYPE_TONE.get(t, "gray")}, "quote": e.get("quote", ""),
            "rep": representation.get(origin.get("representation"), origin.get("representation") or "미기록"),
            "loc": e.get("location", ""), "links": [{"text": x, "tone": c.claim_tone(x)} for x in c.links.get(sid, [])],
            "scope": MATCHING_LABEL.get(origin.get("model_matching"), origin.get("model_matching") or "미기록"),
            "dates": f"게시 {origin.get('published_date') or '미기재'}\n관측 {origin.get('retrieved_date') or '미기록'}",
            "pv": pv,
            "sha": e.get("sha256") or "미기록",
            "url": {"href": url, "text": re.sub(r"^https://([^/]+).*$", r"\1", url)} if url else None,
        })
    blocks = stale_blocks(c) + [
        {"type": "chips", "items": [{"text": f"문서 {v}", "mono": True} for v in doc_versions]
         + [{"text": f"자료 {c.cur['data_version']}", "mono": True}]
         + [{"text": f"{MATCHING_LABEL.get(k, k)} {v}", "tone": "blue"} for k, v in matching.items()]},
        {"type": "table", "search": True, "search_placeholder": "인용·위치·ID 검색", "filter": "type",
         "columns": [{"key": "id", "label": "ID", "kind": "mono"}, {"key": "type", "label": "유형", "kind": "pill"},
                     {"key": "quote", "label": "인용", "kind": "wide"}, {"key": "rep", "label": "표현"},
                     {"key": "loc", "label": "위치", "kind": "mid"}, {"key": "scope", "label": "모델 범위"},
                     {"key": "dates", "label": "게시·관측일", "kind": "mono"}, {"key": "pv", "label": "구매·협찬·고지"},
                     {"key": "links", "label": "연결 항목", "kind": "chips"}, {"key": "sha", "label": "SHA-256", "kind": "mono"},
                     {"key": "url", "label": "원문", "kind": "link"}],
         "rows": rows, "source": "현재 결과의 evidence_refs · 유형은 원문 지문이 일치하는 출처 메타데이터의 kind, 이전 export는 "
                                 "source_id 접두어나 원문 표현 · 링크는 HTTPS 주소만 표시"},
    ]
    if c.web:
        blocks += [{"type": "section", "text": "선택 등록본문 전체"},
                   {"type": "callout", "tone": "info", "text": "위 표는 결과에 사용한 인용입니다. 아래는 선택된 등록본문 전체이며, 원본 전체 문서 인증이나 의미 품질 통과를 뜻하지 않습니다."}]
        for source in c.web.get("sources") or []:
            blocks.append({"type": "expander", "title": source["source_id"], "blocks": [
                {"type": "table", "columns": [{"key": "field", "label": "항목"}, {"key": "value", "label": "저장 내용", "kind": "wide"}],
                 "rows": [{"field": key, "value": (source.get(key) if isinstance(source.get(key), str)
                           else json.dumps(source.get(key), ensure_ascii=False, indent=2))}
                          for key in ("source_id", "kind", "model_id", "model_version", "document_version", "data_version",
                                      "sha256", "location", "origin", "text")],
                 "source": "sources[] · 등록본문·전체 SHA-256과 출처 메타데이터 · 본문 생략 없음"}]})
    return blocks


def usage_metric(usage: dict, label: str, field: str) -> dict:
    """부분 측정이면 합계 옆에 미측정 건수를 적는다. 값이 없으면 0이 아니라 미측정이다."""
    value = (usage.get("totals") or {}).get(field)
    unknown = (usage.get("unknown_counts") or {}).get(field) or 0
    calls = usage.get("recorded_calls") or 0
    if value is None:
        return {"label": label, "value": "미측정", "note": f"{calls}건 모두 미측정" if calls else ""}
    if unknown:
        return {"label": label, "value": value, "note": f"부분 합계 · {calls}건 중 {unknown}건 미측정"}
    return {"label": label, "value": value}


def web_file_blocks(c: Ctx) -> list[dict]:
    if not c.web or not c.web_file:
        return []
    b = c.web.get("binding") or {}
    name = c.web_file["name"]
    return [
        {"type": "section", "text": "웹 전달 파일"},
        {"type": "files", "items": [
            {"label": "파일", "value": name},
            {"label": "경로", "value": f"runtime-data/web-deliveries/{name}"},
            {"label": "SHA-256", "value": c.web_file["sha256"]},
            {"label": "결과 버전 · 자료 버전", "value": f"v{b.get('result_version', '?')} · {b.get('data_version') or '미기록'}", "copy": False},
        ]},
        {"type": "chips", "items": [
            {"text": "✓ 파일 이름(SHA-256)과 내용 일치", "tone": "green"},
            {"text": "✓ 검토된 현재 결과의 전체 binding 일치", "tone": "green"},
            semantic_chip(c.web),
            {"text": "화면 연결·HTML 검수는 하네스가 하지 않음", "tone": "gray"}]},
    ]


def page_export(c: Ctx) -> list[dict]:
    blocks = export_blocks(c)
    at = next((i for i, b in enumerate(blocks) if b.get("type") == "section" and b.get("text") == "관측 사용량 합계"), len(blocks))
    return blocks[:at] + web_file_blocks(c) + blocks[at:]


def export_blocks(c: Ctx) -> list[dict]:
    cur = c.cur
    val = c.validation if c.has_result else cur["last_validation"]
    review = val.get("review") or {}
    raw = c.export_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    # 사용자 이름이 든 절대 경로를 화면·공유 보고서에 넣지 않는다.
    resolved = c.export_path.resolve()
    in_exports = resolved.parent.name == "exports" and resolved.parent.parent.name == "runtime-data"
    rel_project = f"runtime-data/exports/{resolved.name}" if in_exports else resolved.name
    usage = c.export.get("usage_summary") or {}
    ok = cur["status"] == "completed" and cur["valid"] and c.has_result
    # 구조·계약 검사는 저장 판정(validation)에서, 나머지는 검토 기록(review)에서 읽는다.
    checks = [(val, "structural_valid", "구조 검사"), (val, "contract_valid", "저장 승인(계약 검사)"),
              (review, "contract_valid", "검토 기록 계약"), (review, "reported_reasoning_consistent", "검토 기록 정합성"),
              (review, "can_finalize_reported_result", "완료 보고 가능")]
    # 보여주는 결과가 없으면 마지막 후보의 검사를 보이되, 그 후보가 거절인지·승인됐지만 현재 결과가 아닌지 구분한다.
    if c.has_result:
        check_title, dim = "저장 검사" + (" (무효 처리된 결과)" if c.invalid else ""), False
    elif not cur["cands"]:
        check_title, dim = "저장 검사 (저장된 후보 없음)", False
    elif cur["rejection"]:
        check_title, dim = "저장 검사 (마지막 거절 후보)", False
    else:
        check_title, dim = "저장 검사 (마지막 저장 후보 · 현재 결과 아님)", True
    chips = [{"text": ("✓ " if src.get(k) else "✗ ") + label, "tone": "gray" if dim else ("green" if src.get(k) else "red")}
             for src, k, label in checks if k in src]
    if dim:
        chips.insert(0, {"text": f"현재 결과 아님: turn 상태 {status_text(cur['status'])} · 완료 보고 대상 아님", "tone": "red"})
    if cur["rejection"] and not c.has_result:
        chips.append({"text": f"거절: {cur['rejection']['code']}", "tone": "red"})
    if "planning_detail_complete" in val:
        chips.append({"text": ("✓ " if val["planning_detail_complete"] else "✗ ") + "세부 필드 있음 (필드 존재 검사일 뿐, 평가 통과 아님)",
                      "tone": "gray" if dim else ("green" if val["planning_detail_complete"] else "red")})
    if review.get("completion_scope"):
        chips.append({"text": "완료 범위: " + ("기획 초안" if review["completion_scope"] == "planning_draft_only" else review["completion_scope"]), "tone": "blue"})
    if val:
        chips.append({"text": f"확인한 근거 {val.get('checked_sources', review.get('checked_sources', '?'))}건", "tone": "blue"})
    check_blocks = [{"type": "chips", "items": chips}] if chips else [{"type": "callout", "tone": "info", "text": "저장된 후보가 없어 저장 검사 기록이 없습니다."}]
    calls = usage.get("recorded_calls")
    head = (f"마지막 저장: **{status_text(cur['status'])}** · valid={str(cur['valid']).lower()} · 근거 {len(c.evidence)}건 · 수정 {cur['revisions']}회"
            if c.has_result else f"승인된 결과 없음: **{status_text(cur['status'])}** · 후보 {cur['cands']}개"
            + (f" · 마지막 후보 거절 {rejection_text(cur['rejection'])}" if cur["rejection"] else ""))
    return [
        {"type": "callout", "tone": "success" if ok else "warning", "text": head},
        {"type": "callout", "tone": "warning",
         "text": f"semantic_status: **{c.export.get('semantic_status', '미기록')}** · acceptance_ready: **{str(c.export.get('acceptance_ready')).lower()}**. "
                 "검토 통과는 원문 의미·성능·효과의 자동 증명이 아닙니다."},
        {"type": "section", "text": check_title},
        *check_blocks,
        *([
            {"type": "section", "text": "세션 export"},
            {"type": "files", "items": [
                {"label": "파일", "value": c.export_path.name},
                {"label": "경로", "value": rel_project},
                {"label": "크기", "value": f"{len(raw):,}바이트 ({human_size(len(raw))})", "copy": False},
                {"label": "SHA-256", "value": sha},
            ]}]),
        {"type": "section", "text": "관측 사용량 합계"},
        {"type": "metrics", "items": [
            {"label": "기록 호출", "value": calls if calls else "기록 없음",
             "note": f"사용량 상태 {USAGE_STATUS.get(usage.get('status'), usage.get('status', '미기록'))}"},
            usage_metric(usage, "입력 토큰", "input_tokens"), usage_metric(usage, "캐시 토큰", "cache_tokens"),
            usage_metric(usage, "출력 토큰", "output_tokens"), usage_metric(usage, "비용(USD)", "cost_usd"),
            usage_metric(usage, "reasoning 토큰", "reasoning_tokens"),
        ]},
        {"type": "section", "text": "미확인 항목"},
        {"type": "list", "items": c.ins.get("unresolved") or ["insights에 미확인 항목이 없습니다."]},
        {"type": "expander", "icon": "🔍", "title": "검토가 요구하는 의미 검사",
         "blocks": [{"type": "list", "items": (review.get("semantic_checks_required") or val.get("semantic_checks_required") or [])
                     + ([f"판단 메모 구분 범위: {val['decision_basis_scope']}"] if val.get("decision_basis_scope") else [])}]},
    ]


BUILDERS = {
    "story": page_story, "overview": page_overview, "dashboard": page_dashboard, "screening": page_screening, "compare": page_compare,
    "concepts": page_concepts, "history": page_history, "evidence": page_evidence, "export": page_export,
}


def custom_pages(ins: dict, start: int, values: dict) -> list[dict]:
    """insights의 pages: 모델이 블록을 직접 쓴 화면(작업 중간 시각자료). 블록 형식은 README.md 참고."""
    pages = []
    for i, p in enumerate(ins.get("pages") or [], start):
        if not p.get("id") or not isinstance(p.get("blocks"), list):
            warn("id와 blocks가 없는 pages 항목은 건너뜁니다.")
            continue
        cap = p.get("caption") or {}
        caption = {"title": f"{i:02d} · " + fill(cap["title"], values) if cap.get("title") else "",
                   "text": fill(cap.get("text", ""), values)}
        if cap.get("meta"):
            caption["meta"] = cap["meta"]
        pages.append({"id": p["id"], "nav": p.get("nav") or p.get("title", p["id"]), "icon": p.get("icon", "📄"),
                      "title": p.get("title", p["id"]), "title_icon": p.get("title_icon", p.get("icon", "📄")),
                      "caption": caption if caption["title"] or caption["text"] else None, "blocks": p["blocks"]})
    return pages


def warning_block() -> dict | None:
    """화면을 만들며 생긴 경고를 화면에도 보여준다(상태 파일에만 두지 않는다)."""
    if not warnings:
        return None
    return {"type": "callout", "tone": "warning",
            "text": f"**화면 생성 경고 {len(warnings)}건.** insights·결과가 서로 맞지 않는 부분은 그리지 않았습니다. · " + " · ".join(warnings[:8])
                    + (" · …" if len(warnings) > 8 else "")}


def build(c: Ctx | None, ins: dict, focus: str | None) -> dict:
    pages = []
    if c:
        caps = ins.get("captions") or {}
        family = c.cur["family"]
        if c.cur["scope_mode"] == "family_catalog":
            default_title = f"{family_label(family)} 제품군 상품기획"
        else:
            default_title = f"{c.cur['model']} {FAMILY[family][0] + ' ' if family in FAMILY else ''}상품기획"
        for i, (pid, nav, icon, title, title_icon) in enumerate(PAGES, 1):
            cap_title, cap_text = DEFAULT_CAPTIONS[pid]
            given = caps.get(pid) or {}
            pages.append({
                "id": pid, "nav": nav, "icon": icon,
                "title": title or ins.get("title") or default_title,
                "title_icon": title_icon or ins.get("title_icon") or (FAMILY[family][1] if family in FAMILY else "📋"),
                "caption": {"title": f"{i:02d} · " + fill(given.get("title", cap_title), c.values),
                            "text": fill(given.get("text", cap_text), c.values)},
                "blocks": BUILDERS[pid](c) + ([] if c.web else [{"type": "callout", "tone": "warning", "text":
                    "현재 웹 전달 미검증: 검토된 현재 결과와 같은 버전·코드·자료·조사 지문의 웹 자료 연결을 확인하지 못했습니다. 저장된 후보는 이력에서 확인할 수 있습니다."}]),
            })
    pages += custom_pages(ins, len(pages) + 1, c.values if c else {})
    if not pages:
        raise SystemExit("그릴 화면이 없습니다. --export를 주거나 insights에 pages를 쓰세요.")
    ids = [p["id"] for p in pages]
    if len(set(ids)) != len(ids):
        raise SystemExit("화면 id가 겹칩니다: " + ", ".join(ids))
    if focus and focus not in ids:
        warn(f"--focus {focus}는 없는 화면입니다. 첫 화면을 보여줍니다.")
        focus = None
    notice = warning_block()
    if notice:
        for p in pages:
            if p["id"] in ("story", "overview", "dashboard"):
                p["blocks"].insert(1 if p["id"] == "story" else 0, notice)
    if c:
        usage = c.export.get("usage_summary") or {}
        name = c.export_path.name
        status = []
        if c.pending:  # 어느 요청이 최신인지 고르지 않는다(export에 요청 시각이 없다)
            status.append(turnless_chip(c.pending))
        status += [{"text": ("마지막 결과 " if c.pending else "") + status_plain(c.cur["status"]), "tone": STATUS_TONE.get(c.cur["status"], "gray"),
                    "tip": f"status: {c.cur['status']}"},
                   {"text": "유효" if c.cur["valid"] else "무효", "tone": "green" if c.cur["valid"] else "red",
                    "tip": f"valid: {str(c.cur['valid']).lower()}" + ("" if c.cur["valid"] else f" · {c.cur['invalidation'] or '사유 미기록'}")}]
        if not c.has_result:
            status.append({"text": "승인된 결과 없음", "tone": "red"})
        if c.synthetic:
            status.append({"text": "합성 시험 자료", "tone": "purple"})
        status.append(semantic_chip(c.export))
        if warnings:
            status.append({"text": f"화면 경고 {len(warnings)}", "tone": "orange"})
        # 제품군 질문이면 모델 이름에 이미 제품군이 들어 있으니 한 번만 쓴다.
        default_meta = "{model} · 자료 {version} · 저장된 실행 결과" if c.values["family"] in c.values["model"] else \
            "{model} · {family} · 자료 {version} · 저장된 실행 결과"
        context = {
            "meta": fill(ins.get("meta") or default_meta, c.values),
            "file": {"name": name if len(name) <= 40 else f"{name[:22]}…{name[-14:]}", "size": human_size(c.export_path.stat().st_size)},
            "loaded": f"근거 {len(c.evidence)}건 · 질문 {len(c.rows)}개",
            "status": status,
            "footer": [f"🗄️ 기록된 호출 {usage['recorded_calls']}건" if usage.get("recorded_calls") else "🗄️ 사용량 기록 없음 (미측정)",
                       f"🆔 Session: `{c.export.get('session_id', '')[:16]}…`"],
        }
    else:
        context = {"meta": ins.get("meta", ""), "loaded": f"화면 {len(pages)}개 · export 전",
                   "status": [{"text": ins.get("status", "진행 중"), "tone": "orange"}], "footer": []}
    return {
        "kind": "lgax-view", "schema": 1,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "focus": focus,
        "app": {"title": "LG AX 상품기획", "subtitle": "하네스 시각자료 뷰어", "icon": "📊"},
        "context": context,
        "pages": pages,
        "warnings": list(warnings),
    }


REQUEST_CAPTION = {
    "needs_input": "입력 필요로 멈춘 요청 기록입니다. 제품군이나 정확한 모델을 정해 다시 질문해야 합니다.",
    "research_required": "조사 단계에서 멈춘 기록입니다. 근거·제안 화면은 만들지 않았습니다.",
    "held": "조사 단계에서 보류된 기록입니다. 근거·제안 화면은 만들지 않았습니다.",
}


def build_requests_only(export: dict, export_path: Path, ins: dict, focus: str | None) -> dict:
    """업무 turn 없이 요청 기록만 있는 export(입력 필요·조사 보류 등). 근거·대조·제안 화면은 만들지 않는다."""
    reqs = turnless_requests(export, [])
    rows = []
    for i, r in enumerate(reqs, 1):
        rows.append({
            "n": f"R{i}", "q": r["question"], "model": r["model"],
            "status": {"text": status_text(r["status"]), "tone": STATUS_TONE.get(r["status"], "gray")},
            "why": (f"`{r['code']}` " if r["code"] else "") + (r["reason"] or "사유 미기록"),
            "events": [{"text": f"{e.get('kind', '?')} v{e.get('version', '?')}", "tone": "gray"} for e in r["events"]] or [{"text": "없음", "tone": "gray"}],
            "detail": " / ".join(json.dumps(e.get("input"), ensure_ascii=False)[:300] for e in r["events"]) or "–",
        })
    raw = export_path.read_bytes()
    usage = export.get("usage_summary") or {}
    # export에는 요청 시각이 없고 순서도 시간 순서가 아니다. 상태가 하나로 같을 때만 그 상태로 안내한다.
    kinds = list(dict.fromkeys(r["status"] for r in reqs))
    only_status = kinds[0] if len(kinds) == 1 else None
    reasons = [row["why"] for row in rows if row["why"] != "사유 미기록"]
    blocks = [
        {"type": "lead", "text": "이 export에는 업무 turn이 없습니다. 요청 기록만 있어 근거·대조·제안 화면은 만들지 않았습니다. "
                                 "화면은 **저장된 실행 결과**만 보여주고 모델이나 업무를 다시 실행하지 않습니다."},
        {"type": "callout", "tone": "warning", "text": "turn 없음: 요청은 저장됐지만 업무 결과(후보)가 없습니다. "
                                                     + (f"멈춘 이유: {' / '.join(reasons)}" if reasons else "멈춘 이유가 기록되지 않았습니다.")},
        {"type": "section", "text": f"요청 기록 {len(rows)}건"},
        {"type": "table", "columns": [
            {"key": "n", "label": "요청", "kind": "mono"}, {"key": "model", "label": "모델", "kind": "mono"},
            {"key": "q", "label": "질문", "kind": "wide"}, {"key": "status", "label": "상태", "kind": "pill"},
            {"key": "why", "label": "멈춘 이유", "kind": "wide"}, {"key": "events", "label": "기록", "kind": "chips"},
            {"key": "detail", "label": "기록 내용(앞부분)", "kind": "wide"},
        ], "rows": rows, "source": "requests[].input·response.reason·events · R 번호는 export 순서이며 시간 순서가 아닙니다(요청 시각 미기록)"},
        {"type": "section", "text": "세션 export"},
        {"type": "files", "items": [
            {"label": "파일", "value": export_path.name},
            {"label": "크기", "value": f"{len(raw):,}바이트 ({human_size(len(raw))})", "copy": False},
            {"label": "SHA-256", "value": hashlib.sha256(raw).hexdigest()},
        ]},
        {"type": "metrics", "items": [
            {"label": "기록 호출", "value": usage.get("recorded_calls") or "기록 없음", "note": f"사용량 상태 {usage.get('status', '미기록')}"},
            {"label": "의미 검토", "value": export.get("semantic_status", "미기록"), "note": "acceptance_ready=" + str(export.get("acceptance_ready")).lower()},
        ]},
    ]
    caption = REQUEST_CAPTION.get(only_status) or ("업무 turn 없이 멈춘 요청 기록입니다. 요청마다 멈춘 이유가 다르며, 어느 요청이 "
                                                   "최신인지는 export에 기록되지 않았습니다. 근거·제안 화면은 만들지 않았습니다.")
    pages = [{"id": "overview", "nav": "요청 기록", "icon": "🏠", "title": "요청 기록 (turn 없음)", "title_icon": "📋",
              "caption": {"title": "01 · 입력: 요청은 저장됐지만 업무 turn이 없습니다", "text": caption},
              "blocks": blocks}]
    pages += custom_pages(ins, 2, {})
    ids = [p["id"] for p in pages]
    if focus and focus not in ids:
        warn(f"--focus {focus}는 없는 화면입니다. 첫 화면을 보여줍니다.")
        focus = None
    notice = warning_block()
    if notice:
        pages[0]["blocks"].insert(0, notice)
    return {
        "kind": "lgax-view", "schema": 1,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "focus": focus,
        "app": {"title": "LG AX 상품기획", "subtitle": "하네스 시각자료 뷰어", "icon": "📊"},
        "context": {"meta": ins.get("meta") or "요청 기록 · 저장된 실행 결과", "file": {"name": export_path.name, "size": human_size(len(raw))},
                    "loaded": f"요청 {len(rows)}건 · turn 0개",
                    "status": [{"text": f"결과 없음 · {status_plain(only_status)}" if only_status else turnless_chip(reqs)["text"],
                                "tone": STATUS_TONE.get(only_status, "orange"),
                                "tip": f"turn 없음 · status: {only_status}" if only_status else turnless_chip(reqs)["tip"]},
                               semantic_chip(export)],
                    "footer": [f"🆔 Session: `{str(export.get('session_id', ''))[:16]}…`"]},
        "pages": pages,
        "warnings": list(warnings),
    }


def write_atomic(path: Path, data: str | bytes) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    if isinstance(data, bytes):
        tmp.write_bytes(data)
    else:
        tmp.write_text(data, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def auto_focus(export: dict | None) -> str | None:
    """승인된 유효 완료 결과는 한눈에 보기, 그 밖(turn 없는 최근 요청·무효·거절·보류·취소)은 요청·개요를 먼저 보여준다."""
    if not export or not export.get("turns"):
        return "overview"
    rows = read_turns(export)
    cur = current_row(rows)
    if turnless_requests(export, rows):  # 순서를 모르는 멈춘 요청이 있으면 먼저 보여준다
        return "overview"
    ok = cur["valid"] and cur["status"] == "completed" and bool(cur["result"])
    return "story" if ok else "overview"


def report_charts(c: "Ctx") -> dict | None:
    """보고서로 보기(신진하 보고서 양식)에 덧붙이는 그래프 두 개. 양식이 받는 report_plan 형식으로 쓴다(2026-10-15 사용자 선택).

    - 근거 구성: 결과에 연결한 근거를 종류별로 센다. 근거 대시보드의 '유형별 등록 근거'와 같은 기준(ev_type)이다.
    - 제안과 근거 연결: 제안마다 source_ids 수를 센다. 근거 대시보드의 항목별 연결 근거와 같은 기준이다.
    보고서가 그리는 결과(그 turn의 latest_result)와 같은 결과일 때만 만든다. 무효·취소 turn이나 결과가 없으면 만들지 않는다.
    양식은 title·summary가 비어 있으면 결과로 표지를 만들고, sections만 본문 뒤에 붙인다.
    """
    if c.invalid or c.cur["status"] == "cancelled" or not c.result:
        return None
    sections = []
    by_type: dict[str, int] = {}
    for e in c.evidence:
        by_type[ev_type(e)] = by_type.get(ev_type(e), 0) + 1
    if by_type:
        order = type_order(by_type)
        sections.append({"title": "근거 구성", "blocks": [{
            "type": "chart", "chart_type": "donut", "title": "결과에 연결한 근거의 종류", "labels": order,
            "series": [{"name": "근거 수", "values": [by_type[t] for t in order]}], "unit": "건",
            "source_ids": list(dict.fromkeys(e.get("source_id") for e in c.evidence if e.get("source_id"))),
            "caption": f"결과에 연결한 근거 {len(c.evidence)}건을 종류별로 나눴습니다(화면의 근거 대시보드와 같은 기준). "
                       "고객 수나 시장 비율이 아닙니다.",
        }]})
    concepts = [cl for cl in c.result.get("concepts") or [] if isinstance(cl, dict)]
    if concepts:
        sections.append({"title": "제안과 근거 연결", "blocks": [{
            "type": "chart", "chart_type": "bar", "title": "제안별 연결 근거",
            "labels": [f"제안 {i} ({cl.get('id') or '?'})" for i, cl in enumerate(concepts, 1)],
            "series": [{"name": "연결 근거 수", "values": [len(cl.get("source_ids") or []) for cl in concepts]}], "unit": "건",
            "source_ids": list(dict.fromkeys(s for cl in concepts for s in cl.get("source_ids") or [])),
            "caption": "제안마다 결과에 연결한 근거 수입니다. 같은 근거가 여러 제안에 연결될 수 있고, 연결 수는 효과나 우선순위를 뜻하지 않습니다.",
        }]})
    return {"title": "", "summary": [], "sources": [], "sections": sections} if sections else None


# Installed callers may still pass --mode ops. K is now the only view.
VIEW_MODES = ("ops",)


def report_source(c: Ctx) -> dict | None:
    """Project only the verified current turn into the report vendor's input contract.

    Keep stored result/refs untouched. Full registered bodies and review/research records
    are separate report sections, so quoted refs and chart/keyword denominators stay intact.
    """
    if not c.web or not c.has_result or c.invalid or c.cur["status"] == "cancelled":
        return None
    turn_id = c.cur["turn_id"]
    current = next((h for h in c.export.get("turns", [])
                    if h.get("state", {}).get("turn_id") == turn_id), None)
    if current is None:
        return None
    # Never expose another turn's unchecked latest_result through the report's selector.
    report_export = {**c.export, "turns": [current]}
    plan = report_charts(c) or {"title": "", "summary": [], "sources": [], "sections": []}
    encode = lambda value: json.dumps(value, ensure_ascii=False, indent=2)
    sections = plan["sections"]
    sections.append({"title": "보고서 범위와 검증 조건", "blocks": [{
        "type": "paragraph", "text": "현재 저장 검토와 전체 버전 지문이 일치한 결과만 표시합니다. "
        "기본 근거와 키워드는 결과에 인용한 본문 범위이고, 아래 등록 원문 전체와 구분합니다. "
        "등록 건수는 고객 수나 대표성이 아니며, source_fact·검토 신고는 모델의 분류로 원문 의미 인증이 아닙니다. "
        "검증 계획은 실측 전 조건이며 다음 원문 필드를 생략하지 않습니다."
    }, {"type": "table", "columns": ["제안 ID", "검증 계획 원문"],
        "rows": [[cl.get("id", ""), encode(cl.get("validation_plan"))]
                 for cl in c.result.get("concepts", [])]}]})
    sources = [s for s in c.web.get("sources", []) if isinstance(s, dict)]
    source_blocks = [{"type": "table", "columns": ["전달·검토 범위", "원문 기록"],
                      "rows": [["coverage", encode(c.web.get("coverage", {}))]]}]
    for source in sources:
        sid = source.get("source_id", "")
        source_blocks.append({"type": "table", "title": sid,
                              "columns": ["출처 메타데이터", "기록"], "rows": [
                                  ["결과 인용 여부", "결과에 인용" if sid in c.ev else "인용 안 함"],
                                  ["원문 메타데이터", encode({k: v for k, v in source.items() if k != "text"})]]})
        # No excerpt, trimming or model summary substitutes for the registered body.
        if source.get("text"):
            source_blocks.append({"type": "paragraph", "title": sid + " · 등록 원문 전체",
                                  "text": source["text"]})
    sections.append({"title": f"선택 등록 원문 전체 {len(sources)}건", "blocks": source_blocks})
    sections.append({"title": "현재 검토·조사 이력과 버전", "blocks": [{
        "type": "table", "columns": ["구분", "저장 기록 원문"], "rows": [
            ["binding", encode(c.web.get("binding", {}))],
            ["저장 검토", encode(c.validation)],
            ["근거 검토·전달 이력", encode(c.web.get("evidence_history", {}))],
            ["조사 상태", encode(c.web.get("investigation", {}))],
            ["조사 사건", encode(c.web.get("investigation_events", []))],
            ["현재 turn 이력", encode({k: v for k, v in current.items() if k != "state"})]]}]})
    return {"export": report_export, "turn_id": turn_id, "plan": plan}


def generate(export_path: Path | None, insights_path: Path | None = None, focus: str | None = None,
             standalone: Path | None = None, out_dir: Path | None = None, insights_dir: Path | None = None,
             index_sha256: str | None = None, mode: str | None = None,
             web_result_path: Path | None = None, web_result_sha256: str | None = None) -> dict:
    """view를 out_dir(기본: 이 폴더)의 view-data.js로 쓰고 요약을 돌려준다. focus="auto"는 상태로 고른다.

    - insights_path가 없고 insights_dir가 있으면 그 폴더의 insights-*.json에서 session_id·turn_id로 고른다.
    - out_dir가 이 폴더가 아니면 index.html도 그 폴더에 복사한다. index_sha256을 주면 복사 전에 지문을 확인한다.
    """
    if mode is not None and mode not in VIEW_MODES:
        raise ValueError("K 업무형(ops)만 지원합니다.")
    warnings.clear()
    out_dir = Path(out_dir) if out_dir else HERE
    export = load_json(export_path) if export_path else None
    if web_result_path and export is None:
        raise SystemExit("--web-result는 현재 저장 검토와 전체 binding을 확인할 --export와 함께 필요합니다.")
    web_file = {}
    web_result, delivery_state = load_web_result(export, Path(export_path), web_result_path, web_result_sha256, web_file) if export and export.get("turns") else ({}, "no_current_turn")
    insights_file = None
    if insights_path:
        insights = load_json(insights_path)
        insights_file = Path(insights_path).name
        shape = insights_shape_errors(insights)
        if shape:
            warn(f"insights {insights_file}의 형식이 README와 달라 쓰지 않았습니다: {', '.join(shape)}")
            insights, state = {}, "invalid"
        else:
            state = classify_insights(export, insights)
        if export is not None and state != "matched":
            warn(f"insights {insights_file}의 {'session_id' if state == 'mismatch' else 'turn_id'}가 이 export와 달라 쓰지 않았습니다.")
            insights = {}
    elif insights_dir and export is not None:
        path, insights, state = pick_insights(Path(insights_dir), export)
        insights_file = path.name if path else None
    else:
        insights, state = {}, "missing"
    if focus == "auto":
        focus = auto_focus(export) if web_result else "overview"
    ctx = None
    if export is not None and not export.get("turns"):
        view = build_requests_only(export, export_path, insights, focus)
    else:
        ctx = Ctx(export, export_path, insights, state, insights_file, web_result, delivery_state, web_file) if export else None
        if ctx:
            state, insights_file = ctx.insights_state, ctx.insights_file
        view = build(ctx, ctx.ins if ctx else insights, focus)
        report = report_source(ctx) if ctx else None
        if report is not None:
            view["report"] = report
    payload = json.dumps(view, ensure_ascii=False, indent=1)

    html = (HERE / "index.html").read_bytes()
    if index_sha256 and hashlib.sha256(html).hexdigest() != index_sha256:
        raise IntegrityError("index.html이 설치 때와 다릅니다. viewer.py install로 다시 설치하세요.")
    out_dir.mkdir(parents=True, exist_ok=True)
    page = HERE / "index.html"
    if out_dir.resolve() != HERE:
        target = out_dir / "index.html"
        # 출력 폴더의 index.html은 매번 검증한 원본과 같게 맞춘다(다른 프로그램이 바꿔 놓았어도 되돌린다).
        if not target.is_file() or target.read_bytes() != html:
            write_atomic(target, html)
        page = target
    data_path = out_dir / "view-data.js"
    write_atomic(data_path, "/* build_view.py가 만든 파일입니다. 직접 고치지 말고 다시 생성하세요. */\nwindow.LGAX_VIEW = " + payload + ";\n")
    outputs = {"view_data": data_path.as_posix(), "index": page.as_posix()}

    if standalone:
        text = html.decode("utf-8")
        tag = '<script src="view-data.js" charset="utf-8"></script>'
        if tag not in text:
            raise SystemExit("index.html에서 view-data.js 태그를 찾지 못했습니다.")
        # 단일 파일은 옮겨서 공유하므로 이 폴더 기준 상대 경로 링크(export 열기)는 뺀다.
        shared = json.loads(payload)
        for pg in shared["pages"]:
            for block in pg["blocks"]:
                if block.get("type") == "files":
                    block.pop("href", None)
                    block.pop("href_label", None)
        shared_payload = json.dumps(shared, ensure_ascii=False, indent=1)
        inline = ("<script>window.LGAX_VIEW_INLINE = true; "
                  + "window.LGAX_VIEW = " + shared_payload.replace("</", "<\\/") + ";</script>")
        write_atomic(Path(standalone), text.replace(tag, inline))
        outputs["standalone"] = Path(standalone).as_posix()
    web = ctx.web_file.get("name") if ctx else None
    return {"ok": True, "pages": len(view["pages"]), "focus": view["focus"], "insights": state, "insights_file": insights_file,
            "outputs": outputs, "warnings": list(warnings), "web_delivery": delivery_state, "web_result": web}


def main() -> int:
    ap = argparse.ArgumentParser(description="하네스 세션 export → 시각자료 뷰어 데이터")
    ap.add_argument("--export", type=Path, help="export_session이 만든 세션 JSON (없으면 insights의 pages만 그림)")
    ap.add_argument("--web-result", type=Path, help="현재 export와 정확 지문이 일치하는 불변 웹 JSON")
    ap.add_argument("--web-result-sha256", help="명시한 웹 JSON 바이트의 SHA-256")
    ap.add_argument("--insights", type=Path, help="모델이 쓴 해석·화면 JSON")
    ap.add_argument("--focus", help="브라우저가 보여줄 화면 id: " + ", ".join(BUILDERS) + ", insights pages의 id, 또는 auto(상태로 선택)")
    ap.add_argument("--standalone", type=Path, help="데이터를 넣은 단일 HTML 보고서 경로")
    ap.add_argument("--mode", choices=VIEW_MODES, help="설치된 호출과의 호환 옵션: K 업무형 ops")
    ap.add_argument("--out-dir", type=Path, help="view-data.js·index.html을 둘 폴더 (기본: 이 폴더)")
    ap.add_argument("--open", action="store_true", help="뷰어를 기본 브라우저로 연다")
    args = ap.parse_args()
    if not args.export and not args.insights and not args.web_result:
        ap.error("--export, --web-result, --insights 중 하나는 필요합니다.")
    if args.mode and not args.standalone:
        ap.error("--mode는 --standalone과 함께 씁니다(K 업무형만 지원합니다).")
    summary = generate(args.export, args.insights, args.focus, args.standalone, args.out_dir, mode=args.mode,
                       web_result_path=args.web_result, web_result_sha256=args.web_result_sha256)
    if args.open:
        webbrowser.open(Path(summary["outputs"]["index"]).resolve().as_uri())
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
