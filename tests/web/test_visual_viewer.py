"""Visual viewer prototype: builder, CLI hook and installer on synthetic v0.7.0 exports.

Every export here is generated at test time through the real product-tools save/export path,
with text marked "[합성 시험 자료]". They are code fixtures, not AI or customer results.
No test opens a browser, runs a business question, starts Codex/Claude or calls a model.
"""
import contextlib
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
VIEWER = ROOT / "web" / "prototypes" / "visual-viewer"
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.conversation import Conversation  # noqa: E402
from product_tools.dataset import Dataset  # noqa: E402
from product_tools.state import StateStore  # noqa: E402

SYNTH = "[합성 시험 자료]"
FAMILIES = (("refrigerator", "냉장고", "B502S33", "REVIEW-B502S33-01", "SPEC-B502S33-02"),
            ("microwave", "전자레인지", "MWJ25E", "REVIEW-MWJ25E-01", "SPEC-MWJ25E-02"),
            ("dishwasher", "식기세척기", "DUBJ2EA", "REVIEW-DUBJ2EA-01", "SPEC-DUBJ2EA-03"))
M, RID, FID = "MWJ25E", "REVIEW-MWJ25E-01", "SPEC-MWJ25E-02"
EXPORTS: dict[str, Path] = {}
_TMP = None
_ENV = {}


def load(name):
    spec = importlib.util.spec_from_file_location(name, VIEWER / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_view = load("build_view")
hook = load("hook")
viewer = load("viewer")


# ---------------------------------------------------------------- synthetic exports through real product-tools

class Gen:
    def __init__(self, work: Path, data: str):
        for name in ("skills/manifest.json", "agents/product-planning.md"):
            p = work / name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, p)
        self.work = work
        self.store = StateStore(work / "runtime-data/product.sqlite", Dataset(ROOT / data))
        self.conv = Conversation(self.store, work)

    def keep(self, name: str, rel: str):
        EXPORTS[name] = self.work / rel

    def author(self, value, scope, rid, fid, unsupported=None, notes=None):
        r = value["result"]
        r.update(status="completed",
                 pains=[{"id": "p1", "text": f"{SYNTH} 현재 불편", "source_ids": [rid]}],
                 existing_features=[{"id": "f1", "text": f"{SYNTH} 기존 기능", "source_ids": [fid]}],
                 remaining_pains=[{"id": "r1", "text": f"{SYNTH} 남은 불편", "source_ids": [rid, fid]}],
                 concepts=[{"id": "c1", "text": f"{SYNTH} 제안", "source_ids": [rid, fid], "requirements": [f"{SYNTH} 조건"],
                            "requires_hardware": False, "assumptions": [f"{SYNTH} 효과 미측정"],
                            "implementation_steps": [f"{SYNTH} 1단계 시제품", f"{SYNTH} 2단계 과업 시험"],
                            "validation_plan": {"metric": f"{SYNTH} 과업 시간", "baseline": "현행", "method": "동일 과업 비교",
                                                "success_criterion": "시험 전 합의", "business_value": "가설", "status": "planned_not_measured"}}],
                 assumptions=[f"{SYNTH} 코드 시험용"],
                 evidence_refs=self.store.tools.select_evidence(scope, [rid, fid])["evidence_refs"])
        if notes:
            r["decision_notes"] = notes
        checks = [{"claim_id": c["id"], "source_ids": c["source_ids"], "support_status": "supported", "scope_relation": "current_model",
                   "rationale": "code fixture"} for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in r[key]]
        if unsupported:
            checks[0]["support_status"] = unsupported
        value["assessment"] = {
            "claim_checks": checks,
            "feature_matches": [{"remaining_pain_id": "r1", "pain_id": "p1", "feature_source_ids": [fid], "resolution": "unresolved", "rationale": "fixture"}],
            "concept_links": [{"concept_id": "c1", "remaining_pain_ids": ["r1"], "duplicates_existing": False, "geometry_required": False,
                               "geometry_known": False, "geometry_source_ids": [], "rationale": "fixture"}]}
        return value

    def bundle(self, question, **extra):
        return self.conv.open_request_bundle({"question": f"{SYNTH} {question}", "user_submitted": True, **extra})

    def completed(self, name, model, rid, fid, **extra):
        b = self.bundle(f"{model} 불편 개선 시험", model_id=model, **extra)
        v = self.author(b["candidate_template"], b["turn"]["input"]["model_scope"][0], rid, fid,
                        notes=[{"text": f"{SYNTH} 판단 메모", "source_ids": [rid], "basis": "ai_interpretation"}])
        saved = self.conv.save_and_export(v)
        assert saved["save"]["accepted"], saved["save"]
        self.keep(name, saved["export"]["path"])
        return v

    def close(self):
        self.store.close()


def make_exports(base: Path):
    g = Gen(base / "product", "data/business/lg-kitchen-v4")
    try:
        for family, _, model, rid, fid in FAMILIES:
            g.completed(family, model, rid, fid)
        # 보류 결과 + 판단 메모(원문 사실·근거 없는 미확인)
        b = g.bundle("보류 시험", model_id=M)
        v = b["candidate_template"]
        v["result"].update(status="held", validation_findings=[f"{SYNTH} 내부 치수 근거 없음"],
                           evidence_refs=g.store.tools.select_evidence(b["turn"]["input"]["model_scope"][0], [RID])["evidence_refs"],
                           decision_notes=[{"text": f"{SYNTH} 원문 범위", "source_ids": [RID], "basis": "source_fact"},
                                           {"text": f"{SYNTH} 근거 없는 추정", "source_ids": [], "basis": "unverified"}])
        saved = g.conv.save_and_export(v)
        assert saved["save"]["accepted"]
        g.keep("held", saved["export"]["path"])
        # 거절 1회(수정 필요) → 3회(보류)
        b = g.bundle("거절 시험", model_id=M)
        scope = b["turn"]["input"]["model_scope"][0]
        template = b["candidate_template"]
        v = g.author(template, scope, RID, FID, unsupported="unsupported")
        saved = g.conv.save_and_export(v)
        assert not saved["save"]["accepted"] and saved["save"]["turn"]["status"] == "needs_revision"
        g.keep("reject1", saved["export"]["path"])
        for k in (1, 2):
            v = g.author({"session_id": v["session_id"], "turn_id": v["turn_id"], "result_key": f"candidate-{k}", "expected_result_version": k,
                          "result": dict(template["result"], revisions=k), "assessment": {}}, scope, RID, FID, unsupported="uncertain")
            saved = g.conv.save_and_export(v)
        assert saved["save"]["turn"]["status"] == "held"
        g.keep("reject3", saved["export"]["path"])
        # 완료 뒤 모르는 모델 후속 → 조사 보류(turn 없음)
        v = g.completed("followup_base", M, RID, FID)
        r = g.conv.open_request_bundle({"question": f"{SYNTH} 후속 ZZZ123", "session_id": v["session_id"], "prior_turn_id": v["turn_id"],
                                        "model_id": "ZZZ123", "user_submitted": True})
        assert r["status"] == "research_required"
        g.conv.record_request_research({"session_id": v["session_id"], "request_key": r["request_key"], "event_key": "e1",
                                        "expected_request_version": r["request_version"], "status": "held",
                                        "reason": f"{SYNTH} HTTP403 보류 사유", "observation_refs": []})
        g.keep("followup_held", g.conv.export_session({"session_id": v["session_id"]})["path"])
        # 사용량: 출력 토큰 미측정 → 일부 측정
        b = g.bundle("사용량 시험", model_id=M)
        t = b["turn"]
        g.store.record_usage(t["session_id"], t["turn_id"], {"call_id": "c1", "status": "succeeded", "input_tokens": 1000, "output_tokens": None,
                                                             "cache_tokens": None, "reasoning_tokens": None, "cost_usd": None})
        saved = g.conv.save_and_export(g.author(b["candidate_template"], t["input"]["model_scope"][0], RID, FID))
        g.keep("usage_out_null", saved["export"]["path"])
        g.store.record_usage(t["session_id"], t["turn_id"], {"call_id": "c2", "status": "succeeded", "input_tokens": None, "output_tokens": 50,
                                                             "cache_tokens": None, "reasoning_tokens": None, "cost_usd": "0.01"})
        g.keep("usage_partial", g.conv.export_session({"session_id": t["session_id"]})["path"])
        # 제품군 카탈로그(냉장고 3개 모델 중 T876MQQ012 근거)
        b = g.bundle("냉장고 제품군 시험", product_family="refrigerator")
        scope = [s for s in b["turn"]["input"]["model_scope"] if s["model_id"] == "T876MQQ012"][0]
        saved = g.conv.save_and_export(g.author(b["candidate_template"], scope, "REVIEW-T876MQQ012-01", "SPEC-T876MQQ012-02"))
        assert saved["save"]["accepted"]
        g.keep("family_catalog", saved["export"]["path"])
        # 여러 turn: 제외 조건 → 셋째 취소(후보 없음) → 넷째 진행 중
        v1 = g.completed("e_first", M, RID, FID)
        b2 = g.conv.open_request_bundle({"question": f"{SYNTH} E 둘째", "session_id": v1["session_id"], "prior_turn_id": v1["turn_id"], "user_submitted": True,
                                         "constraints": {"max_concepts": 1, "hardware_allowed": False, "exclude_pains": [f"{SYNTH} 소음제외"]}})
        v2 = g.author(b2["candidate_template"], b2["turn"]["input"]["model_scope"][0], RID, FID)
        saved = g.conv.save_and_export(v2)
        g.keep("two_turns", saved["export"]["path"])
        b3 = g.conv.open_request_bundle({"question": f"{SYNTH} E 셋째 취소", "session_id": v1["session_id"], "prior_turn_id": v2["turn_id"], "user_submitted": True})
        g.store.cancel_turn(v1["session_id"], b3["turn"]["turn_id"], "cx", f"{SYNTH} 셋째 취소 사유", 0, True)
        g.keep("third_cancelled", g.conv.export_session({"session_id": v1["session_id"]})["path"])
        g.conv.open_request_bundle({"question": f"{SYNTH} E 넷째 진행 중", "session_id": v1["session_id"], "prior_turn_id": v2["turn_id"], "user_submitted": True})
        g.keep("fourth_pending", g.conv.export_session({"session_id": v1["session_id"]})["path"])
        # 거절 뒤 취소
        b = g.bundle("거절 뒤 취소", model_id=M)
        v = g.author(b["candidate_template"], b["turn"]["input"]["model_scope"][0], RID, FID, unsupported="unsupported")
        g.conv.save_and_export(v)
        g.store.cancel_turn(v["session_id"], v["turn_id"], "cf", f"{SYNTH} 사용자 취소 사유", 1, True)
        g.keep("cancel_after_reject", g.conv.export_session({"session_id": v["session_id"]})["path"])
        # 제품 미지정 → 입력 필요(turn 없음)
        r = g.bundle("제품 미지정")
        assert r["status"] == "needs_input"
        g.keep("needs_input", g.conv.export_session({"session_id": r["session_id"]})["path"])
        # 같은 세션에 입력 필요 + 모르는 모델 조사 보류(turn 없는 요청 2건, 순서 모름)
        r2 = g.conv.open_request_bundle({"question": f"{SYNTH} 둘째 요청 ZZZ666", "session_id": r["session_id"], "model_id": "ZZZ666", "user_submitted": True})
        g.conv.record_request_research({"session_id": r["session_id"], "request_key": r2["request_key"], "event_key": "e1",
                                        "expected_request_version": r2["request_version"], "status": "held",
                                        "reason": f"{SYNTH} 조사 보류", "observation_refs": []})
        g.keep("requests_mixed", g.conv.export_session({"session_id": r["session_id"]})["path"])
        # T1·T2 완료 뒤 prior_turn_id=T1인 후속이 보류(마지막 turn 뒤인지 export로는 알 수 없음), prior 없는 후속
        v1 = g.completed("b2_first", M, RID, FID)
        b2 = g.conv.open_request_bundle({"question": f"{SYNTH} B2 둘째", "session_id": v1["session_id"], "prior_turn_id": v1["turn_id"], "user_submitted": True})
        assert g.conv.save_and_export(g.author(b2["candidate_template"], b2["turn"]["input"]["model_scope"][0], RID, FID))["save"]["accepted"]
        r = g.conv.open_request_bundle({"question": f"{SYNTH} B2 후속 ZZZ777", "session_id": v1["session_id"], "prior_turn_id": v1["turn_id"],
                                        "model_id": "ZZZ777", "user_submitted": True})
        g.conv.record_request_research({"session_id": v1["session_id"], "request_key": r["request_key"], "event_key": "e1",
                                        "expected_request_version": r["request_version"], "status": "held",
                                        "reason": f"{SYNTH} ZZZ777 보류", "observation_refs": []})
        g.keep("followup_prior_t1", g.conv.export_session({"session_id": v1["session_id"]})["path"])
        v1 = g.completed("b3_first", M, RID, FID)
        r = g.conv.open_request_bundle({"question": f"{SYNTH} B3 후속 ZZZ888", "session_id": v1["session_id"], "model_id": "ZZZ888", "user_submitted": True})
        assert r["status"] == "research_required"
        g.keep("followup_no_prior", g.conv.export_session({"session_id": v1["session_id"]})["path"])
        # v1 승인 → v2 거절(같은 turn): 승인 결과가 없는 상태
        b = g.bundle("승인 뒤 거절", model_id=M)
        template = b["candidate_template"]
        v = g.author(template, b["turn"]["input"]["model_scope"][0], RID, FID)
        assert g.conv.save_and_export(v)["save"]["accepted"]
        v2 = g.author({"session_id": v["session_id"], "turn_id": v["turn_id"], "result_key": "candidate-1", "expected_result_version": 1,
                       "result": dict(template["result"], revisions=1), "assessment": {}}, b["turn"]["input"]["model_scope"][0], RID, FID, unsupported="unsupported")
        saved = g.conv.save_and_export(v2)
        assert not saved["save"]["accepted"]
        g.keep("acc_then_rej", saved["export"]["path"])
        # 승인된 보류 결과 → 사용자 취소
        b = g.bundle("보류 뒤 취소", model_id=M)
        v = b["candidate_template"]
        v["result"].update(status="held", validation_findings=[f"{SYNTH} 치수 확인 필요"])
        assert g.conv.save_and_export(v)["save"]["accepted"]
        g.store.cancel_turn(v["session_id"], v["turn_id"], "hc", f"{SYNTH} 보류 뒤 취소 사유", 1, True)
        g.keep("held_then_cancel", g.conv.export_session({"session_id": v["session_id"]})["path"])
        # 모델이 쓴 cancelled 결과(취소 기록 없이 결과에 사유)
        b = g.bundle("모델 취소 결과", model_id=M)
        v = b["candidate_template"]
        v["result"].update(status="cancelled", validation_findings=[f"{SYNTH} 모델이 쓴 취소 사유"])
        saved = g.conv.save_and_export(v)
        assert saved["save"]["accepted"]
        g.keep("result_cancelled", saved["export"]["path"])
    finally:
        g.close()
    s = Gen(base / "synthetic", "data/synthetic/kitchen-v1")
    try:
        b = s.bundle("합성 카탈로그 시험", model_id="AX-R302")
        saved = s.conv.save_and_export(s.author(b["candidate_template"], b["turn"]["input"]["model_scope"][0],
                                                "REV-AX-R302-1.0-01", "DOC-AX-R302-1.0-01"))
        assert saved["save"]["accepted"]
        s.keep("synthetic_catalog", saved["export"]["path"])
        b = s.bundle("합성 카탈로그 거절 시험", model_id="AX-R302")
        saved = s.conv.save_and_export(s.author(b["candidate_template"], b["turn"]["input"]["model_scope"][0],
                                                "REV-AX-R302-1.0-01", "DOC-AX-R302-1.0-01", unsupported="unsupported"))
        assert not saved["save"]["accepted"]
        s.keep("synthetic_rejected", saved["export"]["path"])
    finally:
        s.close()


