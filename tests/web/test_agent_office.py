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
                result_version INTEGER NOT NULL, created_at TEXT NOT NULL, validation_json TEXT NOT NULL DEFAULT '{}',
                PRIMARY KEY(turn_id,result_key));
            CREATE TABLE evidence_deliveries(turn_id TEXT NOT NULL, binding TEXT NOT NULL, delivery_key TEXT NOT NULL, source_id TEXT NOT NULL,
                source_sha256 TEXT NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(turn_id,binding,delivery_key,source_id));
        """)
        con.execute("INSERT INTO product_workflows VALUES('R1','2026-10-13T12:00:00+00:00',1800,NULL,NULL,NULL)")
        con.execute("INSERT INTO product_workflow_events VALUES('R1','e1','research_plan','2026-10-13T12:00:05+00:00',?)",
                    (json.dumps({"data": {"product_name": "합성 시험 전자레인지", "coverage": [], "source_plan": []}}),))
        con.execute("INSERT INTO product_workflow_events VALUES('R1','e2','source_scan','2026-10-13T12:01:00+00:00',?)",
                    (json.dumps({"data": {"source_url": f"https://reviews.example/item?q={SECRET}", "page_label": "후기 1쪽",
                                          "status": "observed", "reviews": [{"x": 1}, {"x": 2}], "reason": SECRET}}),))
        research = "research-" + hashlib.sha256(b'["S1","K1"]').hexdigest()
        con.execute("UPDATE product_workflows SET research_id=?", (research,))
        con.execute("UPDATE product_workflow_events SET research_id=?", (research,))
        con.execute("INSERT INTO conversation_requests VALUES('S1','K1',?,'T1',?)",
                    (json.dumps({"question": SECRET}), json.dumps({"status": "research_required"})))
        con.execute("INSERT INTO turns VALUES('T1','S1','K1','{}','c','d','e','completed',1,1,2,NULL,'2026-10-13T12:05:00+00:00')")
        candidate = {"status": "held", "pains": [{"text": SECRET}, {"text": SECRET}], "existing_features": [],
                     "remaining_pains": [{"text": SECRET}], "concepts": [{"text": SECRET}], "evidence_refs": [{"quote": SECRET}] * 3}
        check = {"contract_valid": True, "structural_valid": True, "acceptance_ready": False, "semantic_status": "unverified",
                 "note": SECRET}
        con.execute("INSERT INTO results VALUES('T1','k',?,'h',1,'2026-10-13T12:05:01+00:00',?)",
                    (json.dumps(candidate), json.dumps(check)))
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

    def test_canonical_operation_names_and_interrupted_stop_are_distinct(self):
        import ast
        parsed = ast.parse((ROOT / "product-tools/cli.py").read_text(encoding="utf-8"))
        choices = next(ast.literal_eval(k.value) for node in ast.walk(parsed) if isinstance(node, ast.Call)
                       and any(isinstance(a, ast.Constant) and a.value == "operation" for a in node.args)
                       for k in node.keywords if k.arg == "choices")
        spec = importlib.util.spec_from_file_location("office_observer_check", APP / "observe.py")
        observer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(observer)
        self.assertEqual(set(choices), observer.CLI_OPS)
        event = observer.classify({"hook_event_name": "Stop", "session_id": "S1", "is_interrupt": True})
        self.assertEqual(event["kind"], "turn_cancelled")

    def test_other_latest_request_and_workflow_are_not_joined_to_this_turn(self):
        db = self.h.make_db()
        con = sqlite3.connect(db)
        con.execute("INSERT INTO conversation_requests VALUES('other','K2',?,NULL,?)",
                    (json.dumps({"question": SECRET}), json.dumps({"status": "held"})))
        con.execute("INSERT INTO product_workflows VALUES('other-research','2026-10-14T12:00:00+00:00',1800,NULL,NULL,NULL)")
        con.commit()
        con.close()
        self.h.run({"hook_event_name": "SessionStart", "session_id": "other-native"})
        raw = (self.h.out / "live.js").read_text(encoding="utf-8")
        value = json.loads(raw[raw.index("window.LGAX_OFFICE_LIVE = ") + len("window.LGAX_OFFICE_LIVE = "):].rstrip().rstrip(";"))
        self.assertEqual(value["db"]["binding"], {"session_id": "S1", "turn_id": "T1", "request_key": "K1"})
        self.assertNotEqual(value["db"]["workflow"]["research_id"], "other-research")
        self.assertNotIn(SECRET, self.h.all_text())

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

    def test_other_skill_operation_and_save_outcome(self):
        self.h.run(pre("Bash", {"command": "uv run python .claude/skills/evidence-retrieval/scripts/run.py fetch_web_page --input x"}))
        save = "uv run python .claude/skills/review-and-revise/scripts/run.py save_and_export --input x"
        response = {"ok": True, "result": {"save": {"accepted": False, "reason": {"code": "claim_unsupported", "message": SECRET},
                                                  "turn": {"status": "needs_revision", "result_version": 1, "revision_count": 0}},
                                         "delivery_ready": False, "export": None}}
        self.h.run({"hook_event_name": "PostToolUse", "session_id": "S1", "tool_name": "Bash", "tool_input": {"command": save},
                    "tool_response": {"stdout": json.dumps(response)}})
        accepted = {"ok": True, "result": {"save": {"accepted": True, "reason": None, "turn": {"status": "completed"}}}}
        self.h.run({"hook_event_name": "PostToolUse", "session_id": "S1", "tool_name": "Bash", "tool_input": {"command": save},
                    "tool_response": {"stdout": json.dumps(accepted)}})
        a, b, c = self.h.events()
        self.assertEqual((a["node"], a["op"], a["detail"]), ("evidence-retrieval", "fetch_web_page", {"other_skill_operation": True}))
        self.assertEqual(b["detail"], {"accepted": False, "reason": "claim_unsupported", "turn_status": "needs_revision",
                                       "result_version": 1, "revision_count": 0})
        self.assertEqual(office.label_of(b), "검토·수정 · save_and_export 거절됨 (claim_unsupported, needs_revision)")
        self.assertEqual(office.label_of(c), "검토·수정 · save_and_export 승인됨 (completed)")
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
        self.assertEqual(snap["request"], {"turn_id": "T1", "request_key": "K1", "status": "research_required"})
        self.assertEqual(snap["binding_status"], "unverified_native_session")
        self.assertEqual([e["kind"] for e in snap["workflow_events"]], ["research_plan", "source_scan"])
        scan = snap["workflow_events"][1]
        self.assertEqual((scan["host"], scan["reviews"], scan["status"]), ("reviews.example", 2, "observed"))
        self.assertEqual((snap["turn"]["status"], snap["turn"]["revision_count"], snap["results"], snap["evidence_delivered"]),
                         ("completed", 1, 1, 1))
        self.assertIsNone(snap["evidence_reviews"])  # table missing: unknown, not 0
        self.assertEqual(snap["candidates"], [{
            "result_version": 1, "created_at": "2026-10-13T12:05:01+00:00", "status": "held",
            "counts": {"pains": 2, "existing_features": 0, "remaining_pains": 1, "concepts": 1, "evidence_refs": 3},
            "contract_valid": True, "structural_valid": True, "acceptance_ready": False, "semantic_status": "unverified"}])
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

    def test_install_puts_the_page_next_to_the_records(self):
        office.install(self.root)
        page = self.root / "runtime-data" / "agent-office" / "index.html"
        if not (APP / "index.html").is_file():
            self.assertFalse(page.exists())
            return
        self.assertEqual(page.read_bytes(), (APP / "index.html").read_bytes())
        self.assertTrue((self.root / "web/prototypes/agent-office/index.html").is_file())
        self.assertEqual(office.status(self.root)["page"], str(page))
        self.assertEqual(office.open_page(self.root, launch=False), f"사무실 화면: {page.as_uri()}")

    def test_open_without_install_explains(self):
        with self.assertRaises(office.OfficeError):
            office.open_page(self.root, launch=False)

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


MAIN_ID = "01a20000-0000-7000-8000-000000000001"
CHILD_ID = "01a20000-0000-7000-8000-000000000002"


def codex_records(harness, main=MAIN_ID, child=CHILD_ID):
    """A Codex 0.162-style main thread and one research-agent thread (synthetic; secrets must not leak)."""
    t = 1792000000000

    def at(ms):
        return {"timestamp": f"2026-10-14T03:00:{ms // 1000:02d}.{ms % 1000:03d}Z"}

    def item(ms, body, took=1000):
        return {**at(ms + took), "type": "event_msg", "payload": {"type": "item_completed", "thread_id": main, "turn_id": "turn-1",
                "started_at_ms": t + ms, "completed_at_ms": t + ms + took, "item": body}}

    run = ".claude/skills/{}/scripts/run.py {} --input runtime-data/" + SECRET + ".json"
    save_out = json.dumps({"ok": True, "result": {"save": {"accepted": True, "turn": {"status": "completed", "result_version": 1, "revision_count": 0}}}})
    main_lines = [
        {**at(0), "type": "session_meta", "payload": {"id": main, "cwd": str(harness), "cli_version": "0.162.1", "source": "cli",
                                                    "base_instructions": SECRET}},
        {**at(1), "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}},
        item(1000, {"type": "UserMessage", "id": "u1", "content": [{"type": "text", "text": SECRET}]}, 1),
        {**at(2000), "type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "call_id": "call_exec1", "input": SECRET}},
        item(2100, {"type": "CommandExecution", "id": "c1", "command": ["pwsh", "-Command", "Get-Content .claude/skills/evidence-retrieval/SKILL.md"],
                    "parsed_cmd": [{"type": "read", "cmd": SECRET, "name": "SKILL.md", "path": ".claude/skills/evidence-retrieval/SKILL.md"}],
                    "status": "completed", "exit_code": 0, "stdout": SECRET, "duration": {"secs": 0, "nanos": 300000000}}),
        item(3000, {"type": "CommandExecution", "id": "c2", "command": ["pwsh", "-Command", "uv run python " + run.format("evidence-retrieval", "open_request_bundle")],
                    "parsed_cmd": [{"type": "unknown", "cmd": SECRET}], "status": "completed", "exit_code": 0,
                    "stdout": '{"ok": true, "result": {"note": "' + SECRET + '"}}', "duration": {"secs": 1, "nanos": 0}}),
        item(4500, {"type": "CommandExecution", "id": "c3", "command": ["pwsh", "-Command", "uv run python " + run.format("evidence-retrieval", "retrieve_reviews")],
                    "status": "failed", "exit_code": 1, "stdout": '{"ok": false, "error": {"code": "model_not_found", "message": "' + SECRET + '"}}'}),
        item(5000, {"type": "Extension", "kind": "web.search", "query": SECRET, "action": {"type": "search", "query": SECRET}}),
        {**at(5900), "type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "call_exec1", "output": [{"type": "input_text", "text": SECRET}]}},
        item(20000, {"type": "CommandExecution", "id": "c4", "command": ["pwsh", "-Command", "uv run python " + run.format("review-and-revise", "save_and_export")],
                     "status": "completed", "exit_code": 0, "stdout": save_out}),
        item(22000, {"type": "FileChange", "id": "f1", "changes": {str(Path(harness) / "runtime-data" / "exports" / (SECRET + ".md")): {"type": "add", "content": SECRET}},
                     "status": "completed"}),
        {**at(23000), "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-1", "last_agent_message": SECRET}},
    ]
    child_lines = [
        {**at(6000), "type": "session_meta", "payload": {"id": child, "cwd": str(harness), "parent_thread_id": main, "agent_role": "product_review_researcher",
                                                       "source": {"subagent": {"thread_spawn": {"parent_thread_id": main}}}}},
        {**at(6001), "type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-c"}},
        {**item(7000, {"type": "Extension", "kind": "web.search", "query": SECRET, "action": {"type": "openPage", "url": f"https://reviews.example/p?q={SECRET}"}})},
        {**at(15000), "type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-c"}},
    ]
    return main_lines, child_lines


import io  # noqa: E402


class CodexFollowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agent-office-codex-")
        base = Path(self.tmp.name)
        self.root = base / "harness"
        (self.root / ".claude").mkdir(parents=True)
        (self.root / "product-install.json").write_text("{}", encoding="utf-8")
        self.home = base / "codex-home"
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc)
        self.day = self.home / "sessions" / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.day:02d}"
        self.day.mkdir(parents=True)
        self.old_home = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(self.home)
        self.out = self.root / "runtime-data" / "agent-office"

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = self.old_home
        self.tmp.cleanup()

    def write_logs(self, main_lines, child_lines, tail=""):
        main = self.day / f"rollout-2026-10-14T12-00-00-{MAIN_ID}.jsonl"
        child = self.day / f"rollout-2026-10-14T12-00-06-{CHILD_ID}.jsonl"
        main.write_text("".join(json.dumps(r) + "\n" for r in main_lines) + tail, encoding="utf-8")
        child.write_text("".join(json.dumps(r) + "\n" for r in child_lines), encoding="utf-8")
        return main

    def events(self):
        return [json.loads(line) for line in (self.out / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_codex_actual_abort_record_is_distinct_from_normal_end(self):
        import io
        main, child = codex_records(self.root)
        changed = False
        for record in main:
            if (record.get("payload") or {}).get("type") == "task_complete":
                record["payload"]["type"] = "turn_aborted"
                changed = True
        self.assertTrue(changed)
        self.write_logs(main, child)
        office.codex(self.root, latest=True, once=True, out=io.StringIO())
        cancelled = [e for e in self.events() if e["kind"] == "turn_cancelled"]
        self.assertEqual(len(cancelled), 1)
        self.assertEqual(cancelled[0]["detail"], {"reason": "turn_aborted", "interrupted": True})
        self.assertFalse(any(e["kind"] == "turn_end" for e in self.events()))

    def test_latest_session_with_agent_thread_becomes_office_records(self):
        import io
        self.write_logs(*codex_records(self.root))
        buf = io.StringIO()
        written = office.codex(self.root, latest=True, once=True, out=buf)
        events = self.events()
        self.assertEqual(written, len(events))
        kinds = [(e["hook"], e["kind"], e["actor"], e.get("node"), e.get("op"), e["phase"]) for e in events]
        self.assertIn(("SessionStart", "session", "main", "main", None, "start"), kinds)
        self.assertIn(("UserPromptSubmit", "request", "main", "main", None, "point"), kinds)
        self.assertIn(("PreToolUse", "skill_load", "main", "evidence-retrieval", None, "start"), kinds)
        self.assertIn(("PostToolUse", "skill_op", "main", "evidence-retrieval", "open_request_bundle", "end"), kinds)
        self.assertIn(("PostToolUseFailure", "skill_op", "main", "evidence-retrieval", "retrieve_reviews", "fail"), kinds)
        self.assertIn(("SubagentStart", "subagent", "product_review_researcher", "product_review_researcher", None, "start"), kinds)
        self.assertIn(("SubagentStop", "subagent", "product_review_researcher", "product_review_researcher", None, "end"), kinds)
        self.assertIn(("Stop", "turn_end", "main", "main", None, "point"), kinds)
        failed = next(e for e in events if e["op"] == "retrieve_reviews" and e["phase"] == "fail")
        self.assertEqual(failed["detail"]["error"], "model_not_found")
        save = next(e for e in events if e["op"] == "save_and_export" and e["phase"] == "end")
        self.assertEqual((save["detail"]["accepted"], save["detail"]["turn_status"]), (True, "completed"))
        web = [e for e in events if e["kind"] == "web" and e["actor"] == "product_review_researcher"]
        self.assertEqual({e["detail"].get("host") for e in web}, {"reviews.example"})
        self.assertEqual(next(e for e in events if e["kind"] == "file" and e["phase"] == "end")["detail"], {"area": "exports"})
        exec_end = next(e for e in events if e["call"] == "call_exec1" and e["phase"] == "end")
        self.assertEqual(exec_end["tool"], "exec")
        self.assertTrue(all(e["src"] == "codex" and e["session"] == MAIN_ID for e in events))
        for name in ("events.jsonl", "live.js", "codex-follow.json"):
            self.assertNotIn(SECRET, (self.out / name).read_text(encoding="utf-8"), name)
        self.assertIn("근거 조회 · open_request_bundle", buf.getvalue())
        self.assertEqual(office.codex(self.root, latest=True, once=True, out=io.StringIO()), 0)  # nothing twice

    def test_start_times_come_from_the_log(self):
        self.write_logs(*codex_records(self.root))
        office.codex(self.root, latest=True, once=True, out=io.StringIO())
        start = next(e for e in self.events() if e["op"] == "open_request_bundle" and e["phase"] == "start")
        end = next(e for e in self.events() if e["op"] == "open_request_bundle" and e["phase"] == "end")
        from datetime import datetime
        gap = datetime.fromisoformat(end["ts"].replace("Z", "+00:00")) - datetime.fromisoformat(start["ts"].replace("Z", "+00:00"))
        self.assertAlmostEqual(gap.total_seconds(), 1.0, places=2)
        self.assertEqual((start["ts_basis"], end["detail"]["duration_ms"]), ("codex_log", 1000.0))

    def test_unfinished_last_line_waits_for_its_newline(self):
        main_lines, child_lines = codex_records(self.root)
        half = json.dumps(main_lines[-1])[:40]
        self.write_logs(main_lines[:-1], child_lines, tail=half)
        office.codex(self.root, latest=True, once=True, out=io.StringIO())
        self.assertFalse(any(e["kind"] == "turn_end" for e in self.events()))
        self.write_logs(main_lines, child_lines)
        office.codex(self.root, latest=True, once=True, out=io.StringIO())
        self.assertEqual(sum(e["kind"] == "turn_end" for e in self.events()), 1)

    def test_selection_is_checked(self):
        main_lines, child_lines = codex_records(self.root)
        other = [dict(main_lines[0], payload={**main_lines[0]["payload"], "cwd": str(Path(self.tmp.name) / "elsewhere")})] + main_lines[1:]
        path = self.write_logs(other, child_lines)
        with self.assertRaises(office.OfficeError):
            office.codex(self.root, rollout=path, once=True, out=io.StringIO())
        with self.assertRaises(office.OfficeError):
            office.codex(self.root, latest=True, once=True, out=io.StringIO())
        child = self.day / f"rollout-2026-10-14T12-00-06-{CHILD_ID}.jsonl"
        with self.assertRaises(office.OfficeError):
            office.codex(self.root, rollout=child, once=True, out=io.StringIO())
        self.assertFalse((self.out / "events.jsonl").exists())

    def test_records_before_the_identity_are_ignored(self):
        main_lines, child_lines = codex_records(self.root)
        stray = {"timestamp": "2026-10-14T02:59:00.000Z", "type": "event_msg", "payload": {"type": "task_complete"}}
        path = self.write_logs(main_lines, child_lines)
        path.write_text(json.dumps(stray) + "\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
        office.codex(self.root, rollout=path, once=True, out=io.StringIO())
        self.assertEqual(sum(e["kind"] == "turn_end" for e in self.events()), 1)

    def test_wait_follows_only_a_session_started_later(self):
        import threading
        import time
        old_id = "01a20000-0000-7000-8000-0000000000ff"
        old_main, _ = codex_records(self.root, main=old_id)
        (self.day / f"rollout-2026-10-14T11-00-00-{old_id}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in old_main), encoding="utf-8")
        result = {}

        def run():
            result["n"] = office.codex(self.root, wait=True, once=True, max_minutes=0.5, out=io.StringIO())

        worker = threading.Thread(target=run)
        worker.start()
        time.sleep(1.5)
        self.write_logs(*codex_records(self.root))
        worker.join(40)
        self.assertGreater(result.get("n", 0), 0)
        self.assertEqual({e["session"] for e in self.events()}, {MAIN_ID})

    def test_sessions_list(self):
        import io
        self.write_logs(*codex_records(self.root))
        buf = io.StringIO()
        self.assertEqual(office.codex_sessions(self.root, out=buf), 1)
        self.assertIn(MAIN_ID, buf.getvalue())
        self.assertIn("하위 에이전트 1개", buf.getvalue())


class PageTests(unittest.TestCase):

    def test_actual_typescript_cancel_closes_open_spans_and_time_overlap_is_not_binding(self):
        node = shutil.which("node")
        if not node:
            self.fail("Node is required to verify the actual office state/model code")
        script = r'''
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const app = process.argv[1], target = process.argv[2];
fs.writeFileSync(path.join(target, 'package.json'), '{"type":"module"}');
for (const file of ['catalog', 'labels', 'model', 'state']) {
  const result = fs.readFileSync(path.join(target, file + '.js'), 'utf8');
  fs.writeFileSync(path.join(target, file + '.js'), result.replace(/from '([.][^']+)'/g, (_,p) => `from '${p}.js'`));
}
(async () => {
  const {buildSession} = await import(pathToFileURL(path.join(target, 'model.js')));
  const {snapshot} = await import(pathToFileURL(path.join(target, 'state.js')));
  const base = Date.parse('2026-10-13T12:00:00Z');
  const ev = (i, kind, phase='point', hook='UserPromptSubmit') => ({v:1,id:String(i),ts:new Date(base+i*1000).toISOString(),
    session:'native',agent_id:null,actor:'main',kind,phase,hook,call:kind==='tool'?'open':null,tool:'exec',basis:'observed',node:'main',op:null,detail:{}});
  const events = [ev(0,'request'), ev(1,'tool','start','PreToolUse'), ev(2,'turn_cancelled','point','Stop')];
  const db = {available:true,turn:{created_at:new Date(base).toISOString()},binding:{session_id:'business',turn_id:'turn',request_key:'request'}};
  const model = buildSession(events, 'native', db, true, true);
  assert.equal(model.dbMatched, false);
  assert.equal(model.spans[0].status, 'interrupted');
  assert.equal(model.spans[0].detail.outcome, 'unknown');
  assert.equal(model.spans[0].end, base+2000);
  const state = snapshot(model, base+2500, 10);
  assert.equal(state.active.length, 0);
  assert.match(state.main.label, /취소/);
  assert.ok(state.feed.some(x=>x.label.includes('도구 종료 결과 미확인')));
  events.push(ev(3,'tool','end','PostToolUse'));
  assert.equal(buildSession(events, 'native', db, true, true).spans[0].status, 'interrupted');
  const replay = buildSession(events.slice(0,2), 'native', db, false, true);
  assert.equal(replay.spans[0].status, 'unknown');
  assert.equal(snapshot(replay, base+2500).active.length, 0);
  events[1].detail.business_binding = db.binding;
  assert.equal(buildSession(events, 'native', db, true, true).dbMatched, true);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        with tempfile.TemporaryDirectory(prefix="office-model-check-") as target:
            compile_result = subprocess.run([node, str(APP / "app/node_modules/typescript/bin/tsc"),
                "--target", "es2022", "--module", "es2022", "--moduleResolution", "bundler", "--skipLibCheck",
                "--outDir", target, *[str(APP / "app/src/lib" / (name + ".ts")) for name in ("model", "state", "catalog", "labels")]],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            compiled = str(Path(target) / "lib") if (Path(target) / "lib").is_dir() else target
            result = subprocess.run([node, "-e", script, str(APP / "app"), compiled], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    @unittest.skipUnless((APP / "index.html").is_file(), "page not built (app: npm run build)")
    def test_page_is_one_file_that_reads_live_js(self):
        import re
        html = (APP / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('<script src="live.js" charset="utf-8"></script>'), 1)
        external = re.findall(r'<script[^>]+src="([^"]+)"', html)
        self.assertEqual(external, ["live.js"])
        self.assertNotIn('src="./assets/', html)
        self.assertIn("THIRD-PARTY NOTICES", html)
        for text in ("데모 화면", "실제 하네스가 한 일이 아닙니다", "명령 경로로 알아냄", "미측정"):
            self.assertIn(text, html)


if __name__ == "__main__":
    unittest.main()
