"""Visual viewer prototype: builder, CLI hook and installer on synthetic v0.7.0 exports.

All exports here are generated at test time through the real product-tools save/export
path, with text marked "[합성 시험 자료]". They are code fixtures, not AI or customer
results. No test opens a browser, runs a business question or calls a model.
"""
import contextlib
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
EXPORTS: dict[str, Path] = {}
_TMP = None


def load(name):
    spec = importlib.util.spec_from_file_location(name, VIEWER / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_view = load("build_view")
hook = load("hook")
viewer = load("viewer")


def completed(conv, store, model, rid, fid):
    bundle = conv.open_request_bundle({"question": f"{SYNTH} {model} 불편 개선 시험", "model_id": model, "user_submitted": True})
    value = bundle["candidate_template"]
    scope = bundle["turn"]["input"]["model_scope"][0]
    result = value["result"]
    result.update(
        status="completed",
        pains=[{"id": "p1", "text": f"{SYNTH} 현재 불편", "source_ids": [rid]}],
        existing_features=[{"id": "f1", "text": f"{SYNTH} 기존 기능", "source_ids": [fid]}],
        remaining_pains=[{"id": "r1", "text": f"{SYNTH} 남은 불편", "source_ids": [rid, fid]}],
        concepts=[{"id": "c1", "text": f"{SYNTH} 제안", "source_ids": [rid, fid], "requirements": [f"{SYNTH} 조건"],
                   "requires_hardware": False, "assumptions": [f"{SYNTH} 효과 미측정"],
                   "implementation_steps": [f"{SYNTH} 1단계 시제품", f"{SYNTH} 2단계 과업 시험"],
                   "validation_plan": {"metric": f"{SYNTH} 과업 시간", "baseline": "현행", "method": "동일 과업 비교",
                                       "success_criterion": "시험 전 합의", "business_value": "가설", "status": "planned_not_measured"}}],
        assumptions=[f"{SYNTH} 코드 시험용"],
        evidence_refs=store.tools.select_evidence(scope, [rid, fid])["evidence_refs"],
        decision_notes=[{"text": f"{SYNTH} 판단 메모", "source_ids": [rid], "basis": "ai_interpretation"}])
    checks = [{"claim_id": c["id"], "source_ids": c["source_ids"], "support_status": "supported", "scope_relation": "current_model",
               "rationale": "code fixture"} for key in ("pains", "existing_features", "remaining_pains", "concepts") for c in result[key]]
    value["assessment"] = {
        "claim_checks": checks,
        "feature_matches": [{"remaining_pain_id": "r1", "pain_id": "p1", "feature_source_ids": [fid], "resolution": "unresolved", "rationale": "fixture"}],
        "concept_links": [{"concept_id": "c1", "remaining_pain_ids": ["r1"], "duplicates_existing": False, "geometry_required": False,
                           "geometry_known": False, "geometry_source_ids": [], "rationale": "fixture"}]}
    saved = conv.save_and_export(value)
    assert saved["save"]["accepted"] and saved["export"], saved
    return saved["export"]["path"]


def held(conv, store):
    bundle = conv.open_request_bundle({"question": f"{SYNTH} 보류 시험", "model_id": "MWJ25E", "user_submitted": True})
    value = bundle["candidate_template"]
    scope = bundle["turn"]["input"]["model_scope"][0]
    value["result"].update(status="held", validation_findings=[f"{SYNTH} 내부 치수 근거 없음"],
                           evidence_refs=store.tools.select_evidence(scope, ["REVIEW-MWJ25E-01"])["evidence_refs"],
                           decision_notes=[{"text": f"{SYNTH} 원문 범위", "source_ids": ["REVIEW-MWJ25E-01"], "basis": "source_fact"},
                                           {"text": f"{SYNTH} 근거 없는 추정", "source_ids": [], "basis": "unverified"}])
    saved = conv.save_and_export(value)
    assert saved["save"]["accepted"] and saved["export"], saved
    return saved["export"]["path"]


def setUpModule():
    global _TMP
    os.environ["LGAX_VIEWER_NO_OPEN"] = "1"
    _TMP = tempfile.TemporaryDirectory(prefix="lgax-viewer-fixtures-")
    work = Path(_TMP.name) / "product"
    for name in ("skills/manifest.json", "agents/product-planning.md"):
        p = work / name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, p)
    store = StateStore(work / "runtime-data/product.sqlite", Dataset(ROOT / "data/business/lg-kitchen-v4"))
    try:
        conv = Conversation(store, work)
        for family, _, model, rid, fid in FAMILIES:
            EXPORTS[family] = work / completed(conv, store, model, rid, fid)
        EXPORTS["held"] = work / held(conv, store)
    finally:
        store.close()
    requests_only = {"session_id": "synthetic-requests-only", "turns": [], "semantic_status": "unverified", "acceptance_ready": False,
                     "usage_summary": {"status": "unknown"},
                     "requests": [{"input": {"question": f"{SYNTH} 조사 보류"}, "turn_id": None, "request_version": 1, "events": [],
                                   "response": None, "research_usage": {"status": "unknown"}}]}
    EXPORTS["requests_only"] = Path(_TMP.name) / "export-synthetic-requests-only.json"
    EXPORTS["requests_only"].write_text(json.dumps(requests_only, ensure_ascii=False), encoding="utf-8")