def setUpModule():
    global _TMP
    _TMP = tempfile.TemporaryDirectory(prefix="lgax-viewer-fixtures-")
    codex_home = Path(_TMP.name) / "codexhome"
    codex_home.mkdir()
    for key, value in (("LGAX_VIEWER_NO_OPEN", "1"), ("CODEX_HOME", str(codex_home))):
        _ENV[key] = os.environ.get(key)
        os.environ[key] = value
    make_exports(Path(_TMP.name))


def tearDownModule():
    for key, value in _ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    _TMP.cleanup()


# ---------------------------------------------------------------- helpers

def read_view(out_dir: Path) -> dict:
    text = (out_dir / "view-data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("window.LGAX_VIEW = ") + len("window.LGAX_VIEW = "):].rstrip().rstrip(";"))


def page(view, pid):
    return next(p for p in view["pages"] if p["id"] == pid)


def blob(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def blob_blocks(pg) -> list[dict]:
    """화면의 블록을 row·expander 안까지 펼친다."""
    out, todo = [], list(pg["blocks"])
    while todo:
        b = todo.pop(0)
        out.append(b)
        todo[:0] = [x for col in b.get("cols") or [] for x in col.get("blocks") or []] + list(b.get("blocks") or [])
    return out


def export_of(key: str) -> dict:
    return json.loads(EXPORTS[key].read_text(encoding="utf-8"))


def current_turn(key: str) -> str:
    return build_view.current_row(build_view.read_turns(export_of(key)))["turn_id"]


def rename_source(value, old: str, new: str):
    if isinstance(value, dict):
        return {k: rename_source(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [rename_source(v, old, new) for v in value]
    return new if value == old else value


def git_bash() -> str | None:
    """Git Bash (WSL의 System32 bash가 아님). PowerShell·cmd에서 돌려도 찾는다."""
    if os.name != "nt":
        return shutil.which("bash")
    candidates = []
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parents[1]
        candidates += [root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"]
    candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe")
    for path in candidates:
        if path.is_file():
            return str(path)
    found = shutil.which("bash")
    return found if found and "system32" not in found.lower() else None


class Harness:
    """Minimal harness folder: what viewer.py checks for, plus runtime-data/exports."""

    def __init__(self, root: Path):
        self.root = root
        (root / "product-tools").mkdir(parents=True)
        (root / "AGENTS.md").write_text("# 시험용 하네스\n", encoding="utf-8")
        self.exports = root / "runtime-data" / "exports"
        self.exports.mkdir(parents=True)
        self.out = root / "runtime-data" / "visual-viewer"

    def add(self, key: str, name: str | None = None, data: dict | None = None) -> Path:
        dest = self.exports / (name or EXPORTS[key].name)
        if data is None:
            shutil.copyfile(EXPORTS[key], dest)
        else:
            dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        web = self.root / "runtime-data/web-deliveries"
        web.mkdir(exist_ok=True)
        for source in (EXPORTS[key].parent.parent / "web-deliveries").glob("web-*.json"):
            shutil.copyfile(source, web / source.name)
        stamp = time.time() + len(list(self.exports.iterdir()))  # strictly newer than earlier copies
        os.utime(dest, (stamp, stamp))
        return dest

    def state(self) -> dict:
        return json.loads((self.out / ".hook-state.json").read_text(encoding="utf-8"))

    def insights(self, name: str, value: dict, bom: bool = False) -> Path:
        self.out.mkdir(parents=True, exist_ok=True)
        path = self.out / name
        # Explicit turn fixtures use the same full binding as their saved export.
        # Unbound fixture tests deliberately omit turn_id and remain unverified.
        if value.get("turn_id") and "binding" not in value:
            for export in self.exports.glob("*.json"):
                data = json.loads(export.read_text(encoding="utf-8"))
                current = (data.get("turns") or [{}])[-1]
                if data.get("session_id") == value.get("session_id") and (current.get("state") or {}).get("turn_id") == value["turn_id"]:
                    value = {**value, "binding": current.get("web_binding")}
                    break
        path.write_bytes(json.dumps(value, ensure_ascii=False).encode("utf-8-sig" if bom else "utf-8"))
        return path


def run_viewer(*argv) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = viewer.main(list(argv))
    return code, out.getvalue() + err.getvalue()


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lgax-viewer-test-")
        self.h = Harness(Path(self.tmp.name) / "harness")
        self.generators = []

    def tearDown(self):
        for generator in self.generators:
            generator.close()
        self.tmp.cleanup()

    def build(self, key=None, path=None, insights_path=None):
        export = path or self.h.add(key)
        summary = build_view.generate(export, insights_path, "auto", out_dir=self.h.out,
                                      insights_dir=None if insights_path else self.h.out)
        return summary, read_view(self.h.out)


# ---------------------------------------------------------------- builder

class BuildViewTests(TempCase):

    def test_duplicate_null_false_true_transitions_use_real_reviewed_web_snapshots(self):
        g = Gen(Path(self.tmp.name) / "duplicate-states", "data/business/lg-kitchen-v4")
        self.generators.append(g)
        bundle = g.bundle("중복 판단 상태 코드 시험", model_id=M)
        value = g.author(bundle["candidate_template"], bundle["turn"]["input"]["model_scope"][0], RID, FID)
        value["result"].update(status="held", validation_findings=[f"{SYNTH} 판단 상태 보류 시험"])
        for version, (state, label, tone) in enumerate(((None, "미확인", "orange"), (False, "확정 비중복", "green"), (True, "확정 중복", "red"))):
            with self.subTest(state=state):
                value["expected_result_version"] = version
                value["result_key"] = f"duplicate-state-{version}"
                value["result"]["revisions"] = version
                value["assessment"]["concept_links"][0]["duplicates_existing"] = state
                saved = g.conv.save_and_export(value)
                self.assertTrue(saved["save"]["accepted"], saved)
                self.assertTrue(saved["web_ready"], saved)
                summary = build_view.generate(g.work / saved["export"]["path"], out_dir=self.h.out)
                self.assertEqual(summary["web_delivery"], "verified_binding")
                view = read_view(self.h.out)
                chip = {"text": "기존 기능 중복: " + label, "tone": tone}
                solutions = next(b for b in blob_blocks(page(view, "story")) if b["type"] == "solutions")
                self.assertIn(chip, solutions["items"][0]["chips"])
                concept_review = next(b for b in page(view, "concepts")["blocks"] if b.get("title") == "검토 기록")
                self.assertEqual(concept_review["items"][0], chip)
                aggregate = next(b for b in blob_blocks(page(view, "dashboard")) if b.get("source") == "검토 기록 concept_links")
                text = blob(aggregate)
                self.assertIn(f"확정 중복 제안 {int(state is True)}개", text)
                self.assertIn(f"확정 비중복 제안 {int(state is False)}개", text)
                self.assertIn(f"중복 여부 미확인 제안 {int(state is None)}개", text)
                stored = json.loads((g.work / saved["export"]["path"]).read_bytes())
                self.assertIs(stored["turns"][-1]["candidates"][-1]["validation"]["assessment"]["concept_links"][0]["duplicates_existing"], state)
                if state is None:
                    self.assertNotIn("겹치지 않음", blob(page(view, "story")))
                    self.assertNotIn("확정 비중복", blob(solutions))

    def test_two_unknown_concepts_are_not_reported_as_confirmed_nonduplicates(self):
        g = Gen(Path(self.tmp.name) / "two-unknown", "data/business/lg-kitchen-v4")
        self.generators.append(g)
        bundle = g.bundle("두 제안 중복 미확인 코드 시험", model_id=M)
        value = g.author(bundle["candidate_template"], bundle["turn"]["input"]["model_scope"][0], RID, FID)
        value["result"].update(status="held", validation_findings=[f"{SYNTH} 중복 미확인 보류"])
        concept = json.loads(json.dumps(value["result"]["concepts"][0]))
        concept["id"] = "c2"
        value["result"]["concepts"].append(concept)
        check = json.loads(json.dumps(value["assessment"]["claim_checks"][-1]))
        check["claim_id"] = "c2"
        value["assessment"]["claim_checks"].append(check)
        link = json.loads(json.dumps(value["assessment"]["concept_links"][0]))
        link["concept_id"] = "c2"
        value["assessment"]["concept_links"].append(link)
        for link in value["assessment"]["concept_links"]:
            link["duplicates_existing"] = None
        saved = g.conv.save_and_export(value)
        self.assertTrue(saved["web_ready"], saved)
        build_view.generate(g.work / saved["export"]["path"], out_dir=self.h.out)
        view = read_view(self.h.out)
        aggregate = next(b for b in blob_blocks(page(view, "dashboard")) if b.get("source") == "검토 기록 concept_links")
        self.assertIn({"text": "확정 중복 제안 0개", "tone": "gray"}, aggregate["items"])
        self.assertIn({"text": "확정 비중복 제안 0개", "tone": "gray"}, aggregate["items"])
        self.assertIn({"text": "중복 여부 미확인 제안 2개", "tone": "orange"}, aggregate["items"])
        solutions = next(b for b in blob_blocks(page(view, "story")) if b["type"] == "solutions")
        self.assertEqual(sum({"text": "기존 기능 중복: 미확인", "tone": "orange"} in c["chips"] for c in solutions["items"]), 2)

    def test_default_constraints_are_attributed_to_saved_execution_input(self):
        _, view = self.build("microwave")
        original = export_of("microwave")["turns"][-1]["state"]["input"]
        self.assertEqual(original["constraints"]["hardware_allowed"], False)
        self.assertEqual(original["constraints"]["max_concepts"], 3)
        self.assertNotIn("하드웨어", original["question"])
        overview = page(view, "overview")
        metrics = next(b for b in overview["blocks"] if b["type"] == "metrics")["items"]
        for item in metrics:
            if item["label"] in ("제안 상한", "하드웨어 추가"):
                self.assertEqual(item["note"], "저장된 실행 제약 · 기본값·후속 설정 포함")
        self.assertIn("요청과 저장된 실행 제약", blob(overview))
        self.assertNotIn("사용자 조건", blob(overview))
        solution = next(b for b in page(view, "story")["blocks"] if b.get("key") == "solution")
        self.assertTrue(solution["text"].startswith("저장된 실행 제약:"))
        self.assertIn("요청 원문에 명시된 조건으로 추정하지 않습니다", solution["text"])
    def test_three_families_with_steps_plan_and_decision_notes(self):
        for family, label, model, rid, _ in FAMILIES:
            with self.subTest(family=family):
                summary, view = self.build(family)
                self.assertEqual((summary["warnings"], summary["focus"]), ([], "story"))
                self.assertTrue((self.h.out / "index.html").is_file())
                self.assertEqual([p["id"] for p in view["pages"]],
                                 ["story", "overview", "dashboard", "screening", "compare", "concepts", "history", "evidence", "export"])
                self.assertIn(label, page(view, "overview")["title"])
                self.assertIn(label, view["context"]["meta"])
                concepts = blob(page(view, "concepts"))
                self.assertIn("구현 단계 2", concepts)
                self.assertIn("검증 계획 · 실측 전", concepts)
                overview = blob(page(view, "overview"))
                self.assertIn("판단 메모 1개", overview)
                self.assertIn("AI 해석", overview)
                self.assertIn('"D1"', blob(page(view, "evidence")))
                self.assertIn("decision note support and attribution", blob(page(view, "export")))
                self.assertIn("✓ 저장 승인(계약 검사)", blob(page(view, "export")))

    def test_held_result_shows_decision_notes_and_overview_focus(self):
        summary, view = self.build("held")
        self.assertEqual(summary["focus"], "overview")
        overview = blob(page(view, "overview"))
        self.assertIn("보류(held)", overview)
        for text in ("판단 메모 2개", "원문 사실", "미확인", "근거 없음", f"{SYNTH} 근거 없는 추정", f"{SYNTH} 내부 치수 근거 없음"):
            self.assertIn(text, overview)

    def test_rejected_candidate_is_never_the_current_result(self):  # v07-format-01
        summary, view = self.build("reject1")
        self.assertEqual(summary["focus"], "overview")
        status = [c["text"] for c in view["context"]["status"]]
        self.assertIn("수정 필요", status)
        self.assertIn("status: needs_revision", [c.get("tip") for c in view["context"]["status"]])
        self.assertIn("승인된 결과 없음", status)
        self.assertIn("review_not_finalizable", blob(page(view, "overview")))
        self.assertIn("unsupported_or_uncertain:p1", blob(page(view, "overview")))
        for pid in ("dashboard", "concepts", "compare", "evidence"):
            self.assertIn("비워 두었습니다", page(view, pid)["blocks"][0]["text"])
        self.assertNotIn("c1 · 제안", blob(view))
        history = blob(page(view, "history"))
        self.assertIn("거절 · review_not_finalizable", history)
        self.assertIn("거절 후보(현재 결과 아님)", history)
        export = blob(page(view, "export"))
        self.assertIn("✗ 저장 승인(계약 검사)", export)
        self.assertNotIn("✓ 저장 승인", export)
        _, view = self.build("reject3")
        overview = blob(page(view, "overview"))
        self.assertIn("보류(held)", overview)
        self.assertIn("review_not_finalizable", overview)
        self.assertNotIn("결과에 사유가 기록되지 않았습니다", overview)

    def test_turnless_followups_are_shown_and_order_is_not_invented(self):  # v07-format-02, view-new-01, view-new-02
        summary, view = self.build("followup_held")
        self.assertEqual(summary["focus"], "overview")
        status = [c["text"] for c in view["context"]["status"]]
        self.assertEqual(status[0], "마지막 결과 뒤 멈춘 요청 1건 (보류 1)")
        self.assertEqual(status[1], "마지막 결과 기획 초안 완료")
        self.assertEqual(view["context"]["status"][1]["tip"], "status: completed")
        overview = blob(page(view, "overview"))
        for text in ("마지막 turn(T1) 뒤에 turn 없이 멈춘 요청 1건", f"{SYNTH} 후속 ZZZ123", f"{SYNTH} HTTP403 보류 사유", "research_observation"):
            self.assertIn(text, overview)
        self.assertIn("turn 없는 요청 1건", blob(page(view, "history")))
        self.assertIn("마지막 turn(T1) 뒤", blob(page(view, "history")))
        for key, question in (("followup_prior_t1", "B2 후속 ZZZ777"), ("followup_no_prior", "B3 후속 ZZZ888")):
            with self.subTest(key=key):
                summary, view = self.build(key)
                self.assertEqual(summary["focus"], "overview")
                status = [c["text"] for c in view["context"]["status"]]
                self.assertTrue(status[0].startswith("결과 없이 멈춘 요청 1건 · 순서 미확인"), status)
                self.assertTrue(status[1].startswith("마지막 결과 "), status)
                overview = blob(page(view, "overview"))
                self.assertIn(question, overview)
                self.assertIn("나중인지 알 수 없습니다", overview)
                self.assertIn("순서 미확인", blob(page(view, "history")))
                for text in ("최근 요청", "이전 요청", "마지막 turn 뒤(최근)"):
                    self.assertNotIn(text, blob(view))
        summary, view = self.build("requests_mixed")
        self.assertEqual(summary["focus"], "overview")
        self.assertEqual(view["context"]["status"][0]["text"], "결과 없이 멈춘 요청 2건 · 순서 미확인 (" +
                         ", ".join(f"{build_view.STATUS_LABEL[s]} 1" for s in dict.fromkeys(
                             r["status"] for r in build_view.turnless_requests(export_of("requests_mixed"), []))) + ")")
        overview = blob(view["pages"][0])
        self.assertIn("어느 요청이 최신인지는 export에 기록되지 않았습니다", overview)
        self.assertIn("시간 순서가 아닙니다", overview)
        self.assertNotIn("입력 필요로 멈춘 요청 기록", overview)

    def test_unmeasured_usage_is_never_zero_or_complete(self):  # v07-format-03
        _, view = self.build("usage_out_null")
        history = blob(page(view, "history"))
        self.assertNotIn("turn별 출력 토큰", history)
        self.assertIn("출력 토큰 미측정 호출이 있는 turn T1(1/1건)", history)
        _, view = self.build("usage_partial")
        export = blob(page(view, "export"))
        self.assertIn("부분 합계 · 2건 중 1건 미측정", export)
        self.assertIn("일부 측정", export)
        self.assertNotIn("turn별 출력 토큰", blob(page(view, "history")))

    def test_family_catalog_scope_and_commercial_disclosure(self):  # v07-format-04, -09
        _, view = self.build("family_catalog")
        self.assertEqual(page(view, "overview")["title"], "냉장고 제품군 상품기획")
        self.assertTrue(view["context"]["meta"].startswith("냉장고 제품군 3개 모델"))
        overview = blob(page(view, "overview"))
        for text in ("제품군 카탈로그", "S836GBB122", "B502S33", "T876MQQ012 · 결과 근거"):
            self.assertIn(text, overview)
        self.assertNotIn("S836GBB122 · 결과 근거", overview)
        # 큰 글씨 칸에는 짧은 값만: 결과 근거 모델 하나, 범위는 '제품군'(원래 이름은 설명 줄)
        metrics = next(b for b in page(view, "overview")["blocks"] if b["type"] == "metrics")["items"]
        self.assertEqual(metrics[0], {"label": "모델", "value": "T876MQQ012", "note": "냉장고 제품군 질문 · 결과 근거 모델"})
        self.assertEqual((metrics[1]["value"], metrics[1]["note"]), ("제품군", "제품군 카탈로그 · 대상 모델 3개"))
        exact = next(b for b in page(self.build("refrigerator")[1], "overview")["blocks"] if b["type"] == "metrics")["items"]
        self.assertEqual((exact[0]["value"], exact[0]["note"], exact[1]["value"]), ("B502S33", "냉장고", "모델 지정"))
        self.assertIn("상업 고지: 글과 사이트에 파트너스 활동", blob(page(view, "evidence")))

    def test_turn_order_cancellation_and_pending(self):  # v07-format-06, -07
        for key in ("third_cancelled", "fourth_pending"):
            with self.subTest(key=key):
                _, view = self.build(key)
                quote = next(b for b in page(view, "overview")["blocks"] if b["type"] == "quotes")["items"][0]
                self.assertEqual(quote["quote"], f"{SYNTH} {M} 불편 개선 시험")
                self.assertEqual(quote["chips"][0]["text"], "T1 요청 원문")
        _, view = self.build("third_cancelled")
        self.assertIn(f"{SYNTH} 셋째 취소 사유", blob(page(view, "overview")))
        self.assertIn("실행 중단은 확인 안 됨", blob(page(view, "overview")))
        _, view = self.build("cancel_after_reject")
        self.assertIn(f"{SYNTH} 사용자 취소 사유", blob(page(view, "overview")))
        self.assertNotIn("c1 · 제안", blob(view))
        self.assertIn("비워 두었습니다", page(view, "concepts")["blocks"][0]["text"])

    def test_model_authored_cancelled_result_keeps_its_reason(self):  # view-new-08
        _, view = self.build("result_cancelled")
        overview = blob(page(view, "overview"))
        self.assertIn(f"{SYNTH} 모델이 쓴 취소 사유", overview)
        self.assertNotIn("결과에 사유가 기록되지 않았습니다", overview)

    def test_export_page_check_titles_follow_the_last_candidate(self):  # view-new-07
        _, view = self.build("held_then_cancel")
        export = page(view, "export")
        self.assertIn("저장 검사 (마지막 저장 후보 · 현재 결과 아님)", blob(export))
        chips = next(b for b in export["blocks"] if b["type"] == "chips")["items"]
        self.assertTrue(chips[0]["text"].startswith("현재 결과 아님: turn 상태 취소(cancelled)"))
        self.assertFalse([c for c in chips if c["text"].startswith("✓") and c["tone"] == "green"])
        self.assertNotIn("마지막 거절 후보", blob(export))
        _, view = self.build("fourth_pending")
        export = blob(page(view, "export"))
        self.assertIn("저장 검사 (저장된 후보 없음)", export)
        self.assertIn("저장된 후보가 없어 저장 검사 기록이 없습니다", export)
        self.assertNotIn("확인한 근거 ?건", export)
        _, view = self.build("reject1")
        self.assertIn("저장 검사 (마지막 거절 후보)", blob(page(view, "export")))

    def test_exclude_pains_condition_is_shown(self):  # v07-format-11
        _, view = self.build("two_turns")
        self.assertIn(f"{SYNTH} 소음제외", blob(page(view, "overview")))
        self.assertIn("역사적 기록 · 무효(input_or_dependency_changed)", blob(page(view, "history")))

    def test_evidence_types_and_synthetic_marker(self):  # v07-format-08, view-new-10
        _, view = self.build("synthetic_catalog")
        dashboard = blob(page(view, "dashboard"))
        self.assertIn('"후기 근거", "value": 1', dashboard)
        self.assertIn('"label": "제품 사실"', dashboard)
        self.assertIn("합성 시험 자료", [c["text"] for c in view["context"]["status"]])
        _, view = self.build("synthetic_rejected")
        status = [c["text"] for c in view["context"]["status"]]
        self.assertIn("승인된 결과 없음", status)
        self.assertIn("합성 시험 자료", status)
        self.assertIn("합성 시험 자료(synthetic)", blob(page(view, "overview")))
        data = rename_source(export_of("synthetic_catalog"), "REV-AX-R302-1.0-01", "rv-001")
        for turn in data["turns"]:
            turn.pop("source_metadata", None)
            for candidate in turn["candidates"]:
                candidate.pop("source_metadata", None)
            for result in [turn["state"].get("latest_result")] + [c["result"] for c in turn["candidates"]]:
                for ref in (result or {}).get("evidence_refs") or []:
                    if ref["source_id"] == "rv-001":
                        ref["origin"]["representation"] = "excerpt"
        _, view = self.build(path=self.h.add("synthetic_catalog", "export-renamed.json", data))
        dashboard = page(view, "dashboard")
        self.assertIn("현재 웹 전달 미검증", blob(dashboard))
        self.assertNotIn('"kpis"', blob(dashboard))
        refs = build_view.read_turns(data)[-1]["result"]["evidence_refs"]
        self.assertEqual(build_view.ev_type(next(r for r in refs if r["source_id"] == "rv-001")), "원문 발췌")

    def test_dashboard_without_insights_counts_only_what_the_export_records(self):
        _, view = self.build("microwave")
        dashboard = page(view, "dashboard")
        blocks = blob_blocks(dashboard)
        titled = {b.get("title"): b for b in blocks if b.get("title")}
        # 항목 종류는 ID 접두어가 아니라 결과 목록으로 정한다(p1·f1·r1·c1은 소문자라 접두어 관례에 맞지 않는다)
        claims = {i["label"]: i["tone"] for i in titled["항목별 연결 근거"]["items"]}
        self.assertEqual(claims, {"p1 현재 불편": "red", "f1 기존 기능": "blue", "r1 남은 불편": "orange", "c1 제안": "purple"})
        self.assertEqual([(i["label"], i["value"], i["note"]) for i in titled["기존 기능과 대조한 결과"]["items"]], [("미해소", 1, "p1→r1")])
        self.assertEqual([(i["label"], i["value"]) for i in titled["항목별 근거 확인"]["items"]], [("뒷받침됨", 4)])
        sites = titled["출처 사이트별 근거"]["items"]
        self.assertEqual(sum(i["value"] for i in sites), len(export_of("microwave")["turns"][-1]["state"]["latest_result"]["evidence_refs"]))
        text = blob(dashboard)
        for expected in ("남은 불편 1개 중 제안과 연결 1개", "확정 중복 제안 0개", "확정 비중복 제안 1개", "중복 여부 미확인 제안 0개", "의미가 맞는지는 사람이 원문으로 확인해야 합니다"):
            self.assertIn(expected, text)
        for invented in ('"donut"', "의견 묶음 (모델 해석)", "발생률", "%"):  # 의견 묶음·비율을 만들지 않는다(자막은 제외)
            self.assertNotIn(invented, blob(dashboard["blocks"]))
        links = [x for row in next(b for b in page(view, "evidence")["blocks"] if b["type"] == "table")["rows"] for x in row["links"]]
        self.assertIn({"text": "c1", "tone": "purple"}, links)

    def test_story_page_shows_recorded_counts_and_links_only(self):
        _, view = self.build("microwave")
        story = page(view, "story")
        blocks = blob_blocks(story)
        hero = blocks[0]
        self.assertEqual(hero["type"], "hero")
        self.assertIn(f"{SYNTH} {M} 불편 개선 시험", hero["title"])
        self.assertEqual([(s["label"], s["value"]) for s in hero["stats"]], [("근거", 2), ("현재 불편", 1), ("남은 불편", 1), ("제안", 1)])
        self.assertEqual([c["text"] for c in hero["chips"]][:3], ["기획 초안 완료", "유효", "의미 검토 전 · 인수 전"])
        # B(슬라이드)·C(한 장) 보기는 이 키로 구역을 찾는다
        self.assertEqual([b["key"] for b in story["blocks"] if b["type"] == "story"], ["problem", "check", "flow", "solution", "trust"])
        flow = next(b for b in blocks if b["type"] == "flow")
        self.assertEqual([(n["id"], n["column"]) for n in flow["nodes"]], [("p1", "pain"), ("r1", "remaining"), ("c1", "concept")])
        self.assertEqual(flow["links"], [{"from": "p1", "to": "r1", "label": "미해소", "tone": "red"},
                                         {"from": "r1", "to": "c1", "label": "", "tone": "purple"}])
        sol = next(b for b in blocks if b["type"] == "solutions")["items"][0]
        self.assertEqual((sol["id"], sol["plan"]["status"], len(sol["steps"])), ("c1", "실측 전", 2))
        self.assertEqual(sol["links"], [{"text": "r1", "tone": "orange"}])
        quotes = next(b for b in blocks if b["type"] == "claims")["items"][0]["quotes"]
        self.assertEqual([q["source_id"] for q in quotes], [RID])
        for invented in ('"donut"', "발생률은", "%"):
            self.assertNotIn(invented, blob(story["blocks"]))
        # 검토 기록에 연결이 없으면 선을 만들지 않는다(항목은 그대로 보인다)
        data = export_of("microwave")
        for turn in data["turns"]:
            for cand in turn["candidates"]:
                assessment = (cand.get("validation") or {}).get("assessment")
                if assessment:
                    assessment["feature_matches"], assessment["concept_links"] = [], []
        _, view = self.build(path=self.h.add("microwave", "export-nolinks.json", data))
        blocks = blob_blocks(page(view, "story"))
        self.assertNotIn('"flow"', blob(blocks))
        self.assertIn("현재 웹 전달 미검증", blob(blocks))
        # 승인된 결과가 없으면 이야기 화면을 비우고 이유를 보인다
        summary, view = self.build("reject1")
        self.assertEqual(summary["focus"], "overview")
        story = blob(page(view, "story"))
        self.assertIn("비워 두었습니다", story)
        self.assertNotIn('"solutions"', story)
        _, view = self.build("synthetic_catalog")
        self.assertIn("합성 시험 자료", [c["text"] for c in page(view, "story")["blocks"][0]["chips"]])

    def test_evidence_kind_field_is_used_when_present(self):  # 이슈 #8: export에 kind가 생기면 바로 쓴다
        # 출처 메타데이터(source_metadata)가 없는 export에서 evidence_refs의 kind를 쓰는지 본다. 메타데이터가 있으면
        # 원문 지문이 맞는 메타데이터의 kind가 이긴다(test_viewer_integration).
        data = rename_source(rename_source(export_of("microwave"), RID, "forum-01"), FID, "official-02")
        for turn in data["turns"]:
            turn.pop("source_metadata", None)
            for candidate in turn["candidates"]:
                candidate.pop("source_metadata", None)
        kinds = {"forum-01": "review", "official-02": "product_fact"}
        for turn in data["turns"]:
            for result in [turn["state"].get("latest_result")] + [c["result"] for c in turn["candidates"]]:
                for ref in (result or {}).get("evidence_refs") or []:
                    ref["kind"] = kinds[ref["source_id"]]
        _, view = self.build(path=self.h.add("microwave", "export-kind.json", data))
        dashboard = page(view, "dashboard")
        self.assertIn("현재 웹 전달 미검증", blob(dashboard))
        self.assertEqual([build_view.ev_type(r) for r in build_view.read_turns(data)[-1]["result"]["evidence_refs"]], ["후기", "제품 사실"])
        # 모르는 kind는 후기로 세지 않고 이름 그대로 보인다(차트에서 빠지지 않는다)
        for turn in data["turns"]:
            for result in [turn["state"].get("latest_result")] + [c["result"] for c in turn["candidates"]]:
                for ref in (result or {}).get("evidence_refs") or []:
                    if ref["source_id"] == "forum-01":
                        ref["kind"] = "forum_post"
        _, view = self.build(path=self.h.add("microwave", "export-kind2.json", data))
        dashboard = page(view, "dashboard")
        self.assertIn("현재 웹 전달 미검증", blob(dashboard))
        self.assertEqual([build_view.ev_type(r) for r in build_view.read_turns(data)[-1]["result"]["evidence_refs"]], ["미지원(forum_post)", "제품 사실"])
        self.assertIn("현재 웹 전달 미검증", blob(page(view, "evidence")))

    def invalidated(self, key: str) -> dict:
        data = export_of(key)
        state = data["turns"][-1]["state"]
        state.update(valid=False, invalidation_reason="dataset_or_code_changed", latest_result=None)  # product-tools와 같게
        return data

    def test_invalidated_current_result_is_marked_everywhere(self):  # v07-format-10, view-new-04, -05, -06
        summary, view = self.build(path=self.h.add("microwave", "export-invalid.json", self.invalidated("microwave")))
        self.assertEqual(summary["focus"], "overview")
        overview = blob(page(view, "overview"))
        self.assertIn("현재 유효한 결과가 없습니다", overview)
        self.assertIn("마지막 승인 결과를 보여주며", overview)
        for pid in ("dashboard", "screening", "compare", "concepts", "evidence"):
            self.assertIn("무효 처리된 결과입니다", page(view, pid)["blocks"][0]["text"], pid)
        history = blob(page(view, "history"))
        self.assertIn("현재 turn · 무효(dataset_or_code_changed)", history)
        self.assertIn("무효 결과(현재 아님)", history)
        self.assertNotIn('"현재 결과"', history)
        export = blob(page(view, "export"))
        self.assertIn("저장 검사 (무효 처리된 결과)", export)
        self.assertIn("✓ 저장 승인(계약 검사)", export)
        self.assertIn("확인한 근거 2건", export)
        self.assertIn("검토 기록의 대조 판단", blob(page(view, "compare")))
        _, view = self.build(path=self.h.add("reject1", "export-reject-invalid.json", self.invalidated("reject1")))
        overview = blob(page(view, "overview"))
        self.assertIn("무효 처리 전에도 승인된 결과가 없어 보여줄 결과가 없습니다", overview)
        self.assertNotIn("마지막 승인 결과를 보여주며", overview)

    def test_invalidation_does_not_revive_a_superseded_candidate(self):  # view-new-03
        _, before = self.build("acc_then_rej")
        _, view = self.build(path=self.h.add("acc_then_rej", "export-acc-rej-invalid.json", self.invalidated("acc_then_rej")))
        for v in (before, view):
            status = [c["text"] for c in v["context"]["status"]]
            self.assertIn("승인된 결과 없음", status)
            overview = blob(page(v, "overview"))
            self.assertIn("review_not_finalizable", overview)
            self.assertNotIn("결과에 사유가 기록되지 않았습니다", overview)
            self.assertNotIn("c1 · 제안", blob(v))
            self.assertNotIn('"현재 결과"', blob(page(v, "history")))

    def test_requests_only_export_shows_reason_and_no_absolute_paths(self):  # v07-format-12
        summary, view = self.build("needs_input")
        self.assertEqual((summary["pages"], summary["focus"]), (1, "overview"))
        overview = blob(view["pages"][0])
        self.assertIn("product_required", overview)
        self.assertIn("입력 필요로 멈춘 요청 기록", overview)
        self.assertNotIn("events)에서 확인", overview)
        export = self.h.add("dishwasher")
        build_view.generate(export, None, "auto", out_dir=self.h.out)
        text = (self.h.out / "view-data.js").read_text(encoding="utf-8")
        self.assertIn(f"runtime-data/exports/{export.name}", text)
        for private in (str(self.h.root), self.h.root.as_posix(), str(Path.home())):
            self.assertNotIn(private, text)

    def test_report_view_gets_the_export_and_the_shown_turn(self):
        """보고서로 보기(신진하 양식)는 export를 직접 읽는다. 화면과 같은 결과가 나오도록 지금 화면의 turn을 함께 준다."""
        _, view = self.build("microwave")
        self.assertEqual(view["report"]["export"], export_of("microwave"))
        self.assertEqual(view["report"]["turn_id"], current_turn("microwave"))
        # 덧붙이는 그래프 두 개(근거 구성·제안과 근거 연결)는 근거 대시보드와 같은 기준으로 센다
        plan = view["report"]["plan"]
        self.assertEqual((plan["title"], plan["summary"], plan["sources"]), ("", [], []))
        self.assertEqual([s["title"] for s in plan["sections"][:2]], ["근거 구성", "제안과 근거 연결"])
        donut, bars = (s["blocks"][0] for s in plan["sections"][:2])
        result = build_view.current_row(build_view.read_turns(export_of("microwave")))["result"]
        self.assertEqual((donut["chart_type"], sum(donut["series"][0]["values"])), ("donut", len(result["evidence_refs"])))
        self.assertEqual(bars["series"][0]["values"], [len(c["source_ids"]) for c in result["concepts"]])
        self.assertIn("우선순위를 뜻하지 않습니다", bars["caption"])
        _, view = self.build("cancel_after_reject")  # 취소된 turn은 보고서의 원시 export 우회 경로도 막는다
        self.assertNotIn("report", view)
        _, view = self.build("needs_input")  # turn 없이 멈춘 요청 기록만 있으면 보고서를 두지 않는다
        self.assertNotIn("report", view)

    def test_report_limits_turn_selection_and_retains_selected_full_bodies_and_review_history(self):
        _, view = self.build("two_turns")
        report = view["report"]
        self.assertEqual([h["state"]["turn_id"] for h in report["export"]["turns"]], [report["turn_id"]])
        body = web_body("two_turns")
        turn = report["export"]["turns"][0]
        self.assertEqual(turn["state"]["latest_result"], body["result"])
        self.assertEqual(turn["state"]["latest_result"]["evidence_refs"], body["result"]["evidence_refs"])
        sections = report["plan"]["sections"]
        bodies = [b["text"] for section in sections for b in section["blocks"] if b["type"] == "paragraph"]
        for source in body["sources"]:
            self.assertIn(source["text"], bodies)
        records = {label: json.loads(value) for label, value in sections[-1]["blocks"][0]["rows"]}
        for label, key in (("binding", "binding"), ("근거 검토·전달 이력", "evidence_history"),
                           ("조사 상태", "investigation"), ("조사 사건", "investigation_events")):
            self.assertEqual(records[label], body[key])
        self.assertIn("의미 인증이 아닙니다", blob(report))

    def test_report_preserves_uncited_long_body_and_every_validation_condition_without_changing_refs(self):
        _, view = self.build("microwave")
        # Exercise only the display projection with explicit marked contract text, not a fabricated saved binding.
        export = export_of("microwave")
        body = web_body("microwave")
        context = build_view.Ctx(export, EXPORTS["microwave"], {}, web_result=body, delivery_state="verified_binding")
        context.web = json.loads(json.dumps(body))
        tail = "[합성 시험 자료] 미인용 원문 말미 조건"
        long_text = "[합성 시험 자료] " + "조건 보존 " * 500 + tail
        context.web["sources"].append({"source_id": "UNUSED-CONTRACT-ONLY", "text": long_text, "kind": "review"})
        original_refs = json.loads(json.dumps(context.result["evidence_refs"]))
        context.result = json.loads(json.dumps(context.result))
        context.result["concepts"][0]["validation_plan"].update(
            condition_controls=["[합성 시험 자료] 조건 동등"], guardrail_metrics=["[합성 시험 자료] 미확인율 제한"],
            evaluation_protocol={"denominator": "[합성 시험 자료] 전체 배정건"})
        projected = build_view.report_source(context)
        self.assertIn(long_text, [block.get("text") for section in projected["plan"]["sections"] for block in section["blocks"]])
        validation = next(section for section in projected["plan"]["sections"] if section["title"] == "보고서 범위와 검증 조건")
        self.assertEqual(json.loads(validation["blocks"][1]["rows"][0][1]), context.result["concepts"][0]["validation_plan"])
        self.assertEqual(context.result["evidence_refs"], original_refs)
        for key in ("cancel_after_reject", "reject3", "third_cancelled"):
            _, refused = self.build(key)
            self.assertNotIn("report", refused)

    def test_legacy_mode_ops_standalone_option_is_accepted_with_only_k_view(self):
        export = self.h.add("microwave")
        report = self.h.out / "compat-ops.html"
        summary = build_view.generate(export, standalone=report, out_dir=self.h.out, mode="ops")
        self.assertTrue(summary["ok"])
        self.assertNotIn("LGAX_DEFAULT_MODE", report.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            build_view.generate(export, standalone=report, out_dir=self.h.out, mode="slides")

    def test_report_vendor_files_are_kept_byte_for_byte(self):
        """app/vendor/jinha-report는 받은 그대로 둔다. 바꿀 것은 빌드(scripts/jinha-report.mjs)에서만 바꾼다."""
        vendor = VIEWER / "app" / "vendor" / "jinha-report"
        rows = re.findall(r"\| `([^`]+)` \| `([0-9a-f]{64})` \|", (vendor / "SOURCE.md").read_text(encoding="utf-8"))
        self.assertEqual(sorted(n for n, _ in rows), ["index.html", "report-app.js", "report-data-adapter.js", "result-report.css", "styles.css"])
        for name, sha in rows:
            self.assertEqual(hashlib.sha256((vendor / name).read_bytes()).hexdigest(), sha, name)

    def test_index_html_pin_and_restore(self):  # tests-docs-new-3
        export = self.h.add("microwave")
        with self.assertRaises(ValueError):
            build_view.generate(export, None, "auto", out_dir=self.h.out, index_sha256="0" * 64)
        self.assertFalse((self.h.out / "view-data.js").exists())
        good = hashlib.sha256((VIEWER / "index.html").read_bytes()).hexdigest()
        self.h.out.mkdir(parents=True, exist_ok=True)
        (self.h.out / "index.html").write_text("<script>fetch('https://example.invalid')</script>", encoding="utf-8")
        build_view.generate(export, None, "auto", out_dir=self.h.out, index_sha256=good)
        self.assertEqual((self.h.out / "index.html").read_bytes(), (VIEWER / "index.html").read_bytes())

    def test_built_index_html_keeps_the_data_tag_and_loads_nothing_but_fonts(self):
        """index.html is built from app/ (npm run build). It must stay one self-contained file."""
        html = (VIEWER / "index.html").read_text(encoding="utf-8")
        tag = '<script src="view-data.js" charset="utf-8"></script>'
        self.assertEqual(html.count(tag), 1)
        self.assertTrue(html.startswith("<!doctype html>\n<!-- Built from web/prototypes/visual-viewer/app"))
        self.assertEqual(re.findall(r"<script[^>]*\bsrc=", html), ['<script src='])  # only view-data.js
        self.assertEqual(re.findall(r'<link[^>]*href="(https?://[^"]+)"', html),
                         ["https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"])
        self.assertNotIn("/assets/", html)
        # 묶어 넣은 라이브러리의 라이선스 고지가 파일 끝에 남는다. 지운 보기만 쓰던 라이브러리·컴포넌트는 묶지 않는다.
        notices = html[html.index("THIRD-PARTY NOTICES"):]
        for needle in ("react@", "@unovis/ts@", "lucide-react@"):
            self.assertIn(needle, notices)
        for gone in ("reveal.js@", "motion@", "Cult UI", "Skiper UI"):
            self.assertNotIn(gone, notices)
        # 보고서로 보기: 신진하 보고서 양식이 한 파일 안에 들어 있고 밖에서 불러오는 것은 없다(위의 script·link 검사)
        for needle in ("HarnessReportAdapter", "embedded-report", "보고서로 보기"):
            self.assertIn(needle, html)
        export = self.h.add("microwave")
        report = self.h.out / "report-test.html"
        build_view.generate(export, None, "auto", out_dir=self.h.out, standalone=report)
        text = report.read_text(encoding="utf-8")
        self.assertNotIn(tag, text)
        self.assertIn("window.LGAX_VIEW_INLINE = true; window.LGAX_VIEW = ", text)
        self.assertIn('"id": "story"', text)
        # 보기는 K 업무형 하나라 공유 파일에 처음 열 보기를 적지 않는다
        self.assertNotIn("LGAX_DEFAULT_MODE", text)
        self.assertNotIn("LGAX_DEFAULT_MODE", html)


# ---------------------------------------------------------------- web result (product-web-result-v1)

UNTRUSTED = '<img src=x onerror="alert(1)">'


def web_body(key: str) -> dict:
    """Immutable web payload created by the real reviewed save/export fixture path."""
    expected = export_of(key)["turns"][-1]["web_binding"]
    for path in (EXPORTS[key].parent.parent / "web-deliveries").glob("web-*.json"):
        body = json.loads(path.read_bytes())
        if body.get("binding") == expected:
            return body
    raise AssertionError("Fixture has no matching reviewed web payload")


class WebResultTests(TempCase):
    def test_registered_source_table_keeps_the_end_of_a_long_selected_text(self):
        text = f"{SYNTH} " + "등록 원문 " * 200 + "본문 마지막 표식"
        context = mock.Mock(web={"sources": [{"source_id": "long-source", "kind": "review", "text": text}],
                                 "coverage": {}}, ev={})
        table = next(b for b in build_view.web_source_blocks(context) if b["type"] == "table")
        self.assertEqual(table["rows"][0]["quote"], text)

    def put(self, body: dict, name: str | None = None) -> Path:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        folder = self.h.root / "runtime-data" / "web-deliveries"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (name or f"web-{hashlib.sha256(raw).hexdigest()}.json")
        path.write_bytes(raw)
        return path

    def explicit(self, body, *, name=None, sha=None):
        export = self.h.add("microwave")
        path = self.put(body, name)
        summary = build_view.generate(export, None, "auto", out_dir=self.h.out,
                                      web_result_path=path, web_result_sha256=sha)
        return path, summary, read_view(self.h.out)

    def test_matching_reviewed_web_result_preserves_full_sources_history_and_raw_file_sha(self):
        body = web_body("microwave")
        path, summary, view = self.explicit(body)
        self.assertEqual((summary["web_delivery"], summary["web_result"], summary["warnings"]),
                         ("verified_binding", path.name, []))
        evidence = blob(page(view, "evidence"))
        for source in body["sources"]:
            self.assertIn(json.dumps(source["text"], ensure_ascii=False)[1:-1], evidence)
            self.assertIn(source["sha256"], evidence)
        self.assertIn("선택 등록본문 전체", evidence)
        self.assertIn("등록 원문 전체", evidence)
        self.assertNotIn("전달(읽음)", evidence)
        history = blob(page(view, "history"))
        for text in ("현재 버전의 검토·조사 이력", "근거 검토·전달 이력", "조사 과정 (웹 전달 파일)"):
            self.assertIn(text, history)
        exported = blob(page(view, "export"))
        for text in ("웹 전달 파일", f"runtime-data/web-deliveries/{path.name}", path.name[4:-5],
                     "전체 binding 일치", "의미 검토 전 · 인수 전", "세션 export"):
            self.assertIn(text, exported)

    def test_same_session_turn_and_result_with_any_other_binding_is_not_current(self):
        original = web_body("microwave")
        for field in build_view.BINDING_KEYS - {"session_id", "turn_id", "result_sha256"}:
            with self.subTest(field=field):
                body = json.loads(json.dumps(original))
                body["binding"][field] = 999 if field == "result_version" else "0" * 64
                _, summary, view = self.explicit(body)
                self.assertEqual(summary["web_delivery"], "mismatch")
                self.assertIsNone(summary["web_result"])
                self.assertNotIn("선택 등록본문 전체", blob(page(view, "evidence")))
                self.assertIn("현재 웹 전달 미검증", blob(view))
                self.assertNotIn("report", view)

    def test_web_result_for_another_result_or_incomplete_binding_is_not_used(self):
        for changed in ("result", "binding"):
            with self.subTest(changed=changed):
                body = web_body("microwave")
                if changed == "result":
                    body["result"]["assumptions"] = [f"{SYNTH} 옛 결과"]
                else:
                    body["binding"] = {k: body["binding"][k] for k in ("session_id", "turn_id", "result_version")}
                _, summary, view = self.explicit(body)
                self.assertIsNone(summary["web_result"])
                self.assertNotIn("등록 원문 전체", blob(page(view, "evidence")))
                self.assertNotIn("조사 과정", blob(page(view, "history")))

    def test_web_result_raw_byte_sha_and_filename_are_both_required(self):
        for named, sha in (("web-" + "0" * 64 + ".json", None), ("web-result.json", None), (None, "0" * 64)):
            with self.subTest(name=named, sha=sha):
                _, summary, view = self.explicit(web_body("microwave"), name=named, sha=sha)
                self.assertEqual(summary["web_delivery"], "mismatch")
                self.assertIsNone(summary["web_result"])
                self.assertNotIn("등록 원문 전체", blob(page(view, "evidence")))

    def test_stored_unreviewed_export_cannot_be_promoted_by_a_web_file(self):
        export = self.h.add("microwave")
        original = export_of("microwave")
        for candidate in original["turns"][-1]["candidates"]:
            candidate["validation"].pop("assessment", None)
        export.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
        path = self.put(web_body("microwave"))
        summary = build_view.generate(export, None, "auto", out_dir=self.h.out, web_result_path=path)
        self.assertEqual(summary["web_delivery"], "not_reviewed_current")
        self.assertIsNone(summary["web_result"])
        self.assertNotIn("선택 등록본문 전체", blob(read_view(self.h.out)))
        self.assertNotIn("report", read_view(self.h.out))

    def test_web_result_alone_requires_the_current_stored_export(self):
        path = self.put(web_body("microwave"))
        with self.assertRaisesRegex(SystemExit, "--export"):
            build_view.generate(None, None, "auto", out_dir=self.h.out, web_result_path=path)
        self.assertFalse((self.h.out / "view-data.js").exists())

    def test_given_web_result_of_another_format_is_not_used(self):
        body = web_body("microwave")
        body["contract_version"] = "other-v1"
        _, summary, _ = self.explicit(body)
        self.assertEqual(summary["web_delivery"], "mismatch")



class InsightsTests(TempCase):  # v07-format-05, claude-hook-bom-insights
    def test_missing_insights_shows_dashboard_notice(self):
        export = self.h.add("refrigerator")
        summary, view = self.build(path=export)
        self.assertEqual(summary["insights"], "missing")
        blocks = page(view, "dashboard")["blocks"]
        self.assertIn("의견 묶음 차트는 없습니다", blocks[0]["text"])
        self.assertIn("AI 해석 파일이 없습니다", blocks[0]["text"])
        for internal in ("session_id", "turn_id", "insights-", "runtime-data", "viewer.py"):  # 기획자용 안내에 내부 용어를 넣지 않는다
            self.assertNotIn(internal, blocks[0]["text"])
        howto = blocks[-1]
        self.assertEqual((howto["type"], howto["title"]), ("expander", "의견 묶음 차트를 그리려면 (운영 안내)"))
        self.assertIn(current_turn("refrigerator"), blob(howto))
        self.assertIn(export_of("refrigerator")["session_id"], blob(howto))
        status = {c["text"]: c.get("tip") for c in view["context"]["status"]}
        self.assertEqual(status["유효"], "valid: true")
        self.assertEqual(status["의미 검토 전 · 인수 전"], "semantic_status: unverified · acceptance_ready: false")
        self.assertNotIn("turn", page(view, "overview")["caption"]["text"] + page(view, "history")["caption"]["title"])

    def test_turn_bound_insights_draw_groups_and_bom_is_read(self):
        export = self.h.add("microwave")
        sid = export_of("microwave")["session_id"]
        groups = [{"key": "g1", "label": f"{SYNTH} 묶음", "tone": "blue", "source_ids": [RID]}]
        self.h.insights("insights-bom.json", {"session_id": sid, "turn_id": current_turn("microwave"), "groups": groups}, bom=True)
        summary, view = self.build(path=export)
        self.assertEqual((summary["insights"], summary["insights_file"], summary["warnings"]), ("matched", "insights-bom.json", []))
        dashboard = blob(page(view, "dashboard"))
        self.assertIn('"donut"', dashboard)
        self.assertIn("insights insights-bom.json · turn_id 일치", dashboard)

    def test_summaries_attach_to_story_items_and_bad_ones_are_refused(self):
        export = self.h.add("microwave")
        sid, turn = export_of("microwave")["session_id"], current_turn("microwave")
        self.h.insights("insights-sum.json", {"session_id": sid, "turn_id": turn,
                                              "summaries": {"p1": f"{SYNTH} 불편 요약", "c1": f"{SYNTH} 제안 요약", "ZZ9": "없는 항목"}})
        summary, view = self.build(path=export)
        self.assertEqual((summary["insights"], summary["warnings"]), ("matched", []))
        story = blob(page(view, "story"))
        for text in (f"{SYNTH} 불편 요약", f"{SYNTH} 제안 요약"):
            self.assertIn(text, story)
        self.assertNotIn("없는 항목", story)  # only IDs in the current result get a summary
        self.h.insights("insights-sum.json", {"session_id": sid, "turn_id": turn, "summaries": {"p1": 3}})
        summary, view = self.build(path=export)
        self.assertEqual(summary["insights"], "invalid")
        self.assertTrue(any("summaries" in w for w in summary["warnings"]), summary["warnings"])
        self.assertNotIn(f"{SYNTH} 불편 요약", blob(page(view, "story")))

    def test_insights_without_turn_id_only_for_single_turn_sessions(self):  # v07-format-05 partial
        groups = [{"key": "g1", "label": f"{SYNTH} T1 묶음", "source_ids": [RID]}]
        sid = export_of("two_turns")["session_id"]
        self.h.insights("insights-t1.json", {"session_id": sid, "groups": groups, "concept_titles": {"c1": f"{SYNTH} T1 전용 제목"}})
        summary, view = self.build("two_turns")
        self.assertEqual(summary["insights"], "unbound")
        self.assertNotIn("T1 전용 제목", blob(view))
        self.assertIn("어느 turn의 해석인지 알 수 없어", blob(page(view, "dashboard")))
        summary, view = self.build(path=self.h.add("two_turns", "export-explicit.json"), insights_path=self.h.out / "insights-t1.json")
        self.assertEqual(summary["insights"], "unbound")
        self.assertNotIn("T1 전용 제목", blob(view))
        single = self.h.add("microwave")
        self.h.insights("insights-single.json", {"session_id": export_of("microwave")["session_id"], "groups": groups})
        summary, view = self.build(path=single)
        self.assertEqual((summary["insights"], summary["warnings"]), ("unverified_binding", []))
        self.assertNotIn(f"{SYNTH} T1 묶음", blob(page(view, "dashboard")))

    def test_other_turn_and_stale_insights_are_not_applied_and_warn_visibly(self):
        export = self.h.add("microwave")
        sid = export_of("microwave")["session_id"]
        self.h.insights("insights-a.json", {"session_id": sid, "turn_id": "turn-other", "groups": [{"key": "g", "label": "x", "source_ids": [RID]}]})
        summary, view = self.build(path=export)
        self.assertEqual(summary["insights"], "other_turn")
        self.assertIn("다른 turn(turn_id)용", blob(page(view, "dashboard")))
        self.h.insights("insights-b.json", {"session_id": sid, "turn_id": current_turn("microwave"), "groups": [{"key": "g", "label": "x", "source_ids": ["REVIEW-B502S33-09"]}],
                                            "kpis": [{"label": "확인한 후기", "value": 595, "verify_in": "assumptions"}]})
        summary, view = self.build(path=export)
        self.assertEqual(summary["insights"], "stale")
        self.assertEqual(len(summary["warnings"]), 1)
        self.assertEqual(view["warnings"], summary["warnings"])
        for pid in ("overview", "dashboard"):
            self.assertIn("화면 생성 경고 1건", page(view, pid)["blocks"][0]["text"])
        self.assertIn("화면 경고 1", [c["text"] for c in view["context"]["status"]])
        dashboard = blob(page(view, "dashboard"))
        self.assertNotIn('"donut"', dashboard)
        self.assertNotIn("595", dashboard)

    def test_malformed_insights_are_skipped_not_fatal(self):  # side note: wrong-shape insights
        export = self.h.add("microwave")
        sid = export_of("microwave")["session_id"]
        for bad in ({"groups": "not-a-list"}, {"groups": [{"key": "g"}]}, {"captions": {"overview": "x"}}, {"excluded": [{"kind": "x"}]}):
            with self.subTest(bad=bad):
                self.h.insights("insights-bad.json", {"session_id": sid, "turn_id": current_turn("microwave"), **bad})
                summary, view = self.build(path=export)
                self.assertEqual(summary["insights"], "invalid")
                self.assertIn("형식이 README와 달라 쓰지 않았습니다", page(view, "overview")["blocks"][0]["text"])

    def test_explicit_insights_with_other_session_or_unverified_numbers(self):
        export = self.h.add("microwave")
        path = self.h.insights("insights-x.json", {"session_id": "other-session", "groups": []})
        summary, view = self.build(path=export, insights_path=path)
        self.assertEqual(summary["insights"], "mismatch")
        self.assertIn("session_id가 이 export와 달라", page(view, "overview")["blocks"][0]["text"])
        sid = export_of("microwave")["session_id"]
        path = self.h.insights("insights-y.json", {"session_id": sid, "turn_id": current_turn("microwave"), "kpis": [{"label": "고정", "value": 595, "verify_in": "assumptions"}]})
        summary, view = self.build(path=export, insights_path=path)
        self.assertIn("595가 결과 assumptions 원문에 없어 그리지 않았습니다", " ".join(summary["warnings"]))
        self.assertNotIn('"value": 595', blob(page(view, "dashboard")))


# ---------------------------------------------------------------- hook (in-process)

class HookTests(TempCase):

    def test_no_open_or_failed_browser_request_is_not_reported_as_open(self):
        self.h.add("refrigerator")
        with mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": "1"}), mock.patch("webbrowser.open") as browser:
            result = self.run_hook({"session_id": "no-open"}, "claude")
            self.assertTrue(result["changed"])
            self.assertFalse(result["opened_browser"])
            browser.assert_not_called()
        self.h.add("microwave")
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("webbrowser.open", return_value=False) as browser:
            result = self.run_hook({"session_id": "browser-failed"}, "claude")
            self.assertTrue(result["changed"])
            self.assertFalse(result["opened_browser"])
            browser.assert_called_once()
        self.h.add("dishwasher")
        with mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": ""}), mock.patch.object(hook, "open_browser", return_value=True) as browser:
            self.assertTrue(self.run_hook({"session_id": "browser-failed"}, "claude")["opened_browser"])
            browser.assert_called_once()

    def test_export_before_web_payload_is_rebuilt_when_exact_payload_arrives(self):
        export = self.h.add("microwave")
        body = json.loads(export.read_text(encoding="utf-8"))
        expected = body["turns"][-1]["web_binding"]
        web = self.h.root / "runtime-data/web-deliveries"
        path = next(p for p in web.glob("web-*.json") if json.loads(p.read_bytes())["binding"] == expected)
        raw = path.read_bytes()
        path.unlink()
        with mock.patch.object(hook, "open_browser"):
            self.assertTrue(hook.run({"session_id": "late-web"}, "claude", hook.Paths(str(self.h.root)))["changed"])
            self.assertEqual(self.h.state()["web_delivery"], "mismatch")
            self.assertFalse((self.h.out / ".hook-last-export").exists())
            path.write_bytes(raw)
            self.assertTrue(hook.run({"session_id": "late-web"}, "claude", hook.Paths(str(self.h.root)))["changed"])
            self.assertEqual(self.h.state()["web_delivery"], "verified_binding")
    def run_hook(self, payload, source=None):
        src, _ = hook.parse_args([source] if source else [], payload)
        return hook.run(payload, src, hook.Paths(str(self.h.root)))

    def test_rebuild_only_for_new_export_and_open_once_per_cli_session(self):
        with mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": ""}), mock.patch.object(hook, "open_browser") as opened:
            self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["reason"], "export 없음")
            first = self.h.add("refrigerator")
            result = self.run_hook({"session_id": "s1"}, "claude")
            self.assertEqual((result["export"], result["opened_browser"]), (first.name, True))
            self.assertFalse(self.run_hook({"session_id": "s1"}, "claude")["changed"])
            self.h.add("microwave")
            self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["opened_browser"], False)
            codex = self.h.add("dishwasher")
            result = self.run_hook({"session_id": "s1", "turn_id": "t1", "hook_event_name": "PostToolUse", "tool_name": "Bash"})
            self.assertEqual((result["export"], result["opened_browser"]), (codex.name, True))
            self.assertEqual(opened.call_count, 2)
        state = self.h.state()
        self.assertEqual(state["opened_sessions"], ["claude:s1", "codex:s1"])
        self.assertEqual((state["last_export"], state["built_key"]), (codex.name, state["last_key"]))
        self.assertEqual(state["insights"], "missing")

    def test_failed_export_is_retried_after_insights_change(self):  # claude-hook-bom-insights
        export = self.h.add("microwave")
        paths = hook.Paths(str(self.h.root))
        entry = hook.newest_export(paths)
        hook.write_state(paths, {"failed_key": hook.failure_key(paths, entry)})
        self.assertEqual(self.run_hook({"session_id": "s"}, "claude")["reason"], "이미 처리한 export")
        self.h.insights("insights-fixed.json", {"session_id": export_of("microwave")["session_id"], "turn_id": current_turn("microwave"),
                                                "groups": [{"key": "g", "label": "x", "source_ids": [RID]}]}, bom=True)
        with mock.patch.object(hook, "open_browser"):
            self.assertEqual(self.run_hook({"session_id": "s"}, "claude")["export"], export.name)
        self.assertEqual(self.h.state()["insights"], "matched")
        self.assertNotIn("failed_key", self.h.state())

    def test_hook_draws_the_matching_web_result_and_refuses_a_linked_web_folder(self):
        export = self.h.add("microwave")
        WebResultTests.put(self, web_body("microwave"))
        with mock.patch.object(hook, "open_browser"):
            self.assertEqual(self.run_hook({"session_id": "s"}, "claude")["export"], export.name)
        self.assertIn(f"등록 원문 전체 {len(web_body("microwave")["sources"])}건", blob(page(read_view(self.h.out), "evidence")))
        web = self.h.root / "runtime-data" / "web-deliveries"
        shutil.rmtree(web)
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        try:
            os.symlink(outside, web, target_is_directory=True)
        except OSError:  # no symlink privilege on Windows: a junction is the same reparse point
            made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(web), str(outside)], capture_output=True, timeout=10)
            self.assertEqual(made.returncode, 0, made.stderr.decode(errors="replace"))
        with self.assertRaises(hook.IntegrityError):
            hook.Paths(str(self.h.root)).validate()

    def test_broken_export_is_logged_once_then_skipped(self):
        (self.h.exports / "export-broken.json").write_text("{not json", encoding="utf-8")
        self.assertFalse(self.run_hook({"session_id": "s1"}, "claude")["changed"])
        log = (self.h.out / "hook-error.log").read_text(encoding="utf-8")
        self.assertIn("export-broken.json", log)
        self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["reason"], "이미 처리한 export")
        self.assertEqual((self.h.out / "hook-error.log").read_text(encoding="utf-8"), log)
        self.h.add("microwave")
        with mock.patch.object(hook, "open_browser"):
            self.assertTrue(self.run_hook({"session_id": "s1"}, "claude")["changed"])

    def test_state_write_and_read_retry_and_attempt_is_recorded_before_opening(self):  # state race
        paths = hook.Paths(str(self.h.root))
        real, calls = os.replace, []

        def flaky(a, b):
            calls.append(a)
            if len(calls) <= 2:
                raise PermissionError(5, "Access is denied")
            return real(a, b)

        with mock.patch.object(hook.os, "replace", flaky):
            hook.write_state(paths, {"opened_sessions": ["claude:x"]})
        reads = []

        def flaky_open(*args, **kwargs):
            reads.append(args[0])
            if len(reads) <= 2:
                raise PermissionError(13, "in use")
            return open(*args, **kwargs)

        with mock.patch.object(hook, "open", flaky_open, create=True):
            self.assertEqual(hook.read_state(paths), {"opened_sessions": ["claude:x"]})
        self.assertEqual(len(reads), 3)
        self.h.add("microwave")
        real_write = hook.write_state

        def fail_on_sessions(p, state):
            if "claude:y" in (state.get("open_attempts") or {}):
                raise PermissionError("state locked")
            return real_write(p, state)

        with mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": ""}), mock.patch.object(hook, "write_state", fail_on_sessions), mock.patch.object(hook, "open_browser") as opened:
            with self.assertRaises(PermissionError):
                hook.run({"session_id": "y"}, "claude", paths)
            opened.assert_not_called()
        self.assertEqual(list(self.h.out.glob(".hook-state.json.*.tmp")), [])

    def test_marker_follows_processed_export_only(self):  # round 5 fast path
        paths = hook.Paths(str(self.h.root))
        first = self.h.add("microwave")
        with mock.patch.object(hook, "open_browser"):
            self.run_hook({"session_id": "s"}, "codex")
        self.assertEqual(Path(paths.marker).read_text(encoding="utf-8"), first.name)
        (self.h.exports / "export-zz-broken.json").write_text("{", encoding="utf-8")
        os.utime(self.h.exports / "export-zz-broken.json", (time.time() + 100, time.time() + 100))
        self.run_hook({"session_id": "s"}, "codex")
        self.assertEqual(Path(paths.marker).read_text(encoding="utf-8"), first.name)  # 실패한 export는 표시하지 않는다
        later = self.h.add("dishwasher", "export-zzz-later.json")
        os.utime(later, (time.time() + 200, time.time() + 200))
        run_viewer("install", "--codex", str(self.h.root))  # 설치 기준점도 표시한다
        self.assertEqual(Path(paths.marker).read_text(encoding="utf-8"), later.name)
        hook.write_state(paths, {})
        self.assertFalse(os.path.exists(paths.marker))

    def test_os_lock_excludes_second_holder_and_frees_on_release(self):
        paths = hook.Paths(str(self.h.root))
        first, second = hook.Lock(paths), hook.Lock(paths)
        self.assertTrue(first.acquire(0))
        self.assertFalse(second.acquire(0.3))
        first.release()
        self.assertTrue(second.acquire(0))
        second.release()

    def test_viewer_state_updates_wait_for_the_hook_lock(self):  # side note: open/install vs hook lock
        import threading

        paths = hook.Paths(str(self.h.root))
        holder = hook.Lock(paths)
        self.assertTrue(holder.acquire(0))
        done = threading.Event()
        worker = threading.Thread(target=lambda: (viewer.update_state(paths, lambda s: s.update(marker=1)), done.set()))
        worker.start()
        time.sleep(0.4)
        self.assertFalse(done.is_set())
        holder.release()
        worker.join(10)
        self.assertTrue(done.is_set())
        self.assertEqual(hook.read_state(paths)["marker"], 1)

    def test_argument_parsing(self):
        digest = "a" * 64
        self.assertEqual(hook.parse_args(["codex", digest, "b" * 64], {}), ("codex", {"build_view": digest, "index": "b" * 64}))
        self.assertEqual(hook.parse_args([], {"turn_id": "t"})[0], "codex")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "x"}):
            self.assertEqual(hook.parse_args([], {}), ("claude", {}))


