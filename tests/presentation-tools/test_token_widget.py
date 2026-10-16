import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("token_widget", ROOT / "presentation-tools/token-widget/widget.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
SID = "0199abcd-1234-7000-8000-123456789abc"
OTHER = "0199abcd-1234-7000-8000-123456789abd"


def bind(m):
    m.feed({"type": "session_meta", "payload": {"id": SID}} if m.engine == "codex" else
           {"type": "system", "session_id": SID, "subtype": "init"})


class TokenWidgetTests(unittest.TestCase):
    def test_codex_cumulative_not_summed_and_cache_subset(self):
        m = w.Meter("codex", SID); bind(m)
        for i in (100, 120):
            m.feed({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage":
                    {"input_tokens": i, "cached_input_tokens": 80, "output_tokens": 30, "reasoning_output_tokens": 10}}}})
        self.assertEqual(m.view()["tokens"], {"input": 120, "cache_read": 80, "output": 30, "reasoning": 10, "cache_write": None})
        m.feed({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 90}}}})
        self.assertIn("usage_regressed", m.view()["errors"])
        self.assertEqual(m.view()["tokens"]["input"], 120)

    def test_response_id_latest_and_no_second_cumulative_layer(self):
        m = w.Meter("codex", SID); bind(m)
        for rid, n in (("r1", 3), ("r1", 5), ("r2", 7)):
            m.feed({"type": "token_usage_record", "payload": {"response_id": rid, "usage": {"input_tokens": n, "output_tokens": 1}}})
        m.feed({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 1000}}}})
        self.assertEqual(m.view()["tokens"]["input"], 12)
        self.assertEqual(m.view()["basis"], "unique_responses")

    def test_regressed_window_snapshot_does_not_subtract_baseline_twice(self):
        m = w.Meter("codex", SID, since="2026-10-16T10:00:00Z"); bind(m)
        for at, n in (("09:59:59", 100), ("10:00:01", 500), ("10:00:02", 450)):
            m.feed({"type": "event_msg", "timestamp": "2026-10-16T"+at+"Z", "payload":
                   {"type": "token_count", "info": {"total_token_usage": {"input_tokens": n}}}})
        self.assertEqual(m.view()["tokens"]["input"], 400)
        self.assertIn("usage_regressed", m.view()["errors"])

    def test_claude_camel_session_and_message_latest_no_thinking_double_count(self):
        m = w.Meter("claude", SID)
        for mid, n in (("m1", 3), ("m1", 7), ("m2", 9)):
            m.feed({"type": "assistant", "sessionId": SID, "message": {"id": mid, "model": "claude-opus-5-5",
                "usage": {"input_tokens": 2, "output_tokens": n, "cache_read_input_tokens": 20, "cache_creation_input_tokens": 10,
                          "iterations": [{"output_tokens": 999}], "output_tokens_details": {"thinking_tokens": 5}}}})
        v = m.view()
        self.assertEqual(v["tokens"], {"input": 4, "output": 16, "cache_read": 40, "cache_write": 20, "reasoning": None})
        m.feed({"type": "result", "session_id": SID, "usage": {"input_tokens": 90000}})
        self.assertEqual(m.view()["tokens"]["input"], 4)
        m.feed({"type": "assistant", "session_id": SID, "message": {"id": "m2", "content": "later chunk without usage"}})
        self.assertEqual(m.view()["tokens"]["output"], 16)

    def test_claude_final_chunk_without_usage_finishes_without_erasing_numbers(self):
        m = w.Meter("claude", SID); bind(m)
        m.feed({"type": "user", "sessionId": SID, "timestamp": "2026-10-16T10:00:00Z", "message": {"content": "question"}})
        m.feed({"type": "assistant", "sessionId": SID, "message": {"id": "m1", "usage": {"output_tokens": 12}}})
        m.feed({"type": "assistant", "sessionId": SID, "timestamp": "2026-10-16T10:00:45Z",
                "message": {"id": "m1", "stop_reason": "end_turn"}})
        self.assertEqual(m.view()["tokens"]["output"], 12)
        self.assertEqual(m.view()["elapsed_seconds"], 45)
        self.assertEqual(m.view()["status"], "completed")

    def test_real_claude_followup_resets_clock_but_tool_results_do_not(self):
        m = w.Meter("claude", SID); bind(m)
        def feed(typ, minute, message):
            m.feed({"type": typ, "sessionId": SID, "timestamp": f"2026-10-16T10:{minute}:00Z", "message": message})
        feed("user", "00", {"content": [{"type": "text", "text": "first"}]})
        feed("assistant", "01", {"id": "one", "stop_reason": "end_turn", "usage": {"output_tokens": 4}})
        feed("user", "02", {"content": [{"type": "text", "text": "followup"}]})
        self.assertEqual(m.view()["status"], "running")
        feed("user", "03", {"content": [{"type": "tool_result", "content": "tool return"}]})
        feed("assistant", "04", {"id": "two", "stop_reason": "end_turn", "usage": {"output_tokens": 3}})
        self.assertEqual(m.view()["elapsed_seconds"], 120)
        self.assertEqual(m.view()["tokens"]["output"], 7)

    def test_codex_followup_uses_latest_task_clock_and_session_usage(self):
        m = w.Meter("codex", SID); bind(m)
        for minute, kind in (("00", "task_started"), ("01", "task_complete"), ("05", "task_started"), ("07", "task_complete")):
            m.feed({"type": "event_msg", "timestamp": f"2026-10-16T10:{minute}:00Z", "payload": {"type": kind}})
        self.assertEqual(m.view()["elapsed_seconds"], 120)

    def test_identity_and_privacy_and_unobserved_not_zero(self):
        m = w.Meter("claude", SID)
        m.feed({"type": "assistant", "sessionId": OTHER, "message": {"id": "secret", "usage": {"input_tokens": 9999}}})
        bind(m)
        m.feed({"type": "assistant", "session_id": SID, "message": {"id": "secret", "content": "sk-private C:/Users/private prompt",
                "usage": {"output_tokens": 3}}})
        public = json.dumps(m.view())
        self.assertNotIn("sk-private", public); self.assertNotIn("C:/Users", public); self.assertNotIn("secret", public)
        self.assertIsNone(m.view()["tokens"]["input"])
        self.assertIsNone(m.view()["backend_billing"])
        m.feed({"type": "assistant", "session_id": SID, "message": {"id": "other", "model": "C:/Users/private", "usage": {"input_tokens": True}}})
        self.assertIsNone(m.view()["model"])
        self.assertNotIn("C:/Users", json.dumps(m.view()))

    def test_since_excludes_previous_response_and_elapsed_is_native_interval(self):
        m = w.Meter("codex", SID, since="2026-10-16T10:00:00Z"); bind(m)
        for at, rid in (("09:59:59", "old"), ("10:00:01", "new")):
            m.feed({"type": "token_usage_record", "timestamp": "2026-10-16T"+at+"Z", "payload": {"response_id": rid, "usage": {"input_tokens": 5}}})
        m.feed({"type": "event_msg", "timestamp": "2026-10-16T10:00:00Z", "payload": {"type": "task_started"}})
        m.feed({"type": "event_msg", "timestamp": "2026-10-16T10:01:01Z", "payload": {"type": "task_complete"}})
        self.assertEqual(m.view()["tokens"]["input"], 5)
        self.assertEqual(m.view()["elapsed_seconds"], 61)

    def test_user_start_after_earlier_task_start_and_until_excludes_future_turn(self):
        m = w.Meter("codex", SID, since="2026-10-16T10:00:00Z", until="2026-10-16T10:01:00Z"); bind(m)
        m.feed({"type": "event_msg", "timestamp": "2026-10-16T09:59:59Z", "payload": {"type": "task_started"}})
        m.feed({"type": "response_item", "timestamp": "2026-10-16T10:00:00Z", "payload": {"role": "user"}})
        m.feed({"type": "event_msg", "timestamp": "2026-10-16T10:00:50Z", "payload": {"type": "task_complete"}})
        m.feed({"type": "event_msg", "timestamp": "2026-10-16T10:02:00Z", "payload": {"type": "task_started"}})
        self.assertEqual(m.view()["status"], "completed")
        self.assertEqual(m.view()["elapsed_seconds"], 50)

    def test_replay_and_tail_incomplete_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"native.jsonl"
            start = json.dumps({"type": "thread.started", "thread_id": SID})+"\n"
            token = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 4, "output_tokens": 6}})
            p.write_text(start+token[:20], encoding="utf-8")
            d = w.Display([(p, w.Meter("codex", SID))], "live"); d.poll()
            self.assertIsNone(d.view()["sources"][0]["tokens"]["input"])
            with p.open("a", encoding="utf-8") as f: f.write(token[20:]+"\n")
            d.poll(); d.poll()
            self.assertEqual(d.view()["sources"][0]["tokens"]["input"], 4)

    def test_child_is_separate_not_added_to_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"empty"; p.write_text("")
            d = w.Display([(p, w.Meter("claude", SID)), (p, w.Meter("claude", OTHER, "child"))])
            value = d.view()
            self.assertEqual([s["role"] for s in value["sources"]], ["parent", "child"])
            self.assertNotIn("total_tokens", value)

    def test_http_only_loopback_exact_paths_no_raw_files_or_cross_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"private"; p.write_text("sk-private")
            d = w.Display([(p, w.Meter("claude", SID))])
            server = ThreadingHTTPServer(("127.0.0.1", 0), w.handler(d))
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(url+"/usage.json", timeout=2) as response:
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertNotIn("sk-private", response.read().decode())
                for path, headers, code in (("/../private", {}, 404), ("/usage.json?path=private", {}, 404),
                                            ("/usage.json", {"Host": "attacker.example"}, 403),
                                            ("/usage.json", {"Origin": "https://attacker.example"}, 403)):
                    with self.assertRaises(HTTPError) as caught: urlopen(Request(url+path, headers=headers), timeout=2)
                    self.assertEqual(caught.exception.code, code)
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_widget_not_in_product_install_source_map(self):
        spec = importlib.util.spec_from_file_location("product_install", ROOT/"adapters/codex/install.py")
        install = importlib.util.module_from_spec(spec); spec.loader.exec_module(install)
        paths = install.source_files(ROOT)
        self.assertTrue(paths)
        self.assertFalse(any("presentation-tools" in str(path) for path in paths))


if __name__ == "__main__":
    unittest.main()