def tearDownModule():
    _TMP.cleanup()


def read_view(out_dir: Path) -> dict:
    text = (out_dir / "view-data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("window.LGAX_VIEW = ") + len("window.LGAX_VIEW = "):].rstrip().rstrip(";"))


def page(view, pid):
    return next(p for p in view["pages"] if p["id"] == pid)


def blob(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def session_of(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["session_id"]


class Harness:
    """Minimal harness folder: what viewer.py checks for, plus runtime-data/exports."""

    def __init__(self, root: Path):
        self.root = root
        (root / "product-tools").mkdir(parents=True)
        (root / "AGENTS.md").write_text("# 시험용 하네스\n", encoding="utf-8")
        self.exports = root / "runtime-data" / "exports"
        self.exports.mkdir(parents=True)
        self.out = root / "runtime-data" / "visual-viewer"

    def add(self, key: str, name: str | None = None) -> Path:
        dest = self.exports / (name or EXPORTS[key].name)
        shutil.copyfile(EXPORTS[key], dest)
        stamp = time.time() + len(list(self.exports.iterdir()))  # strictly newer than earlier copies
        os.utime(dest, (stamp, stamp))
        return dest

    def state(self) -> dict:
        return json.loads((self.out / ".hook-state.json").read_text(encoding="utf-8"))


def run_viewer(*argv) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = viewer.main(list(argv))
    return code, out.getvalue() + err.getvalue()


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lgax-viewer-test-")
        self.h = Harness(Path(self.tmp.name) / "harness")

    def tearDown(self):
        self.tmp.cleanup()


class BuildViewTests(TempCase):
    def test_three_families_with_steps_plan_and_decision_notes(self):
        for family, label, model, rid, _ in FAMILIES:
            with self.subTest(family=family):
                export = self.h.add(family)
                summary = build_view.generate(export, None, "auto", out_dir=self.h.out)
                self.assertEqual(summary["warnings"], [])
                self.assertEqual(summary["focus"], "dashboard")
                view = read_view(self.h.out)
                self.assertTrue((self.h.out / "index.html").is_file())
                self.assertEqual([p["id"] for p in view["pages"]],
                                 ["overview", "dashboard", "screening", "compare", "concepts", "history", "evidence", "export"])
                self.assertIn(label, view["pages"][0]["title"])
                self.assertIn(label, view["context"]["meta"])
                concepts = blob(page(view, "concepts"))
                self.assertIn("구현 단계 2", concepts)
                self.assertIn("검증 계획 · 실측 전", concepts)
                overview = blob(page(view, "overview"))
                self.assertIn("판단 메모 1개", overview)
                self.assertIn("AI 해석", overview)
                self.assertIn('"D1"', blob(page(view, "evidence")))
                self.assertIn("decision note support and attribution", blob(page(view, "export")))

    def test_held_result_shows_decision_notes_and_overview_focus(self):
        summary = build_view.generate(self.h.add("held"), None, "auto", out_dir=self.h.out)
        self.assertEqual(summary["focus"], "overview")
        overview = blob(page(read_view(self.h.out), "overview"))
        self.assertIn("보류(held)", overview)
        for text in ("판단 메모 2개", "원문 사실", "미확인", "근거 없음", f"{SYNTH} 근거 없는 추정"):
            self.assertIn(text, overview)

    def test_missing_insights_shows_dashboard_notice(self):
        export = self.h.add("refrigerator")
        summary = build_view.generate(export, None, "auto", out_dir=self.h.out)
        self.assertEqual(summary["insights"], "missing")
        first = page(read_view(self.h.out), "dashboard")["blocks"][0]
        self.assertEqual(first["type"], "callout")
        self.assertIn("의견 묶음 화면에는 insights 파일이 필요합니다", first["text"])
        self.assertIn(session_of(export), first["text"])

    def test_matching_insights_draw_groups_and_mismatch_is_ignored(self):
        export = self.h.add("microwave")
        insights = self.h.out / "insights-synthetic.json"
        self.h.out.mkdir(parents=True, exist_ok=True)
        groups = [{"key": "g1", "label": f"{SYNTH} 묶음", "tone": "blue", "source_ids": ["REVIEW-MWJ25E-01"]}]
        insights.write_text(json.dumps({"session_id": session_of(export), "synthetic": True, "groups": groups}, ensure_ascii=False), encoding="utf-8")
        summary = build_view.generate(export, insights, "auto", out_dir=self.h.out)
        self.assertEqual((summary["insights"], summary["warnings"]), ("matched", []))
        dashboard = page(read_view(self.h.out), "dashboard")
        self.assertNotIn("insights 파일이 필요합니다", blob(dashboard))
        self.assertIn('"donut"', blob(dashboard))
        insights.write_text(json.dumps({"session_id": "other-session", "groups": groups}), encoding="utf-8")
        summary = build_view.generate(export, insights, "auto", out_dir=self.h.out)
        self.assertEqual(summary["insights"], "mismatch")
        self.assertEqual(len(summary["warnings"]), 1)
        dashboard = blob(page(read_view(self.h.out), "dashboard"))
        self.assertIn("session_id가 이 export와 달라", dashboard)
        self.assertNotIn('"donut"', dashboard)

    def test_requests_only_export_and_no_absolute_paths(self):
        summary = build_view.generate(self.h.add("requests_only"), None, "auto", out_dir=self.h.out)
        self.assertEqual((summary["pages"], summary["focus"]), (1, "overview"))
        export = self.h.add("dishwasher")
        build_view.generate(export, None, "auto", out_dir=self.h.out)
        text = (self.h.out / "view-data.js").read_text(encoding="utf-8")
        self.assertIn(f"runtime-data/exports/{export.name}", text)
        for private in (str(self.h.root), self.h.root.as_posix(), str(Path.home())):
            self.assertNotIn(private, text)


class HookTests(TempCase):
    def run_hook(self, payload, source=None):
        argv = [source] if source else []
        return hook.run(payload, hook.detect_source(argv, payload), hook.Paths(str(self.h.root)))

    def test_rebuild_only_for_new_export_and_open_once_per_cli_session(self):
        with mock.patch.object(hook, "open_browser") as opened:
            self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["reason"], "export 없음")
            first = self.h.add("refrigerator")
            result = self.run_hook({"session_id": "s1"}, "claude")
            self.assertEqual((result["export"], result["opened_browser"]), (first.name, True))
            self.assertFalse(self.run_hook({"session_id": "s1"}, "claude")["changed"])
            self.h.add("microwave")
            self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["opened_browser"], False)
            codex = self.h.add("dishwasher")
            result = self.run_hook({"session_id": "s1", "turn_id": "t1", "hook_event_name": "PostToolUse"})
            self.assertEqual((result["export"], result["opened_browser"]), (codex.name, True))
            self.assertEqual(opened.call_count, 2)
        state = self.h.state()
        self.assertEqual(state["opened_sessions"], ["claude:s1", "codex:s1"])
        self.assertEqual(state["last_export"], codex.name)
        self.assertEqual(state["insights"], "missing")

    def test_insights_found_by_session_id(self):
        export = self.h.add("held")
        self.h.out.mkdir(parents=True)
        (self.h.out / "insights-a-other.json").write_text(json.dumps({"session_id": "other"}), encoding="utf-8")
        (self.h.out / "insights-b-broken.json").write_text("{broken", encoding="utf-8")
        (self.h.out / "insights-c-match.json").write_text(json.dumps({"session_id": session_of(export), "synthetic": True}), encoding="utf-8")
        self.run_hook({"session_id": "s1"}, "codex")
        self.assertEqual((self.h.state()["insights"], self.h.state()["insights_file"]), ("matched", "insights-c-match.json"))

    def test_broken_export_is_logged_once_then_skipped(self):
        bad = self.h.exports / "export-broken.json"
        bad.write_text("{not json", encoding="utf-8")
        self.assertFalse(self.run_hook({"session_id": "s1"}, "claude")["changed"])
        log = (self.h.out / "hook-error.log").read_text(encoding="utf-8")
        self.assertIn("export-broken.json", log)
        self.assertEqual(self.run_hook({"session_id": "s1"}, "claude")["reason"], "이미 처리한 export")
        self.assertEqual((self.h.out / "hook-error.log").read_text(encoding="utf-8"), log)
        self.assertTrue(self.run_hook({"session_id": "s1"}, "claude")["changed"] is False)
        self.h.add("microwave")
        self.assertTrue(self.run_hook({"session_id": "s1"}, "claude")["changed"])

    def test_source_detection_and_stale_lock(self):
        self.assertEqual(hook.detect_source(["codex"], {}), "codex")
        self.assertEqual(hook.detect_source([], {"turn_id": "t"}), "codex")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": "x"}):
            self.assertEqual(hook.detect_source([], {}), "claude")
        paths = hook.Paths(str(self.h.root))
        os.makedirs(paths.out)
        Path(paths.lock).write_text("1", encoding="ascii")
        old = time.time() - hook.LOCK_STALE_SECONDS - 5
        os.utime(paths.lock, (old, old))
        self.assertTrue(hook.acquire_lock(paths))
        hook.release_lock(paths)
        self.assertFalse(os.path.exists(paths.lock))


class InstalledHookProcessTests(TempCase):
    """Runs the exact installed command (or its Python part) as the CLIs would: stdin JSON, check silence."""

    def setUp(self):
        super().setUp()
        code, text = run_viewer("install", "--both", str(self.h.root))
        self.assertEqual(code, 0, text)
        self.claude = self.command(".claude/settings.local.json")
        self.codex = self.command(".codex/hooks.json")

    def command(self, rel):
        config = json.loads((self.h.root / rel).read_text(encoding="utf-8"))
        return config["hooks"]["PostToolUse"][-1]["hooks"][0]["command"]

    def call(self, argv, payload, cwd, shell=False, env=None):
        stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        environment = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        environment.update(env or {}, LGAX_VIEWER_NO_OPEN="1")
        return subprocess.run(argv, input=stdin, capture_output=True, cwd=cwd, env=environment, shell=shell, timeout=120)

    def python_part(self, source):
        return [sys.executable, "-I", "-B", "-c", viewer.HOOK_CODE[source], source]

    def assertSilentZero(self, proc):
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"", b""))

    def test_python_part_builds_for_claude_and_codex(self):
        self.h.add("refrigerator")
        proc = self.call(self.python_part("claude"), {"session_id": "c1", "tool_name": "Bash"}, Path.home(),
                         env={"CLAUDE_PROJECT_DIR": str(self.h.root)})
        self.assertSilentZero(proc)
        self.assertEqual(self.h.state()["opened_sessions"], ["claude:c1"])
        self.h.add("microwave")
        proc = self.call(self.python_part("codex"), {"session_id": "x1", "turn_id": "t1", "tool_name": "Bash"}, self.h.root)
        self.assertSilentZero(proc)
        self.assertEqual(self.h.state()["opened_sessions"], ["claude:c1", "codex:x1"])
        self.assertTrue((self.h.out / "view-data.js").is_file())

    def test_garbage_input_missing_script_and_errors_stay_silent(self):
        self.h.add("held")
        self.assertSilentZero(self.call(self.python_part("codex"), b"\xff not json", self.h.root))
        self.assertIn("codex:no-session", self.h.state()["opened_sessions"])
        (self.h.exports / "export-zz-broken.json").write_text("{", encoding="utf-8")
        os.utime(self.h.exports / "export-zz-broken.json", (time.time() + 100, time.time() + 100))
        self.assertSilentZero(self.call(self.python_part("codex"), {"session_id": "x"}, self.h.root))
        self.assertIn("export-zz-broken.json", (self.h.out / "hook-error.log").read_text(encoding="utf-8"))
        (self.h.root / "web/prototypes/visual-viewer/hook.py").unlink()
        self.assertSilentZero(self.call(self.python_part("codex"), {"session_id": "x"}, self.h.root))

    @unittest.skipUnless(shutil.which("uv"), "uv not on PATH")
    def test_exact_installed_command_in_available_shells(self):
        shells = [("default", lambda c: c, True)]
        bash = shutil.which("bash")
        if bash and "system32" not in bash.lower():  # Git Bash, not WSL
            shells.append(("bash", lambda c: [bash, "-c", c], False))
        if os.name == "nt" and shutil.which("powershell.exe"):
            shells.append(("powershell", lambda c: ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", c], False))
        for i, (name, wrap, shell) in enumerate(shells):
            with self.subTest(shell=name):
                self.h.add(FAMILIES[i % 3][0], f"export-{name}.json")
                proc = self.call(wrap(self.claude), {"session_id": name}, Path.home(), shell=shell,
                                 env={"CLAUDE_PROJECT_DIR": str(self.h.root)})
                self.assertSilentZero(proc)
                self.assertEqual(self.h.state()["last_export"], f"export-{name}.json")
                self.assertIn(f"claude:{name}", self.h.state()["opened_sessions"])
        self.h.add("held", "export-codex.json")
        self.assertSilentZero(self.call(self.codex, {"session_id": "cx", "turn_id": "t"}, self.h.root, shell=True))
        self.assertIn("codex:cx", self.h.state()["opened_sessions"])


class InstallTests(TempCase):
    old = {"type": "command", "command": "C:/Users/someone/Python314/python.exe -I -S -B C:/Users/someone/h/runtime-data/visual-viewer/hook.py",
           "timeout": 30, "async": True}

    def write(self, rel, value):
        path = self.h.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return path

    def ours(self, config):
        return [h for groups in config.get("hooks", {}).values() for g in groups for h in g["hooks"] if viewer.is_ours(h)]

    def test_claude_merge_keeps_other_settings_replaces_old_entry_and_is_idempotent(self):
        other = {"matcher": "Write", "hooks": [{"type": "command", "command": "echo other"}]}
        path = self.write(".claude/settings.local.json", {"permissions": {"allow": ["Bash(uv run:*)"]},
                                                          "hooks": {"PostToolUse": [other, {"matcher": "Bash", "hooks": [self.old]}],
                                                                    "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}]}})
        for _ in range(2):
            self.assertEqual(run_viewer("install", "--claude", str(self.h.root))[0], 0)
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["permissions"], {"allow": ["Bash(uv run:*)"]})
        self.assertEqual(config["hooks"]["Stop"], [{"hooks": [{"type": "command", "command": "echo stop"}]}])
        self.assertEqual(config["hooks"]["PostToolUse"][0], other)
        ours = self.ours(config)
        self.assertEqual(len(ours), 1)
        self.assertEqual(config["hooks"]["PostToolUse"][-1]["matcher"], "Bash|PowerShell")
        self.assertEqual((ours[0]["async"], ours[0]["timeout"]), (True, 60))
        command = ours[0]["command"]
        for private in (str(self.h.root), self.h.root.as_posix(), "Users", "someone"):
            self.assertNotIn(private, command)
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]", command))
        self.assertIsNone(re.search(r"[$%!`^&|<>\\]", command.split('"')[1]))
        for name in viewer.APP_FILES:
            self.assertEqual((self.h.root / "web/prototypes/visual-viewer" / name).read_bytes(), (VIEWER / name).read_bytes())
        self.assertTrue((self.h.out / "index.html").is_file())

    def test_codex_merge_uninstall_and_config_untouched(self):
        toml = self.write(".codex/config.toml", "[agents]\nenabled = true\n")
        before = toml.read_bytes()
        other = {"matcher": "apply_patch", "hooks": [{"type": "command", "command": "echo keep"}]}
        path = self.write(".codex/hooks.json", {"hooks": {"PostToolUse": [other]}})
        self.assertEqual(run_viewer("install", "--codex", str(self.h.root))[0], 0)
        config = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(config["hooks"]["PostToolUse"][0], other)
        self.assertEqual(config["hooks"]["PostToolUse"][1]["matcher"], "Bash")
        self.assertTrue(config["hooks"]["PostToolUse"][1]["hooks"][0]["command"].endswith(" codex"))
        self.assertEqual(run_viewer("uninstall", "--codex", str(self.h.root))[0], 0)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"hooks": {"PostToolUse": [other]}})
        path.unlink()
        run_viewer("install", "--codex", str(self.h.root))
        run_viewer("uninstall", "--codex", str(self.h.root))
        self.assertFalse(path.exists())
        self.assertEqual(toml.read_bytes(), before)
        self.assertTrue((self.h.root / "web/prototypes/visual-viewer/hook.py").is_file())

    def test_invalid_config_and_non_harness_are_refused_without_changes(self):
        path = self.write(".claude/settings.local.json", "{broken")
        code, text = run_viewer("install", "--claude", str(self.h.root))
        self.assertEqual(code, 1)
        self.assertIn("JSON", text)
        self.assertEqual(path.read_text(encoding="utf-8"), "{broken")
        self.assertFalse((self.h.root / "web").exists())
        empty = Path(self.tmp.name) / "not-a-harness"
        empty.mkdir()
        self.assertEqual(run_viewer("install", "--codex", str(empty))[0], 1)
        self.assertEqual(list(empty.iterdir()), [])
        self.assertEqual(run_viewer("install", str(self.h.root))[0], 1)

    def test_baseline_open_latest_and_status(self):
        before = self.h.add("refrigerator")
        run_viewer("install", "--both", str(self.h.root))
        self.assertEqual(self.h.state()["last_export"], before.name)
        with mock.patch.object(hook, "open_browser") as opened:
            self.assertFalse(hook.run({"session_id": "s"}, "claude", hook.Paths(str(self.h.root)))["changed"])
            opened.assert_not_called()
        self.assertFalse((self.h.out / "view-data.js").exists())
        with mock.patch("webbrowser.open") as browser:
            code, text = run_viewer("open", "--latest", "--no-browser", str(self.h.root))
            browser.assert_not_called()
        self.assertEqual(code, 0, text)
        self.assertEqual(json.loads(text)["export"], before.name)
        self.assertTrue((self.h.out / "view-data.js").is_file())
        code, text = run_viewer("status", str(self.h.root))
        report = json.loads(text)
        self.assertTrue(report["claude"]["registered"] and report["codex"]["registered"] and report["up_to_date"])
        self.assertTrue(all(report["app_files"].values()))
        self.assertEqual(run_viewer("uninstall", "--both", str(self.h.root))[0], 0)
        report = json.loads(run_viewer("status", str(self.h.root))[1])
        self.assertFalse(report["claude"]["registered"] or report["codex"]["registered"])

    def test_outputs_stay_in_ignored_runtime_data(self):
        self.assertEqual(Path(hook.Paths(str(self.h.root)).out).relative_to(self.h.root).parts[0], "runtime-data")
        ignored = (VIEWER / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("view-data.js", "report-*.html", "insights-*.json", "*.tmp"):
            self.assertIn(pattern, ignored.splitlines())
        self.assertIn("runtime-data/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