# ---------------------------------------------------------------- installed hook process

def windows_shell(name: str) -> str | None:
    """Codex가 Windows에서 훅을 실행하는 셸. cmd: 0.146(또는 세션 셸이 없을 때), powershell·pwsh: 0.162의 사용자 셸."""
    if os.name != "nt":
        return None
    system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    found = {"cmd": os.environ.get("COMSPEC") or os.path.join(system, "cmd.exe"),
             "powershell": os.path.join(system, "WindowsPowerShell", "v1.0", "powershell.exe"),
             "pwsh": shutil.which("pwsh") or r"C:\Program Files\PowerShell\7\pwsh.exe"}[name]
    return found if os.path.isfile(found) else None


def codex_runner(command: str, cwd: Path, stdin: bytes, env: dict, shell: str = "cmd") -> subprocess.CompletedProcess:
    """openai/codex의 hooks command_runner와 같은 방식으로 commandWindows를 실행한다(작업 폴더 = 하네스).

    - cmd: `COMSPEC /C "<명령>"`를 raw 인자로(0.146, 0.162에서 세션 셸이 없거나 cmd일 때).
    - powershell·pwsh: `<셸> -NoProfile -Command <명령>`, 명령은 보통 인자 하나(0.162.1의 Windows 기본 사용자 셸).
    """
    exe = windows_shell(shell)
    if shell == "cmd":
        return subprocess.run(f'{exe} /C "{command}"', input=stdin, capture_output=True, cwd=cwd, env=env, timeout=120)
    return subprocess.run([exe, "-NoProfile", "-Command", command], input=stdin, capture_output=True, cwd=cwd, env=env, timeout=120)


