"""Agent office observer (web/prototypes/agent-office): mapping, privacy, robustness, read-only DB, installer.

No test opens a browser, starts Claude Code or Codex, or calls a model. observe.py runs as a subprocess with synthetic
hook payloads inside a temporary harness layout.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "web" / "prototypes" / "agent-office"
SECRET = "AGENT-OFFICE-SECRET"


def load_office():
    spec = importlib.util.spec_from_file_location("agent_office_cli", APP / "office.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


office = load_office()


class Harness:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agent-office-test-")
        self.root = Path(self.tmp.name) / "harness"
        app = self.root / "web" / "prototypes" / "agent-office"
        app.mkdir(parents=True)
        shutil.copyfile(APP / "observe.py", app / "observe.py")
        (self.root / ".claude").mkdir()
        (self.root / "product-install.json").write_text('{"format": "portable-product-install-v1"}', encoding="utf-8")
        self.out = self.root / "runtime-data" / "agent-office"

    def run(self, payload, raw=None):
        data = raw if raw is not None else json.dumps(payload).encode("utf-8")
        return subprocess.run([sys.executable, "-I", "-B", str(self.root / "web/prototypes/agent-office/observe.py"), "claude"],
                              input=data, capture_output=True, timeout=60)

    def events(self):
        path = self.out / "events.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

    def all_text(self):
        return "".join(p.read_text(encoding="utf-8", errors="replace") for p in self.out.glob("*") if p.is_file())

    def make_db(self):
        db = self.root / "runtime-data" / "product.sqlite"
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db)
        con.executescript("""
            CREATE TABLE product_workflows(research_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, budget_seconds INTEGER NOT NULL,
                research_stopped_at TEXT, finished_at TEXT, checkpoint TEXT);
            CREATE TABLE product_workflow_events(research_id TEXT NOT NULL, event_key TEXT NOT NULL, kind TEXT NOT NULL,
                observed_at TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(research_id,event_key));
            CREATE TABLE conversation_requests(session_id TEXT NOT NULL, request_key TEXT NOT NULL, payload TEXT NOT NULL,
                turn_id TEXT, response TEXT, PRIMARY KEY(session_id,request_key));
            CREATE TABLE turns(turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, request_key TEXT NOT NULL, input_json TEXT NOT NULL,
                context_hash TEXT NOT NULL, dataset_hash TEXT NOT NULL, code_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                valid INTEGER NOT NULL DEFAULT 1, revision_count INTEGER NOT NULL DEFAULT 0, result_version INTEGER NOT NULL DEFAULT 0,
                invalidation_reason TEXT, created_at TEXT NOT NULL);
            CREATE TABLE results(turn_id TEXT NOT NULL, result_key TEXT NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL,
                result_version INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(turn_id,result_key));
            CREATE TABLE evidence_deliveries(turn_id TEXT NOT NULL, binding TEXT NOT NULL, delivery_key TEXT NOT NULL, source_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(turn_id,binding,delivery_key,source_id));
        """)
        con.execute("INSERT INTO product_workflows VALUES('R1','2026-10-13T12:00:00+00:00',1800,NULL,NULL,NULL)")
        con.execute("INSERT INTO product_workflow_events VALUES('R1','e1','research_plan','2026-10-13T12:00:05+00:00',?)",
                    (json.dumps({"data": {"product_name": "합성 시험 전자레인지", "coverage": [], "source_plan": []}}),))
        con.execute("INSERT INTO product_workflow_events VALUES('R1','e2','source_scan','2026-10-13T12:01:00+00:00',?)",
                    (json.dumps({"data": {"source_url": f"https://reviews.example/item?q={SECRET}", "page_label": "후기 1쪽",
                                          "status": "observed", "reviews": [{"x": 1}, {"x": 2}], "reason": SECRET}}),))
        con.execute("INSERT INTO conversation_requests VALUES('S1','K1',?,'T1',?)",
                    (json.dumps({"question": "합성 시험 질문입니다"}), json.dumps({"status": "research_required"})))
        con.execute("INSERT INTO turns VALUES('T1','S1','K1','{}','c','d','e','completed',1,1,2,NULL,'2026-10-13T12:05:00+00:00')")
        con.execute("INSERT INTO results VALUES('T1','k',?,'h',1,'2026-10-13T12:05:01+00:00')", (SECRET,))
        con.execute("INSERT INTO evidence_deliveries VALUES('T1','b','d1','src-1','a','2026-10-13T12:02:00+00:00')")
        con.commit()
        con.close()
        return db

    def close(self):
        self.tmp.cleanup()


def pre(tool, tool_input, **extra):
    return {"hook_event_name": "PreToolUse", "session_id": "S1", "tool_name": tool, "tool_input": tool_input, "tool_use_id": "toolu_1", **extra}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.close()

    def test_skill_operation_from_command_path_without_command_text(self):
        command = f"uv run python .claude/skills/needs-structuring/scripts/run.py select_evidence --input {SECRET}.json"
        r1 = self.h.run(pre("Bash", {"command": command, "description": SECRET}))
        r2 = self.h.run({"hook_event_name": "PostToolUse", "session_id": "S1", "tool_name": "Bash", "tool_use_id": "toolu_1",
                         "tool_input": {"command": command}, "tool_response": {"stdout": json.dumps({"ok": True, "data": SECRET})},
                         "duration_ms": 812})
        for r in (r1, r2):
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
        a, b = self.h.events()
        self.assertEqual((a["kind"], a["node"], a["op"], a["phase"], a["basis"]),
                         ("skill_op", "needs-structuring", "select_evidence", "start", "command_based_mapping"))
        self.assertEqual((b["phase"], b["detail"]["duration_ms"], b["call"]), ("end", 812.0, "toolu_1"))
        self.assertIn("command", a["input_keys"])
        self.assertNotIn(SECRET, self.h.all_text())

    def test_failed_operation_keeps_only_the_error_code(self):
        self.h.run({"hook_event_name": "PostToolUse", "tool_name": "PowerShell", "session_id": "S1",
                    "tool_input": {"command": r"uv run python .claude\skills\review-and-revise\scripts\run.py save_and_export --input x"},
                    "tool_response": {"stdout": json.dumps({"ok": False, "error": "invalid_input", "message": SECRET})}})
        e = self.h.events()[0]
        self.assertEqual((e["node"], e["op"], e["phase"], e["detail"]["error"]), ("review-and-revise", "save_and_export", "fail", "invalid_input"))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_unknown_operation_and_plain_shell(self):
        self.h.run(pre("Bash", {"command": "python skills/concept-writing/scripts/run.py make_it_up --input x"}))
        self.h.run(pre("Bash", {"command": f"echo {SECRET}"}))
        a, b = self.h.events()
        self.assertEqual((a["node"], a["op"]), ("concept-writing", "unknown_operation"))
        self.assertEqual((b["kind"], b["node"], b["op"], b["detail"]["programs"]), ("shell", "main", None, ["echo"]))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_program_names_and_file_areas_without_names(self):
        self.h.run(pre("Bash", {"command": f"uv run python product-doctor.py && ls {SECRET} | {SECRET}-tool --x"}))
        self.h.run(pre("PowerShell", {"command": f"Get-ChildItem C:\\{SECRET}; Remove-Item .\\runtime-data\\{SECRET}.json"}))
        self.h.run(pre("Write", {"file_path": f"runtime-data/{SECRET}.json", "content": SECRET}, cwd=str(self.h.root)))
        self.h.run(pre("Read", {"file_path": str(self.h.root / ".claude/skills/review-and-revise/references/payload.md")}))
        self.h.run(pre("Grep", {"pattern": SECRET, "path": str(self.h.root / "docs")}))
        self.h.run(pre("Edit", {"file_path": f"D:/{SECRET}/x.py", "old_string": SECRET, "new_string": SECRET}))
        a, b, w, r, g, e = self.h.events()
        self.assertEqual(a["detail"]["programs"], ["product_doctor", "ls", "other"])
        self.assertEqual(b["detail"]["programs"], ["get-childitem", "remove-item"])
        self.assertEqual((w["kind"], w["detail"]), ("file", {"area": "runtime"}))
        self.assertEqual(r["detail"], {"area": "skills", "skill": "review-and-revise"})
        self.assertEqual((g["detail"], e["detail"]), ({"area": "docs"}, {"area": "outside"}))
        labels = [office.label_of(x) for x in (a, b, w, r, g, e)]
        self.assertEqual(labels, ["명령 실행 · 설치 점검, 파일 목록 보기", "명령 실행 · 파일 목록 보기, 파일 지우기", "파일 쓰기 · 작업 기록",
                                  "파일 읽기 · 검토·수정 참고 문서", "내용 찾기 · 문서", "파일 고치기 · 하네스 밖"])
        self.assertNotIn(SECRET, self.h.all_text())

    def test_delegation_and_subagent_events(self):
        self.h.run(pre("Agent", {"subagent_type": "product-official-researcher", "prompt": SECRET, "description": SECRET}))
        self.h.run(pre("Task", {"subagent_type": "Explore", "prompt": SECRET}))
        self.h.run({"hook_event_name": "SubagentStart", "session_id": "S1", "agent_id": "a1", "agent_type": "product-official-researcher"})
        self.h.run(pre("WebFetch", {"url": f"https://www.lge.co.kr/support/{SECRET}?q={SECRET}", "prompt": SECRET},
                       agent_id="a1", agent_type="product-official-researcher"))
        self.h.run(pre("WebSearch", {"query": SECRET}, agent_type="product-review-researcher"))  # no agent_id: main (claude --agent)
        self.h.run({"hook_event_name": "SubagentStop", "session_id": "S1", "agent_id": "a1", "agent_type": "product-official-researcher",
                    "last_assistant_message": SECRET})
        d1, d2, start, fetch, search, stop = self.h.events()
        self.assertEqual((d1["kind"], d1["node"], d1["actor"]), ("delegate", "product_official_researcher", "main"))
        self.assertEqual((d2["node"], d2["detail"]["subagent_type"]), ("unknown_subagent", "Explore"))
        self.assertEqual((start["kind"], start["node"], start["phase"]), ("subagent", "product_official_researcher", "start"))
        self.assertEqual((fetch["kind"], fetch["actor"], fetch["detail"]["host"]), ("web", "product_official_researcher", "www.lge.co.kr"))
        self.assertEqual((search["actor"], search["detail"]), ("main", {}))
        self.assertEqual((stop["node"], stop["phase"]), ("product_official_researcher", "end"))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_background_delegation_as_seen_in_claude_code_2_1_289(self):
        role = {"agent_id": "a08e55b03b360a951", "agent_type": "product-evidence-reviewer"}
        self.h.run(pre("Agent", {"subagent_type": "product-evidence-reviewer", "prompt": SECRET, "description": SECRET}))
        self.h.run({"hook_event_name": "SubagentStart", "session_id": "S1", **role})
        self.h.run({"hook_event_name": "PostToolUse", "session_id": "S1", "tool_name": "Agent", "tool_use_id": "toolu_1",
                    "tool_input": {"subagent_type": "product-evidence-reviewer", "prompt": SECRET}, "duration_ms": 59,
                    "tool_response": {"status": "async_launched", "isAsync": True, "agentId": "a08e55b03b360a951",
                                      "prompt": SECRET, "outputFile": f"C:/{SECRET}.output"}})
        self.h.run(pre("Read", {"file_path": "README.md", "limit": 15}, cwd=str(self.h.root), **role))
        self.h.run(pre("SubagentHandback", {"message": SECRET}, **role))
        self.h.run({"hook_event_name": "SubagentStop", "session_id": "S1", **role, "last_assistant_message": SECRET})
        self.h.run({"hook_event_name": "UserPromptSubmit", "session_id": "S1",
                    "prompt": f'Another Claude session sent a message: <agent-message from="a08e55b03b360a951"> {SECRET}'})
        self.h.run({"hook_event_name": "UserPromptSubmit", "session_id": "S1", "prompt": f"<task-notification> {SECRET}"})
        self.h.run({"hook_event_name": "SubagentStop", "session_id": "S1", "agent_id": "ab80", "agent_type": "session-title",
                    "last_assistant_message": SECRET})
        events = self.h.events()
        launch, start, ack, read, handback, stop, delivered, notice, helper = events
        self.assertEqual((ack["kind"], ack["detail"]["background"], ack["detail"]["response_status"], ack["detail"]["launched_agent_id"]),
                         ("delegate", True, "async_launched", "a08e55b03b360a951"))
        self.assertEqual((read["actor"], read["detail"]), ("product_evidence_reviewer", {"area": "harness"}))
        self.assertEqual((handback["kind"], handback["node"]), ("handback", "product_evidence_reviewer"))
        self.assertEqual((delivered["kind"], delivered["detail"]["from_agent_id"]), ("handback_delivered", "a08e55b03b360a951"))
        self.assertEqual((notice["kind"], helper["node"], helper["detail"]["agent_type"]), ("notification", "other_subagent", "session-title"))
        labels = [office.label_of(e) for e in events]
        self.assertEqual(labels[:3], ["독립 근거 검토에 맡김", "독립 근거 검토 시작", "독립 근거 검토 백그라운드로 시작"])
        self.assertEqual(labels[4:], ["독립 근거 검토 결과 돌려줌", "독립 근거 검토 끝", "메인이 연구 결과 받음", "작업 알림 받음",
                                      "Claude Code 보조 작업 끝 (session-title)"])
        trace = office.to_trace(events)["events"]
        self.assertEqual((trace[2]["status"], trace[2]["source"], trace[2]["target"]), ("active", "main", "product_evidence_reviewer"))
        self.assertEqual((trace[4]["source"], trace[4]["target"]), ("product_evidence_reviewer", "main"))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_skill_loading_is_labelled_instruction_loaded(self):
        self.h.run(pre("Skill", {"skill": "feature-comparison", "args": SECRET}))
        self.h.run(pre("Read", {"file_path": r"C:\h\.claude\skills\evidence-retrieval\SKILL.md"}))
        self.h.run(pre("Read", {"file_path": f"C:/private/{SECRET}.txt"}))
        a, b, c = self.h.events()
        self.assertEqual((a["kind"], a["node"], a["basis"]), ("skill_load", "feature-comparison", "instruction_loaded"))
        self.assertEqual((b["kind"], b["node"]), ("skill_load", "evidence-retrieval"))
        self.assertEqual((c["kind"], c["detail"]), ("file", {"area": "outside"}))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_prompts_and_messages_are_not_kept(self):
        self.h.run({"hook_event_name": "UserPromptSubmit", "session_id": "S1", "prompt": SECRET, "prompt_id": "p1"})
        self.h.run({"hook_event_name": "Stop", "session_id": "S1", "last_assistant_message": SECRET})
        self.h.run({"hook_event_name": "SessionEnd", "session_id": "S1", "reason": "prompt_input_exit"})
        a, b, c = self.h.events()
        self.assertEqual((a["kind"], a["prompt_id"], b["kind"], c["detail"]["reason"]), ("request", "p1", "turn_end", "prompt_input_exit"))
        self.assertNotIn(SECRET, self.h.all_text())

    def test_bad_input_never_disturbs_the_session(self):
        for raw in (b"", b"not json", b"[1,2]", b"\xff\xfe\x00", json.dumps({"hook_event_name": 5, "tool_input": "x"}).encode()):
            r = self.h.run(None, raw=raw)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b"", b""))
        self.assertGreaterEqual(len(self.h.events()), 3)
        self.assertTrue((self.h.out / "observe-error.log").is_file())

    def test_live_file_and_read_only_snapshot(self):
        db = self.h.make_db()
        before = hashlib.sha256(db.read_bytes()).hexdigest()
        files_before = sorted(p.name for p in db.parent.iterdir() if p.name.startswith("product.sqlite"))
        self.h.run({"hook_event_name": "PostToolUse", "session_id": "S1", "tool_name": "Bash",
                    "tool_input": {"command": "uv run python .claude/skills/evidence-retrieval/scripts/run.py current_request --input x"},
                    "tool_response": {"stdout": "{\"ok\": true}"}})
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(p.name for p in db.parent.iterdir() if p.name.startswith("product.sqlite")), files_before)  # no -journal/-wal
        text = (self.h.out / "live.js").read_text(encoding="utf-8")
        live = json.loads(text[text.index("window.LGAX_OFFICE_LIVE = ") + len("window.LGAX_OFFICE_LIVE = "):].rstrip().rstrip(";"))
        snap = live["db"]
        self.assertEqual(snap["request"], {"question": "합성 시험 질문입니다", "turn_id": "T1", "status": "research_required"})
        self.assertEqual([e["kind"] for e in snap["workflow_events"]], ["research_plan", "source_scan"])
        scan = snap["workflow_events"][1]
        self.assertEqual((scan["host"], scan["reviews"], scan["status"]), ("reviews.example", 2, "observed"))
        self.assertEqual((snap["turn"]["status"], snap["turn"]["revision_count"], snap["results"], snap["evidence_delivered"]),
                         ("completed", 1, 1, 1))
        self.assertIsNone(snap["evidence_reviews"])  # table missing: unknown, not 0
        self.assertEqual(len(live["events"]), 1)
        self.assertNotIn(SECRET, self.h.all_text())

    def test_missing_database_is_reported_not_created(self):
        self.h.run({"hook_event_name": "SessionStart", "session_id": "S1", "source": "startup"})
        self.assertFalse((self.h.root / "runtime-data" / "product.sqlite").exists())
        text = (self.h.out / "live.js").read_text(encoding="utf-8")
        self.assertIn('"reason": "no_database"', text)

    def test_parallel_hooks_each_leave_one_line(self):
        payloads = [pre("Bash", {"command": f"uv run python .claude/skills/evidence-retrieval/scripts/run.py doctor --input {i}"})
                    for i in range(12)]
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.h.run, payloads))
        self.assertTrue(all(r.returncode == 0 and not r.stdout for r in results))
        events = self.h.events()
        self.assertEqual(len(events), 12)
        self.assertEqual(len({e["id"] for e in events}), 12)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agent-office-install-")
        self.root = Path(self.tmp.name) / "harness"
        (self.root / ".claude").mkdir(parents=True)
        (self.root / "product-install.json").write_text("{}", encoding="utf-8")
        self.settings = self.root / ".claude" / "settings.local.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_keeps_other_hooks_and_is_idempotent(self):
        viewer = {"type": "command", "command": "powershell.exe -NoProfile -EncodedCommand AAAA", "async": True, "timeout": 60}
        original = {"permissions": {"allow": ["Bash(uv run:*)"]},
                    "hooks": {"PostToolUse": [{"matcher": "Bash|PowerShell", "hooks": [viewer]}]}}
        self.settings.write_text(json.dumps(original), encoding="utf-8")
        office.install(self.root)
        office.install(self.root)
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data["permissions"], original["permissions"])
        self.assertEqual(data["hooks"]["PostToolUse"][0], original["hooks"]["PostToolUse"][0])
        for event in office.TOOL_EVENTS + office.OTHER_EVENTS:
            ours = [h for g in data["hooks"][event] for h in g["hooks"] if office.is_ours(h["command"])]
            self.assertEqual(len(ours), 1, event)
            self.assertTrue(ours[0]["async"])
        sha = hashlib.sha256((self.root / "web/prototypes/agent-office/observe.py").read_bytes()).hexdigest()
        self.assertEqual(office.command_sha(ours[0]["command"]), sha)
        status = office.status(self.root)
        self.assertTrue(status["files_match_command"])
        self.assertEqual(status["missing_events"], [])
        office.uninstall(self.root)
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")), original)

    def test_unreadable_settings_stop_without_changes(self):
        for raw in (b"{not json", "{\"a\": 1}".encode("utf-16"), b"[]", b'{"hooks": {"Stop": {}}}'):
            self.settings.write_bytes(raw)
            with self.assertRaises(office.OfficeError):
                office.install(self.root)
            self.assertEqual(self.settings.read_bytes(), raw)
            self.assertFalse((self.root / "web").exists())

    def test_refuses_the_development_repository(self):
        (self.root / "dev-harness").mkdir()
        with self.assertRaises(office.OfficeError):
            office.install(self.root)

    def test_commands_for_both_shells_carry_marker_and_fingerprint(self):
        sha = "ab" * 32
        for windows in (True, False):
            command = office.hook_command(sha, windows=windows)
            self.assertTrue(office.is_ours(command))
            self.assertEqual(office.command_sha(command), sha)

    def test_watch_prints_korean_lines(self):
        import io
        out_dir = self.root / "runtime-data" / "agent-office"
        out_dir.mkdir(parents=True)
        events = [{"ts": "2026-10-13T12:00:00.000Z", "kind": "skill_op", "node": "evidence-retrieval", "op": "retrieve_reviews",
                   "actor": "main", "phase": "end", "basis": "command_based_mapping", "detail": {"duration_ms": 1500}},
                  {"ts": "2026-10-13T12:00:01.000Z", "kind": "delegate", "node": "product_review_researcher", "actor": "main",
                   "phase": "start", "basis": "observed", "detail": {}}]
        lines = [json.dumps(e) for e in events] + ["broken"]
        (out_dir / "events.jsonl").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
        buf = io.StringIO()
        self.assertEqual(office.watch(self.root, once=True, out=buf), 3)
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("[메인] 근거 조회 · retrieve_reviews 끝 (명령으로 추정) · 1.5초"), lines[0])
        self.assertTrue(lines[1].endswith("[메인] 후기 조사·분석에 맡김"), lines[1])

    def test_trace_uses_control_room_fields(self):
        events = [{"id": "1", "ts": "2026-10-13T12:00:00.000Z", "kind": "delegate", "node": "product_review_researcher",
                   "actor": "main", "phase": "start", "basis": "observed"},
                  {"id": "2", "ts": "2026-10-13T12:00:30.500Z", "kind": "delegate", "node": "product_review_researcher",
                   "actor": "main", "phase": "end", "basis": "observed"},
                  {"id": "3", "ts": "2026-10-13T12:00:31.000Z", "kind": "skill_op", "node": "concept-writing", "op": "validate_constraints",
                   "actor": "main", "phase": "fail", "basis": "command_based_mapping"}]
        trace = office.to_trace(events)
        self.assertEqual(trace["mode"], "observed")
        a, b, c = trace["events"]
        for e in (a, b, c):
            self.assertTrue({"id", "at", "kind", "source", "target", "label", "detail", "status"} <= set(e))
        self.assertEqual((a["source"], a["target"], a["status"]), ("main", "product_review_researcher", "active"))
        self.assertEqual((b["source"], b["target"], b["at"]), ("product_review_researcher", "main", 30.5))
        self.assertEqual((c["status"], c["basis"], c["label"]), ("error", "command_based_mapping", "콘셉트 작성 · validate_constraints 실패"))


if __name__ == "__main__":
    unittest.main()