class InstalledHookProcessTests(TempCase):
    """Runs the exact installed command (or its Python part) as the CLIs would: stdin JSON, check silence."""

    def setUp(self):
        super().setUp()
        code, text = run_viewer("install", "--both", str(self.h.root))
        self.assertEqual(code, 0, text)
        self.claude = self.entry(".claude/settings.local.json")
        self.codex = self.entry(".codex/hooks.json")
        self.log = self.h.out / "hook-error.log"
        self.start_log = self.h.out / viewer.START_LOG

    def entry(self, rel):
        config = json.loads((self.h.root / rel).read_text(encoding="utf-8"))
        return [h for groups in config["hooks"].values() for g in groups for h in g["hooks"] if viewer.is_ours(h)][0]

    def python_part(self, entry):
        """등록된 명령의 Python 부분만 그 지문·인자 그대로(Codex는 하네스 경로를 인자로 받는다)."""
        command = entry["command"]
        encoded = re.search(r"-EncodedCommand\s+([A-Za-z0-9+/=]+)", command)
        if encoded:
            script = base64.b64decode(encoded.group(1)).decode("utf-16le")
            self.assertIn(viewer._WINDOWS_PYTHON_CODE.replace("'", "''"), script)
            pins = re.findall(r"[0-9a-f]{64}", script)
            self.assertEqual(len(pins), 3)
            return [sys.executable, "-I", "-B", "-c", viewer._WINDOWS_PYTHON_CODE, "claude", str(self.h.root), *pins]
        m = re.search(r'python -I -B -c "(.*)" claude ([0-9a-f]{64}) ([0-9a-f]{64})', command)
        if m:
            return [sys.executable, "-I", "-B", "-c", m.group(1), "claude", m.group(2), m.group(3)]
        m = re.search(r'-I -B -c "(.*)" codex "\$H" ([0-9a-f]{64}) ([0-9a-f]{64}) ([0-9a-f]{64})', command)
        self.assertIsNotNone(m, command)
        return [sys.executable, "-I", "-B", "-c", m.group(1), "codex", str(self.h.root), m.group(2), m.group(3), m.group(4)]

    def stop(self, session, **extra):
        return {"session_id": session, "turn_id": "t1", "hook_event_name": "Stop", "stop_hook_active": False,
                "last_assistant_message": f"{SYNTH} 답변", "cwd": str(self.h.root), **extra}

    def env(self, **extra):
        environment = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR",) and k.lower() != "nodefaultcurrentdirectoryinexepath"}
        environment.update(extra, LGAX_VIEWER_NO_OPEN="1")
        return environment

    def call(self, argv, payload, cwd, shell=False, env=None):
        stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        return subprocess.run(argv, input=stdin, capture_output=True, cwd=cwd, env=self.env(**(env or {})), shell=shell, timeout=120)

    def assertSilentZero(self, proc):
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"", b""))

    def log_size(self):
        return self.log.stat().st_size if self.log.exists() else 0

    def test_codex_entry_is_stop_sync_hardened_and_flags_pinned(self):  # round 5: Stop, fast path, no venv interpreter
        config = json.loads((self.h.root / ".codex/hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(list(config["hooks"]), ["Stop"])  # 셸 명령마다 도는 PostToolUse에는 없다
        self.assertNotIn("matcher", config["hooks"]["Stop"][0])
        self.assertNotIn("async", self.codex)
        self.assertEqual(self.codex["timeout"], 30)
        self.assertEqual((self.claude.get("async"), self.claude["timeout"]), (True, 60))
        windows = self.codex["commandWindows"]
        self.assertRegex(windows, r"^\.codex\\visual-viewer-hook\.cmd codex( [0-9a-f]{64}){4}$")
        launcher = self.h.root / ".codex" / "visual-viewer-hook.cmd"
        text = launcher.read_bytes().decode("ascii")
        self.assertEqual(windows.split()[-1], hashlib.sha256(launcher.read_bytes()).hexdigest())
        digests = viewer.app_digests(self.h.root / "web/prototypes/visual-viewer")
        self.assertEqual(windows.split()[2:5], [digests["hook"], digests["build_view"], digests["index"]])
        self.assertIn("set NoDefaultCurrentDirectoryInExePath=1", text)
        self.assertNotIn("for /f", text)  # Native UTF8 interpreter path must not pass through cmd's codepage.
        encoded = re.search(r"-EncodedCommand ([A-Za-z0-9+/=]+)", text)
        self.assertIsNotNone(encoded)
        script = base64.b64decode(encoded.group(1)).decode("utf-16le")
        self.assertIn("StandardOutputEncoding=[Text.Encoding]::UTF8", script)
        self.assertIn(viewer.FIND_PYTHON.removeprefix("uv "), script)
        self.assertIn("-I -B -c", script)
        self.assertIn("hook-start-error.log", script)
        self.assertLess(script.index("if(-not (G $r))"), script.index("CreateDirectory"))
        self.assertTrue(text.rstrip().endswith("exit /b 0"))
        posix = self.codex["command"]
        for part in ('cd / || exit 0', viewer.FIND_PYTHON, '"$P" -I -B -c "', 'codex "$H"', '>/dev/null 2>>"$O/hook-start-error.log"; exit 0'):
            self.assertIn(part, posix)
        self.assertNotIn("uv run", posix)
        claude = self.claude["command"]
        if "-EncodedCommand" in claude:
            encoded = re.search(r"-EncodedCommand ([A-Za-z0-9+/=]+)", claude)
            claude = base64.b64decode(encoded.group(1)).decode("utf-16le")
            self.assertIn("run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c", claude)
            self.assertIn("WriteAllText($l,$v[2]", claude)
        for command in (claude, posix):
            self.assertEqual(len(set(re.findall(r"[0-9a-f]{64}", command))), 3)

    def test_codex_stop_payload_triggers_rebuild(self):  # codex-hook-01, round 5
        self.h.add("microwave")
        self.assertSilentZero(self.call(self.python_part(self.codex), self.stop("x1"), self.h.root))
        self.assertFalse(self.h.state().get("opened_sessions"))  # NO_OPEN is not a successful OS request.
        self.assertTrue((self.h.out / "view-data.js").is_file())
        self.assertEqual((self.h.out / ".hook-last-export").read_text(encoding="utf-8"), EXPORTS["microwave"].name)
        self.h.add("dishwasher")
        self.assertSilentZero(self.call(self.python_part(self.claude), {"session_id": "c1", "tool_name": "PowerShell"}, Path.home(),
                                        env={"CLAUDE_PROJECT_DIR": str(self.h.root)}))
        self.assertFalse(self.h.state().get("opened_sessions"))

    def test_tampered_viewer_files_are_not_executed_and_are_logged(self):  # codex-hook-02, installer-new-pinned-other-cli-silent
        app = self.h.root / "web/prototypes/visual-viewer"
        self.h.add("microwave")
        for name, needle in (("build_view.py", "build_view.py가 설치 때와 다릅니다"), ("index.html", "index.html이 설치 때와 다릅니다")):
            with self.subTest(name=name):
                original = (app / name).read_bytes()
                (app / name).write_bytes(original + b"\n<!-- tampered -->\n" if name.endswith(".html") else original + b"\nTAMPERED = True\n")
                self.assertSilentZero(self.call(self.python_part(self.codex), self.stop("x"), self.h.root))
                self.assertFalse((self.h.out / "view-data.js").exists())
                self.assertIn(needle, self.log.read_text(encoding="utf-8"))
                self.assertFalse(json.loads(run_viewer("status", str(self.h.root))[1])["codex"]["files_match_command"])
                (app / name).write_bytes(original)
        marker = self.h.root / "hook-ran.txt"
        (app / "hook.py").write_bytes((app / "hook.py").read_bytes() + f"\nopen({str(marker)!r}, 'w').close()\n".encode())
        before = self.log_size()
        self.assertSilentZero(self.call(self.python_part(self.codex), {"session_id": "x"}, self.h.root))
        self.assertFalse(marker.exists())
        self.assertFalse((self.h.out / "view-data.js").exists())
        self.assertIn("hook.py is missing or differs", self.log.read_bytes()[before:].decode("utf-8", "replace"))

    def test_garbage_input_missing_script_and_errors_stay_silent(self):
        self.h.add("held")
        self.assertSilentZero(self.call(self.python_part(self.codex), b"\xff not json", self.h.root))
        self.assertFalse(self.h.state().get("opened_sessions"))
        broken = self.h.exports / "export-zz-broken.json"
        broken.write_text("{", encoding="utf-8")
        os.utime(broken, (time.time() + 100, time.time() + 100))
        self.assertSilentZero(self.call(self.python_part(self.codex), {"session_id": "x"}, self.h.root))
        self.assertIn("export-zz-broken.json", self.log.read_text(encoding="utf-8"))
        (self.h.root / "web/prototypes/visual-viewer/hook.py").unlink()
        self.assertSilentZero(self.call(self.python_part(self.codex), {"session_id": "x"}, self.h.root))
        self.assertIn("hook.py is missing or differs", self.log.read_text(encoding="utf-8"))

    # The exact command strings per shell. Skips say why, so a missing shell or uv is visible in the run.
    def need_uv(self):
        if not shutil.which("uv"):
            self.skipTest("uv not on PATH: the exact command runs through uv")

    def claude_run(self, name, wrap, shell=False):
        self.need_uv()
        self.h.add(FAMILIES[len(name) % 3][0], f"export-{name}.json")
        self.assertSilentZero(self.call(wrap(self.claude["command"]), {"session_id": name}, Path.home(), shell=shell,
                                        env={"CLAUDE_PROJECT_DIR": str(self.h.root)}))
        self.assertEqual(self.h.state()["last_export"], f"export-{name}.json")
        self.assertFalse(self.h.state().get("opened_sessions"))

    def test_claude_command_default_shell(self):
        self.claude_run("default", lambda c: c, shell=True)  # cmd.exe on Windows, /bin/sh elsewhere

    def test_claude_command_git_bash(self):
        bash = git_bash()
        if not bash:
            self.skipTest("Git Bash not found (WSL bash in System32 is not used)")
        self.claude_run("gitbash", lambda c: [bash, "-c", c])

    def test_claude_command_windows_powershell(self):
        if os.name != "nt" or not shutil.which("powershell.exe"):
            self.skipTest("Windows PowerShell not available")
        self.claude_run("powershell", lambda c: ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", c])

    def check_codex_windows(self, shell):  # E2E 0.162.1 PowerShell, hooks-new-01, codex-hook-02, round 3 logging, round 5 fast path
        """정확한 commandWindows를 Codex처럼 실행: exit 0·무출력, 새 export 재생성, 빠른 길, 심은 uv.cmd·표시 파일 무시, 오류 기록."""
        if os.name != "nt":
            self.skipTest("commandWindows runs only on Windows")
        if not windows_shell(shell):
            self.skipTest(f"{shell} is not installed on this machine")
        self.need_uv()
        app = self.h.root / "web/prototypes/visual-viewer"

        def run(session, **env):
            proc = codex_runner(self.codex["commandWindows"], self.h.root, json.dumps(self.stop(session)).encode(), self.env(**env), shell)
            self.assertSilentZero(proc)
            return json.loads(run_viewer("status", str(self.h.root))[1])

        run(f"{shell}-0")  # export 없음: 아무것도 하지 않는다
        self.assertFalse((self.h.out / "view-data.js").exists())
        self.h.add("microwave")
        run(f"{shell}-1")
        self.assertFalse(self.h.state().get("opened_sessions"))
        self.assertEqual(self.h.state()["last_export"], EXPORTS["microwave"].name)
        marker = self.h.root / "planted-ran.txt"
        (self.h.root / "uv.cmd").write_text(f'@echo off\r\necho planted> "{marker}"\r\n', encoding="ascii")
        self.h.add("dishwasher")
        run(f"{shell}-2")
        self.assertFalse(marker.exists(), "uv.cmd in the harness root ran")
        self.assertEqual(self.h.state()["last_export"], EXPORTS["dishwasher"].name)
        (self.h.root / "uv.cmd").unlink()
        # 빠른 길: 새 export가 없으면 Python을 시작하지 않는다(바꾼 hook.py가 있어도 로그가 늘지 않음)
        original = (app / "hook.py").read_bytes()
        (app / "hook.py").write_bytes(original + b"\n# tampered\n")
        before = self.log_size()
        run(f"{shell}-fast")
        self.assertEqual(self.log_size(), before)
        # 새 export는 빠른 길이 건너뛰지 않는다
        self.h.add("refrigerator")
        report = run(f"{shell}-3")
        self.assertIn("hook.py is missing or differs", report["last_error"])
        self.assertEqual(report["last_error_file"], "hook-error.log")
        (app / "hook.py").write_bytes(original)
        # 샌드박스가 쓸 수 있는 표시 파일에 명령을 넣어도 실행되지 않고, 비교가 틀리면 Python으로 넘어간다
        pwned = self.h.root / "pwned.txt"
        (self.h.out / ".hook-last-export").write_text(f'x" == "x" echo pwned> "{pwned}" & rem "', encoding="ascii")
        report = run(f"{shell}-inject")
        self.assertFalse(pwned.exists())
        self.assertEqual(self.h.state()["last_export"], EXPORTS["refrigerator"].name)
        original = (app / "build_view.py").read_bytes()
        (app / "build_view.py").write_bytes(original + b"\nTAMPERED = True\n")
        self.h.add("held")
        self.assertIn("build_view.py가 설치 때와 다릅니다", run(f"{shell}-4")["last_error"])
        (app / "build_view.py").write_bytes(original)
        broken = self.h.exports / "export-zz-broken.json"
        broken.write_text("{", encoding="utf-8")
        os.utime(broken, (time.time() + 100, time.time() + 100))
        self.assertIn("view 생성 실패 export-zz-broken.json", run(f"{shell}-5")["last_error"])
        self.assertNotIn("PermissionError", self.log.read_text(encoding="utf-8"))
        self.assertEqual(self.start_log.stat().st_size, 0)  # 정상 시작이면 시작 오류 파일은 비어 있다
        fake = Path(self.tmp.name) / f"fakeuv-{shell}"
        fake.mkdir()
        (fake / "uv.cmd").write_text("@echo off\r\necho error: No interpreter found for Python 3.12 1>&2\r\nexit /b 2\r\n", encoding="ascii")
        system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        report = run(f"{shell}-6", PATH=f"{fake};{system}")
        # .NET launches the actual executable; a PATH-only uv.cmd shim is not
        # an interpreter. Startup failure must still be silent and recorded.
        self.assertTrue(report["last_error"].strip())
        self.assertRegex(report["last_error"], r"No interpreter found|cannot find|file specified|Start")
        self.assertEqual(report["last_error_file"], viewer.START_LOG)
        run(f"{shell}-7", PATH=system)  # uv 없음
        self.assertGreater(self.start_log.stat().st_size, 0)

    def test_codex_windows_command_under_cmd(self):
        self.check_codex_windows("cmd")

    def test_codex_windows_command_under_windows_powershell(self):
        self.check_codex_windows("powershell")

    def test_codex_windows_command_under_pwsh(self):
        self.check_codex_windows("pwsh")

    def test_codex_posix_command_in_sh(self):  # hooks-new-01, round 5 (macOS·Linux form; checked with Git Bash on Windows)
        bash = git_bash()
        if not bash:
            self.skipTest("Git Bash / sh not found")
        fake = Path(self.tmp.name) / "fakeuv-sh"
        fake.mkdir()
        script = fake / "uv"
        script.write_text("#!/bin/sh\necho 'error: fake uv failure' >&2\nexit 2\n", encoding="ascii", newline="\n")
        script.chmod(0o755)
        tools = Path(bash).resolve().parents[1] / "usr" / "bin" if os.name == "nt" else Path("/usr/bin")
        self.h.add("held")
        proc = self.call([bash, "-c", self.codex["command"]], self.stop("p"), self.h.root,
                         env={"PATH": os.pathsep.join([str(fake), str(tools), os.path.dirname(bash)])})
        self.assertSilentZero(proc)
        self.assertIn("fake uv failure", self.start_log.read_text(encoding="utf-8", errors="replace"))
        self.assertIn("fake uv failure", json.loads(run_viewer("status", str(self.h.root))[1])["last_error"])
        self.need_uv()
        self.h.add("microwave")
        self.assertSilentZero(self.call([bash, "-c", self.codex["command"]], self.stop("p2"), self.h.root))
        self.assertFalse(self.h.state().get("opened_sessions"))
        app = self.h.root / "web/prototypes/visual-viewer"
        (app / "hook.py").write_bytes((app / "hook.py").read_bytes() + b"\n# tampered\n")
        before = self.log_size()
        self.assertSilentZero(self.call([bash, "-c", self.codex["command"]], self.stop("p3"), self.h.root))
        self.assertEqual(self.log_size(), before)  # 빠른 길: 새 export가 없으면 Python을 시작하지 않는다

    def test_codex_interpreter_ignores_harness_venv(self):  # round 5: .venv route
        """하네스에 심은 .venv(.pth)·.python-version·sitecustomize.py·uv.cmd가 Codex 훅에서 실행되지 않는다."""
        self.need_uv()
        venv = self.h.root / ".venv"
        made = subprocess.run(["uv", "venv", "--quiet", "--python", "3.12", "--no-python-downloads", str(venv)], capture_output=True, timeout=120)
        if made.returncode:
            self.skipTest("uv venv could not create a Python 3.12 venv here")
        site = next(venv.glob("Lib/site-packages")) if os.name == "nt" else next(venv.glob("lib/python3*/site-packages"))
        ran = self.h.root / "venv-code-ran.txt"
        (site / "zz_probe.pth").write_text(f"import os; open({str(ran)!r}, 'w').close()\n", encoding="utf-8")
        (self.h.root / ".python-version").write_text("3.11\n", encoding="ascii")
        (self.h.root / "sitecustomize.py").write_text(f"open({str(ran)!r}, 'w').close()\n", encoding="utf-8")
        # 시험을 `uv run`으로 돌리면 VIRTUAL_ENV가 바깥 venv를 가리켜 대조가 하네스 .venv를 보지 않는다.
        control_env = {k: v for k, v in self.env().items() if k != "VIRTUAL_ENV"}
        control = subprocess.run("uv run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -c pass",
                                 shell=True, capture_output=True, cwd=self.h.root, env=control_env, timeout=120)
        self.assertEqual(control.returncode, 0)
        self.assertTrue(ran.exists(), "control: the planted .pth must run through the old `uv run` route")
        ran.unlink()
        planted = {"VIRTUAL_ENV": str(venv)}  # VIRTUAL_ENV가 심은 .venv를 가리켜도 쓰지 않는다
        runners = [("python-part", lambda: self.call(self.python_part(self.codex), self.stop("v0"), self.h.root))]
        if os.name == "nt":
            for shell in ("cmd", "powershell", "pwsh"):
                if windows_shell(shell):
                    runners.append((shell, lambda shell=shell: codex_runner(self.codex["commandWindows"], self.h.root,
                                                                            json.dumps(self.stop(shell)).encode(), self.env(**planted), shell)))
        bash = git_bash()
        if bash:
            runners.append(("sh", lambda: self.call([bash, "-c", self.codex["command"]], self.stop("sh"), self.h.root, env=planted)))
        for i, (label, run) in enumerate(runners):
            with self.subTest(runner=label):
                self.h.add(FAMILIES[i % 3][0], f"export-venv-{label}.json")
                self.assertSilentZero(run())
                self.assertFalse(ran.exists(), f"{label}: code planted in the harness ran")
                self.assertEqual(self.h.state()["last_export"], f"export-venv-{label}.json")

    def test_install_for_one_cli_repins_the_other(self):  # hooks-new-02, installer-new-pinned-other-cli-silent, tests-docs-new-1
        src2 = Path(self.tmp.name) / "src2" / "web" / "prototypes" / "visual-viewer"
        src2.mkdir(parents=True)
        for name in viewer.APP_FILES:
            shutil.copyfile(VIEWER / name, src2 / name)
        (src2 / "hook.py").write_bytes((src2 / "hook.py").read_bytes() + b"\n# updated viewer\n")
        old_codex = self.codex["commandWindows"]
        proc = subprocess.run([sys.executable, str(src2 / "viewer.py"), "install", "--claude", str(self.h.root)],
                              capture_output=True, env=self.env(PYTHONIOENCODING="utf-8"), timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertIn("[Codex CLI] 이미 등록된 훅도 새 파일 지문으로 갱신했습니다", proc.stdout.decode("utf-8"))
        self.assertNotEqual(self.entry(".codex/hooks.json")["commandWindows"], old_codex)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertTrue(report["claude"]["files_match_command"] and report["codex"]["files_match_command"])
        self.h.add("microwave")
        self.assertSilentZero(self.call(self.python_part(self.entry(".codex/hooks.json")), self.stop("after-update"), self.h.root))
        self.assertFalse(self.h.state().get("opened_sessions"))
        (self.h.root / ".codex/hooks.json").write_text("{broken", encoding="utf-8")
        code, text = run_viewer("install", "--claude", str(self.h.root))
        self.assertEqual(code, 0)
        self.assertIn("[Codex CLI] 주의: 이미 등록된 훅의 지문을 새 파일에 맞추지 못했습니다", text)


# ---------------------------------------------------------------- installer

class InstallTests(TempCase):
    old = {"type": "command", "command": "C:/Users/someone/Python314/python.exe -I -S -B C:/Users/someone/h/runtime-data/visual-viewer/hook.py",
           "timeout": 30, "async": True}
    lint = {"matcher": "apply_patch", "hooks": [{"type": "command", "command": "echo lint", "timeout": 5}]}
    stop_lint = {"hooks": [{"type": "command", "command": "echo stop-lint", "timeout": 5}]}
    mine = {"type": "command", "command": "echo mine", "timeout": 5}

    def write(self, rel, value, encoding="utf-8"):
        path = self.h.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding=encoding)
        return path

    def load(self, rel):
        return json.loads((self.h.root / rel).read_text(encoding="utf-8"))

    def test_claude_merge_keeps_other_settings_moves_misplaced_entry_and_is_idempotent(self):  # installer-new-inplace-keeps-wrong-matcher-event
        other = {"matcher": "Write", "hooks": [{"type": "command", "command": "echo other"}]}
        self.write(".claude/settings.local.json", {"permissions": {"allow": ["Bash(uv run:*)"]},
                                                    "hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [self.old]}, other],
                                                              "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}]}})
        code, text = run_viewer("install", "--claude", str(self.h.root))
        self.assertIn("옮겼습니다", text)
        run_viewer("install", "--claude", str(self.h.root))
        config = self.load(".claude/settings.local.json")
        self.assertEqual(config["permissions"], {"allow": ["Bash(uv run:*)"]})
        self.assertEqual(config["hooks"]["Stop"], [{"hooks": [{"type": "command", "command": "echo stop"}]}])
        groups = config["hooks"]["PostToolUse"]
        self.assertEqual(groups[0], other)
        self.assertEqual(groups[1]["matcher"], "Bash|PowerShell")
        self.assertEqual(len(viewer.our_positions(config)), 1)
        command = groups[1]["hooks"][0]["command"]
        for private in (str(self.h.root), self.h.root.as_posix(), "Users", "someone"):
            self.assertNotIn(private, command)
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]", command))
        if "-EncodedCommand" in command:
            self.assertTrue(viewer.is_ours({"command": command}))
        else:
            self.assertIsNone(re.search(r"[$%!`^&|<>\\]", command.split('"')[1]))
        for name in viewer.APP_FILES:
            self.assertEqual((self.h.root / "web/prototypes/visual-viewer" / name).read_bytes(), (VIEWER / name).read_bytes())
        self.assertEqual((self.h.out / "index.html").read_bytes(), (VIEWER / "index.html").read_bytes())
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual((report["claude"]["registered"], report["claude"]["misplaced"], report["claude"]["matcher"]), (True, 0, "Bash|PowerShell"))

    def test_codex_entry_in_wrong_event_is_moved(self):  # installer-new-inplace-keeps-wrong-matcher-event, round 5 migration
        self.write(".codex/hooks.json", {"hooks": {"SessionEnd": [{"hooks": [dict(self.old)]}], "PostToolUse": [self.lint]}})
        run_viewer("install", "--codex", str(self.h.root))
        config = self.load(".codex/hooks.json")
        self.assertNotIn("SessionEnd", config["hooks"])
        self.assertEqual(config["hooks"]["PostToolUse"], [self.lint])
        self.assertTrue(viewer.is_ours(config["hooks"]["Stop"][0]["hooks"][0]))
        report = json.loads(run_viewer("status", str(self.h.root))[1])["codex"]
        self.assertEqual((report["registered"], report["misplaced"], report["event"]), (True, 0, "Stop"))
        # 이전 버전처럼 PostToolUse(Bash)에 있던 Codex 항목은 Stop으로 옮긴다(명령이 바뀌어 /hooks 재신뢰 필요)
        self.write(".codex/hooks.json", {"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [dict(self.old)]}]}})
        code, text = run_viewer("install", "--codex", str(self.h.root))
        self.assertIn("Stop로 옮겼습니다", text)
        config = self.load(".codex/hooks.json")
        self.assertEqual(list(config["hooks"]), ["Stop"])

    def test_codex_positions_are_preserved_for_groups_and_handlers(self):  # codex-hook-03, installer-new-handler-shift-on-uninstall
        rel = ".codex/hooks.json"
        self.write(rel, {"hooks": {"Stop": [{"hooks": [self.old]}, self.stop_lint]}})
        self.assertEqual(run_viewer("install", "--codex", str(self.h.root))[0], 0)
        groups = self.load(rel)["hooks"]["Stop"]
        self.assertTrue(viewer.is_ours(groups[0]["hooks"][0]))
        self.assertEqual(groups[1], self.stop_lint)
        self.assertEqual(run_viewer("uninstall", "--codex", str(self.h.root))[0], 0)
        self.assertEqual(self.load(rel)["hooks"]["Stop"], [{"hooks": []}, self.stop_lint])
        self.assertIn("추가(이전 자리)", run_viewer("install", "--codex", str(self.h.root))[1])
        groups = self.load(rel)["hooks"]["Stop"]
        self.assertTrue(viewer.is_ours(groups[0]["hooks"][0]))
        self.assertEqual(groups[1], self.stop_lint)
        # 같은 묶음 안 뒤쪽 처리기: 빈 명령 자리표시로 번호(:0:1)를 지킨다
        config = self.load(rel)
        config["hooks"]["Stop"][0]["hooks"].append(self.mine)
        self.write(rel, config)
        code, text = run_viewer("uninstall", "--codex", str(self.h.root))
        self.assertIn("빈 명령 자리표시", text)
        self.assertEqual(self.load(rel)["hooks"]["Stop"][0]["hooks"], [viewer.PLACEHOLDER, self.mine])
        run_viewer("install", "--codex", str(self.h.root))
        handlers = self.load(rel)["hooks"]["Stop"][0]["hooks"]
        self.assertTrue(viewer.is_ours(handlers[0]))
        self.assertEqual(handlers[1], self.mine)
        # Claude는 위치 신뢰가 없어 자리표시를 남기지 않는다
        self.write(".claude/settings.local.json", {"hooks": {"PostToolUse": [{"matcher": "Bash|PowerShell", "hooks": [self.old, self.mine]}]}})
        run_viewer("uninstall", "--claude", str(self.h.root))
        self.assertEqual(self.load(".claude/settings.local.json")["hooks"]["PostToolUse"][0]["hooks"], [self.mine])
        self.write(rel, {"hooks": {"Stop": [self.stop_lint], "PostToolUse": [self.lint]}})
        run_viewer("install", "--codex", str(self.h.root))
        run_viewer("uninstall", "--codex", str(self.h.root))
        self.assertEqual(self.load(rel), {"hooks": {"Stop": [self.stop_lint], "PostToolUse": [self.lint]}})

    def test_codex_uninstall_deletes_own_file_and_keeps_config(self):
        toml = self.write(".codex/config.toml", "[agents]\nenabled = true\n")
        before = toml.read_bytes()
        run_viewer("install", "--codex", str(self.h.root))
        self.assertIn('" codex ', self.load(".codex/hooks.json")["hooks"]["Stop"][0]["hooks"][0]["command"])
        self.assertTrue((self.h.root / ".codex/visual-viewer-hook.cmd").is_file())
        self.assertEqual(json.loads(run_viewer("status", str(self.h.root))[1])["codex"]["launcher"], ".codex/visual-viewer-hook.cmd")
        run_viewer("uninstall", "--codex", str(self.h.root))
        self.assertFalse((self.h.root / ".codex/hooks.json").exists())
        self.assertFalse((self.h.root / ".codex/visual-viewer-hook.cmd").exists())
        self.assertEqual(toml.read_bytes(), before)
        self.assertTrue((self.h.root / "web/prototypes/visual-viewer/hook.py").is_file())

    def test_invalid_non_utf8_and_wrong_shape_configs(self):  # installer-non-utf8-settings-traceback, side note: status shape
        path = self.write(".claude/settings.local.json", "{broken")
        code, text = run_viewer("install", "--claude", str(self.h.root))
        self.assertEqual(code, 1)
        self.assertIn("JSON", text)
        self.assertEqual(path.read_text(encoding="utf-8"), "{broken")
        self.assertFalse((self.h.root / "web").exists())
        for encoding in ("utf-16", "cp949"):
            with self.subTest(encoding=encoding):
                path = self.write(".claude/settings.local.json", '{"hooks": {}, "메모": "한글"}', encoding=encoding)
                raw = path.read_bytes()
                code, text = run_viewer("install", "--claude", str(self.h.root))
                self.assertEqual(code, 1)
                self.assertIn("UTF-8이 아니어서", text)
                self.assertNotIn("Traceback", text)
                self.assertEqual(path.read_bytes(), raw)
                code, text = run_viewer("status", str(self.h.root))
                self.assertEqual(code, 0)
                self.assertIn("UTF-8이 아니어서", json.loads(text)["claude"]["error"])
        self.write(".claude/settings.local.json", {"hooks": {"PostToolUse": {"a": 1}}})
        self.write(".codex/hooks.json", {"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": "x"}]}})
        self.write(".codex/config.toml", "features = true\n")
        code, text = run_viewer("status", str(self.h.root))
        self.assertEqual(code, 0, text)
        self.assertEqual(run_viewer("install", "--codex", str(self.h.root))[0], 1)

    def test_dev_repo_copy_without_git_is_refused(self):  # installer-new-devrepo-check-needs-git, tests-docs-new-4
        dev = Path(self.tmp.name) / "repo-zip"
        app = dev / "web" / "prototypes" / "visual-viewer"
        app.mkdir(parents=True)
        for name in viewer.APP_FILES:
            shutil.copyfile(VIEWER / name, app / name)
        for name in ("product-tools", "dev-harness"):
            (dev / name).mkdir()
        (dev / "AGENTS.md").write_text("# dev\n", encoding="utf-8")  # .git 없음: ZIP 내려받기·git archive와 같은 모양
        for argv in (["install", "--both"], ["uninstall", "--both"], ["status"], ["open", "--latest", "--no-browser"]):
            with self.subTest(argv=argv):
                proc = subprocess.run([sys.executable, str(app / "viewer.py"), *argv], capture_output=True, timeout=120,
                                      env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(proc.returncode, 1)
                self.assertIn("개발 레포에서 실행했습니다", proc.stderr.decode("utf-8"))
        self.assertEqual(sorted(p.name for p in dev.iterdir()), ["AGENTS.md", "dev-harness", "product-tools", "web"])
        code, text = run_viewer("install", "--both", str(dev))
        self.assertEqual(code, 1)
        self.assertIn("개발 레포에는 설치하지 않습니다", text)
        empty = Path(self.tmp.name) / "not-a-harness"
        empty.mkdir()
        self.assertEqual(run_viewer("install", "--codex", str(empty))[0], 1)
        self.assertEqual(list(empty.iterdir()), [])
        self.assertEqual(run_viewer("install", str(self.h.root))[0], 1)

    def test_baseline_on_every_install_and_status_is_honest(self):  # baseline-reinstall, status-unbuilt
        before = self.h.add("refrigerator")
        code, text = run_viewer("install", "--claude", str(self.h.root))
        self.assertIn(before.name, text)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual((report["view_built"], report["baseline_only"], report["up_to_date"], report["last_built"]), (False, True, False, None))
        paths = hook.Paths(str(self.h.root))
        with mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": ""}), mock.patch.object(hook, "open_browser") as opened:
            self.assertFalse(hook.run({"session_id": "a"}, "claude", paths)["changed"])
            built = self.h.add("microwave")
            self.assertTrue(hook.run({"session_id": "a"}, "claude", paths)["opened_browser"])
            run_viewer("uninstall", "--claude", str(self.h.root))
            while_off = self.h.add("dishwasher")
            code, text = run_viewer("install", "--claude", str(self.h.root))
            self.assertIn(while_off.name, text)
            self.assertFalse(hook.run({"session_id": "new-session"}, "claude", paths)["changed"])
            self.assertEqual(opened.call_count, 1)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual((report["view_built"], report["up_to_date"], report["last_built"], report["latest_export"]),
                         (True, False, built.name, while_off.name))
        self.assertTrue(report["claude"]["registered"] and report["claude"]["files_match_command"])

    def test_manual_no_browser_open_does_not_hide_late_web_payload_from_codex(self):
        for old_state in ({}, {"web_delivery": "verified_binding"}):
            with self.subTest(old_state=old_state):
                export = self.h.add("microwave")
                expected = json.loads(export.read_bytes())["turns"][-1]["web_binding"]
                path = next(p for p in (self.h.root / "runtime-data/web-deliveries").glob("web-*.json")
                            if json.loads(p.read_bytes())["binding"] == expected)
                raw = path.read_bytes()
                path.unlink()
                paths = hook.Paths(str(self.h.root))
                hook.write_state(paths, dict(old_state))
                code, text = run_viewer("open", "--latest", "--no-browser", str(self.h.root))
                self.assertEqual(code, 0, text)
                self.assertFalse(Path(paths.marker).exists())
                path.write_bytes(raw)
                with mock.patch.object(hook, "open_browser", return_value=False):
                    self.assertTrue(hook.run({"session_id": "late-manual"}, "codex", paths)["changed"])
                self.assertEqual(self.h.state()["web_delivery"], "verified_binding")

    def test_open_latest_older_export_and_errors(self):  # side notes: open --export older, wrong-shape insights
        older = self.h.add("refrigerator")
        newest = self.h.add("microwave")
        run_viewer("install", "--both", str(self.h.root))
        with mock.patch("webbrowser.open") as browser:
            code, text = run_viewer("open", "--latest", "--no-browser", str(self.h.root))
            browser.assert_not_called()
        self.assertEqual((code, json.loads(text)["export"]), (0, newest.name))
        self.assertTrue(json.loads(run_viewer("status", str(self.h.root))[1])["up_to_date"])
        code, text = run_viewer("open", "--export", str(older), "--no-browser", str(self.h.root))
        self.assertEqual(code, 0, text)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual((report["last_built"], report["up_to_date"]), (older.name, False))
        self.assertEqual(self.h.state()["last_export"], newest.name)
        self.assertFalse(Path(hook.Paths(str(self.h.root)).marker).exists())
        with mock.patch.object(hook, "open_browser", return_value=False):
            restored = hook.run({"session_id": "after-history"}, "codex", hook.Paths(str(self.h.root)))
        self.assertTrue(restored["changed"])
        self.assertEqual(restored["export"], newest.name)
        self.h.insights("insights-bad.json", {"session_id": export_of("microwave")["session_id"], "groups": "not-a-list"})
        code, text = run_viewer("open", "--latest", "--no-browser", str(self.h.root))
        self.assertEqual(code, 0, text)
        self.assertEqual(json.loads(text)["insights"], "invalid")
        (self.h.exports / "export-zz.json").write_text("{", encoding="utf-8")
        os.utime(self.h.exports / "export-zz.json", (time.time() + 100, time.time() + 100))
        code, text = run_viewer("open", "--latest", "--no-browser", str(self.h.root))
        self.assertEqual(code, 1)
        self.assertIn("화면을 만들지 못했습니다", text)
        self.assertNotIn("Traceback", text)
        self.assertEqual(run_viewer("uninstall", "--both", str(self.h.root))[0], 0)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertFalse(report["claude"]["registered"] or report["codex"]["registered"])

    def test_codex_feature_flag_precedence(self):  # codex-hook-04, installer-new-codex-flag-precedence
        home = Path(self.tmp.name) / "codexhome"
        home.mkdir()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(home)}):
            (home / "config.toml").write_text("[features]\nhooks = false\n", encoding="utf-8")
            self.assertTrue(viewer.codex_hooks_disabled(self.h.root))
            self.assertIn("hooks = false", run_viewer("install", "--codex", str(self.h.root))[1])
            report = json.loads(run_viewer("status", str(self.h.root))[1])
            self.assertTrue(report["codex_hooks_disabled"])
            self.assertEqual([layer["hooks"] for layer in report["codex_features"]], [None, False])
            self.write(".codex/config.toml", "[features]\nhooks = true\n")  # 프로젝트가 사용자 설정보다 우선
            self.assertFalse(viewer.codex_hooks_disabled(self.h.root))
            self.assertNotIn("hooks = false", run_viewer("install", "--codex", str(self.h.root))[1])
            (home / "config.toml").write_text("[features]\ncodex_hooks = true\n", encoding="utf-8")
            self.write(".codex/config.toml", "[some_tool]\nhooks = false\n")
            self.assertFalse(viewer.codex_hooks_disabled(self.h.root))
            self.write(".codex/config.toml", "[features]\nhooks = false\n")
            self.assertTrue(viewer.codex_hooks_disabled(self.h.root))

    def test_status_reports_cli_versions_against_tested_list(self):  # round 5 auto-update
        run_viewer("install", "--both", str(self.h.root))
        tested = {name: versions[0] for name, versions in viewer.TESTED_VERSIONS.items()}
        with mock.patch.object(viewer, "cli_version", side_effect=lambda name: tested[name]):
            report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual((report["cli_versions"], report["version_warnings"]), (tested, []))
        with mock.patch.object(viewer, "cli_version", side_effect=lambda name: {"codex": "9.9.9", "claude": None}[name]):
            report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertEqual(len(report["version_warnings"]), 1)
        self.assertIn("codex 9.9.9", report["version_warnings"][0])
        self.assertIn("selftest", report["version_warnings"][0])
        with mock.patch.object(viewer.shutil, "which", return_value=None):
            self.assertIsNone(viewer.cli_version("codex"))

    def test_selftest_runs_registered_commands_in_a_temp_copy(self):  # round 5 auto-update
        if not shutil.which("uv"):
            self.skipTest("uv not on PATH: the registered commands run through uv")
        self.assertEqual(run_viewer("selftest", str(self.h.root))[0], 1)  # 아직 등록 전
        real = self.h.add("microwave")
        run_viewer("install", "--both", str(self.h.root))
        state_before = (self.h.out / ".hook-state.json").read_bytes()
        code, text = run_viewer("selftest", str(self.h.root))
        report = json.loads(text)
        self.assertEqual(code, 0, text)
        ran = [r for r in report["results"] if r["result"] != "skip"]
        self.assertTrue(ran)
        self.assertTrue(all(r["result"] == "pass" and r["exit"] == 0 and r["output_bytes"] == 0 and r["view_rebuilt"] for r in ran))
        self.assertEqual({r["cli"] for r in ran}, {"claude", "codex"})
        for r in report["results"]:
            if r["result"] == "skip":
                self.assertEqual(r["reason"], "이 PC에 없는 셸")
        self.assertEqual((self.h.out / ".hook-state.json").read_bytes(), state_before)  # 실제 상태·화면은 그대로
        self.assertFalse((self.h.out / "view-data.js").exists())
        self.assertEqual([p.name for p in self.h.exports.iterdir()], [real.name])
        app = self.h.root / "web/prototypes/visual-viewer"
        (app / "build_view.py").write_bytes((app / "build_view.py").read_bytes() + b"\n# changed after install\n")
        code, text = run_viewer("selftest", "--codex", str(self.h.root))
        self.assertEqual(code, 1)
        failed = [r for r in json.loads(text)["results"] if r["result"] == "fail"]
        self.assertTrue(failed)
        self.assertTrue(all("build_view.py가 설치 때와 다릅니다" in r["reason"] for r in failed))

    def test_outputs_stay_in_ignored_runtime_data(self):
        self.assertEqual(Path(hook.Paths(str(self.h.root)).out).relative_to(self.h.root).parts[0], "runtime-data")
        ignored = (VIEWER / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("view-data.js", "report-*.html", "insights-*.json", "*.tmp"):
            self.assertIn(pattern, ignored.splitlines())
        self.assertIn("runtime-data/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
