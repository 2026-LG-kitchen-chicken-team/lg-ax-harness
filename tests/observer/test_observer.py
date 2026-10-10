import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import time
import threading
import unittest
from urllib.request import Request, urlopen

from observer.collector import Collector, digest
from observer.storage import JsonlReader, LocalStore
from observer.otlp import Exporter, endpoint, payload
from observer.__main__ import collect

NATIVE = "0199abcd-1234-7000-8000-123456789abc"
OTHER = "0199abcd-1234-7000-8000-123456789abd"
REF = digest("private-log")
ENV = {"OBSERVER_OTLP_ENDPOINT": "https://cloud.langfuse.com/api/public/otel/v1/traces",
       "LANGFUSE_PUBLIC_KEY": "pk-lf-test", "LANGFUSE_SECRET_KEY": "sk-lf-test"}


def start(collector, kind="cli"):
    raw = {"type": "thread.started", "thread_id": NATIVE} if kind == "cli" else {"type": "session_meta", "payload": {"id": NATIVE}}
    return collector.feed(raw, REF, 1, kind)


def tokens(i=100, c=20, o=30, r=10):
    return dict(zip(("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"), (i, c, o, r)))


def snapshot(collector, seq, value):
    return collector.feed({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": value}}}, REF, seq, "rollout")


def completed(collector, seq=2, item="item_0"):
    return collector.feed({"type": "item.completed", "item": {"id": item, "type": "command_execution", "exit_code": 0}}, REF, seq, "cli")


class CollectorTests(unittest.TestCase):
    def test_custom_call_output_list_failure_and_no_nested_tool_invention(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        call = c.feed({"type": "response_item", "payload": {"type": "custom_tool_call", "call_id": "call_secret",
            "name": "exec", "input": "await tools.apply_patch('private raw patch sk-secret');", "status": "completed"}}, REF, 2, "rollout")
        event = c.feed({"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "call_secret",
            "output": [{"type": "input_text", "text": "Script failed\napply_patch verification failed: C:/Users/Private sk-secret"}]}}, REF, 3, "rollout")
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["error_code"], "tool_verification_failed")
        self.assertEqual(event["entity_name"], "exec")
        self.assertEqual(event["tool_type"], "custom_tool_call")
        self.assertEqual(call["invocation_id"], event["invocation_id"])
        self.assertEqual(event["observation_layer"], "rollout_tool")
        self.assertIsNone(event["parent_id"])
        self.assertIsNone(event["mapped_skill"])
        self.assertNotIn("apply_patch", json.dumps(event))
        self.assertNotIn("C:/Users", json.dumps(event))
        self.assertNotIn("sk-secret", json.dumps(event))

    def test_function_output_nonzero_exit_and_output_is_not_success_evidence(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        c.feed({"type": "response_item", "payload": {"type": "function_call", "call_id": "call_1", "name": "exec_command", "arguments": "{}"}}, REF, 2, "rollout")
        event = c.feed({"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call_1", "output": "Process exited with code 1\nFile not found"}}, REF, 3, "rollout")
        self.assertEqual(event["status"], "failed")
        self.assertEqual(event["entity_name"], "exec_command")
        self.assertEqual(payload(event)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["status"]["code"], 2)
        neutral = c.feed({"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call_2", "output": "unstructured response"}}, REF, 4, "rollout")
        self.assertEqual(neutral["result_status_basis"], "output_observed")

    def test_explicit_call_id_dedup_keeps_unpaired_cli_layer(self):
        c = Collector(NATIVE, "run")
        start(c)
        cli = completed(c)
        ref2 = digest("rollout")
        c.feed({"type": "session_meta", "payload": {"id": NATIVE}}, ref2, 1, "rollout")
        raw = {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "item_0", "output": "result"}}
        roll = c.feed(raw, ref2, 2, "rollout")
        self.assertIsNone(cli["correlation_id"])
        self.assertEqual(roll["correlation_id"], "item_0")
        self.assertNotEqual(cli["observation_layer"], roll["observation_layer"])
        self.assertIsNone(c.feed(raw, ref2, 3, "rollout"))
        self.assertEqual(c.state["counts"]["duplicate_tool_phase"], 1)
        self.assertIsNone(c.summary()["merged_tool_execution_count"])
        self.assertEqual(len(c.summary()["source_tool_results"]), 2)

    def test_cached_and_reasoning_highwater_survive_partial_nulls(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, tokens(100, 80, 50, 40))
        snapshot(c, 3, {"input_tokens": 150, "output_tokens": 60})
        self.assertIsNone(c.summary()["native_usage"]["snapshot"]["cached_input_tokens"])
        rejected = snapshot(c, 4, tokens(160, 10, 65, 5))
        self.assertIsNone(rejected["usage_snapshot"]["input_tokens"])
        self.assertEqual(c.summary()["native_usage"]["snapshot"]["input_tokens"], 150)
        self.assertIsNone(c.summary()["native_usage"]["snapshot"]["reasoning_output_tokens"])

    def test_missing_values_are_null(self):
        c = Collector(NATIVE, "run")
        self.assertIsNone(c.summary()["native_usage"])
        self.assertIsNone(c.summary()["noncached_input_tokens"])
        self.assertIsNone(c.summary()["backend_call_count"])

    def test_explicit_identity_required(self):
        c = Collector(NATIVE, "run")
        self.assertIsNone(completed(c))
        c.feed({"type": "thread.started", "thread_id": OTHER}, REF, 1, "cli")
        self.assertIsNone(completed(c))
        self.assertEqual(c.state["counts"]["identity_mismatch"], 1)

    def test_duplicate_reconnect_and_regressing_sequence(self):
        c = Collector(NATIVE, "run")
        start(c)
        event = completed(c, 5)
        self.assertIsNotNone(event)
        self.assertIsNone(completed(c, 5))
        self.assertIsNone(completed(c, 4))
        self.assertEqual(c.state["counts"]["accepted_events"], 2)
        self.assertEqual(c.state["counts"]["duplicate_or_stale_sequence"], 2)

    def test_latest_cumulative_not_sum_and_cached_subset(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, tokens())
        snapshot(c, 3, tokens(150, 40, 50, 20))
        value = c.summary()
        self.assertEqual(value["native_usage"]["snapshot"]["input_tokens"], 150)
        self.assertEqual(value["noncached_input_tokens"], 110)
        self.assertEqual(value["native_usage"]["snapshot"]["output_tokens"], 50)
        self.assertEqual(value["native_usage"]["status"], "partial")

    def test_regressing_usage_does_not_replace_latest(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, tokens())
        rejected = snapshot(c, 3, tokens(90, 20, 25, 10))
        self.assertIsNone(rejected["usage_snapshot"]["input_tokens"])
        self.assertEqual(c.summary()["native_usage"]["snapshot"]["input_tokens"], 100)
        self.assertEqual(c.state["counts"]["regressing_or_invalid_usage"], 1)

    def test_invalid_cache_and_reasoning_subsets(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, tokens(100, 101, 30, 10))
        snapshot(c, 3, tokens(100, 20, 30, 31))
        self.assertIsNone(c.summary()["native_usage"])

    def test_partial_fields_remain_unknown_and_bool_not_token(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, {"input_tokens": 100, "cached_input_tokens": True})
        self.assertIsNone(c.summary()["native_usage"]["snapshot"]["cached_input_tokens"])
        self.assertIsNone(c.summary()["noncached_input_tokens"])

    def test_cli_usage_is_separate_and_may_be_smaller_next_turn(self):
        c = Collector(NATIVE, "run")
        start(c)
        c.feed({"type": "turn.completed", "usage": tokens(100)}, REF, 2, "cli")
        c.feed({"type": "turn.completed", "usage": tokens(50)}, REF, 3, "cli")
        self.assertIsNone(c.summary()["native_usage"])
        self.assertEqual(c.summary()["last_cli_turn_usage"]["snapshot"]["input_tokens"], 50)

    def test_redaction_and_instruction_mapping(self):
        c = Collector(NATIVE, "run")
        start(c)
        raw = {"type": "item.completed", "prompt": "secret prompt", "item": {
            "id": "C:/Users/Private/sk-real-key", "type": "command_execution", "status": "completed",
            "command": "Get-Content C:/Users/Private/skills/evidence-retrieval/SKILL.md",
            "aggregated_output": "reasoning private sk-real-key", "stdout": "private", "exit_code": 0}}
        event = c.feed(raw, REF, 2, "cli")
        encoded = json.dumps(event)
        self.assertNotIn("C:/Users", encoded)
        self.assertNotIn("sk-real-key", encoded)
        self.assertNotIn("secret prompt", encoded)
        self.assertNotIn("aggregated_output", encoded)
        self.assertEqual(event["skill_mapping_basis"], "instruction_loaded")
        self.assertEqual(event["mapped_skill"], "evidence-retrieval")

    def test_command_mapping_and_failure_status(self):
        c = Collector(NATIVE, "run")
        start(c)
        event = c.feed({"type": "item.completed", "item": {"type": "command_execution", "id": "item_0",
            "command": "python tool.py save_result", "exit_code": 2}}, REF, 2, "cli")
        self.assertEqual(event["skill_mapping_basis"], "command_based_mapping")
        self.assertEqual(event["status"], "failed")

    def test_timestamp_redaction_and_actual_parent(self):
        c = Collector(NATIVE, "run")
        start(c)
        event = c.feed({"type": "item.completed", "timestamp": "sk-secret", "item": {"type": "mcp_tool_call",
            "id": "item_1", "parent_id": "item_0"}}, REF, 2, "cli")
        self.assertIsNone(event["source_timestamp"])
        self.assertEqual(event["parent_id"], "item_0")
        self.assertIsNone(event["turn_id"])


class ReaderStoreTests(unittest.TestCase):
    def test_dual_sources_preserve_custom_failure_missing_from_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            cli, rollout = Path(directory)/"cli", Path(directory)/"rollout"
            cli.write_text(json.dumps({"type": "thread.started", "thread_id": NATIVE}) + "\n" + json.dumps({"type": "item.completed", "item": {"type": "command_execution", "id": "item_0", "exit_code": 0}}) + "\n")
            rollout.write_text(json.dumps({"type": "session_meta", "payload": {"id": NATIVE}}) + "\n" + json.dumps({"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": "call_missing_in_cli", "output": [{"type": "input_text", "text": "apply_patch verification failed: private"}]}}) + "\n")
            args = argparse.Namespace(output=Path(directory)/"out", local_limit=4096, native_id=NATIVE, run_id="run", mode="replay",
                cli_log=cli, rollout_log=rollout, http_timeout=0.05, queue_limit=1,
                stop_file=None, until_complete=False, max_seconds=0.02, poll_seconds=0.01)
            value = collect(args, environment={})
            totals = value["source_tool_results"]
            self.assertEqual(totals["cli:cli_item:command_execution"]["returned"], 1)
            self.assertEqual(totals["rollout:rollout_tool:custom_tool_call"]["failed"], 1)
            lines = (Path(directory)/"out/events.jsonl").read_text()
            self.assertIn("tool_verification_failed", lines)
            self.assertNotIn("verification failed: private", lines)

    def test_unterminated_json_tail_waits_replay_accepts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_text('{"type":"thread.started","thread_id":"' + NATIVE + '"}', encoding="utf-8")
            reader = JsonlReader(path)
            self.assertEqual(reader.poll(), [])
            with path.open("a") as stream:
                stream.write("\n")
            self.assertEqual(len(reader.poll()), 1)
            self.assertEqual(len(JsonlReader(path).poll(final=True)), 1)

    def test_invalid_unterminated_replay_and_oversize_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_bytes(b"X" * 100 + b'\n{"type":"safe"}\n{"type":')
            reader = JsonlReader(path, max_line=50)
            self.assertEqual(len(reader.poll(final=True)), 1)
            self.assertEqual(reader.errors["line_limit"], 1)
            self.assertEqual(reader.errors["invalid_json"], 1)

    def test_checkpoint_reconnect_bounded_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStore(directory, max_bytes=4096)
            c = Collector(NATIVE, "run")
            start(c)
            event = completed(c)
            for i in range(30):
                store.append(event)
            self.assertLessEqual(store.events.stat().st_size, 4096)
            store.save(c)
            restored = Collector(NATIVE, "run", state=store.load(NATIVE, "run"))
            start(restored)
            self.assertIsNone(completed(restored))

    def test_old_parser_checkpoint_fails_closed_instead_of_hiding_custom_events(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStore(directory)
            c = Collector(NATIVE, "run")
            start(c)
            store.save(c)
            old = json.loads(store.checkpoint.read_text())
            old["state"].pop("parser_version")
            store.checkpoint.write_text(json.dumps(old))
            with self.assertRaisesRegex(ValueError, "checkpoint_parser_version_mismatch"):
                store.load(NATIVE, "run")

    def test_tail_stop_file_and_source_failure_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "log"
            path.write_text(json.dumps({"type": "thread.started", "thread_id": NATIVE}) + "\n")
            stop = Path(directory) / "stop"
            stop.touch()
            args = argparse.Namespace(output=Path(directory)/"out", local_limit=4096, native_id=NATIVE, run_id="run", mode="tail",
                cli_log=path, rollout_log=Path(directory)/"missing", http_timeout=0.05, queue_limit=1,
                stop_file=stop, until_complete=False, max_seconds=0.03, poll_seconds=0.01)
            value = collect(args, environment={})
            self.assertEqual(value["stop_reason"], "observer_stop_file")
            self.assertFalse(value["export"]["configured"])
            self.assertTrue(any("source_unavailable" in e for e in value["reader_errors"].values()))
            self.assertTrue(path.exists())

    def test_tail_time_limit_and_no_model_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output=Path(directory)/"out", local_limit=4096, native_id=NATIVE, run_id="run", mode="tail",
                cli_log=Path(directory)/"missing", rollout_log=None, http_timeout=0.05, queue_limit=1,
                stop_file=None, until_complete=False, max_seconds=0.02, poll_seconds=0.01)
            value = collect(args, environment={})
            self.assertEqual(value["stop_reason"], "observer_time_limit")
            self.assertEqual(value["observer_created_model_requests"], 0)

    def test_source_output_conflict_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("original raw log", encoding="utf-8")
            args = argparse.Namespace(output=directory, cli_log=path, rollout_log=None)
            with self.assertRaisesRegex(ValueError, "source_output_conflict"):
                collect(args, environment={})
            self.assertEqual(path.read_text(), "original raw log")


class FakeResponse:
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, count):
        return b"{}"


class FakeOpener:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.fail:
            raise TimeoutError("sk-lf-test private credential failure")
        return FakeResponse()


class ExportTests(unittest.TestCase):
    def event(self):
        c = Collector(NATIVE, "run")
        start(c)
        return completed(c)

    def test_otlp_json_payload_without_generation_cost_usage_attributes(self):
        value = payload(self.event())
        span = value["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        self.assertEqual(len(span["traceId"]), 32)
        self.assertEqual(len(span["spanId"]), 16)
        attrs = {a["key"]: a["value"] for a in span["attributes"]}
        self.assertEqual(attrs["langfuse.observation.type"], {"stringValue": "tool"})
        self.assertIn("langfuse.observation.metadata.usage_snapshot", attrs)
        self.assertFalse(any("gen_ai" in key or "cost" in key or key.endswith(".usage") for key in attrs))

    def test_completed_rollout_span_preserves_latest_native_usage_metadata(self):
        c = Collector(NATIVE, "run")
        start(c, "rollout")
        snapshot(c, 2, tokens(150, 40, 50, 20))
        event = c.feed({"type": "event_msg", "payload": {"type": "task_complete"}}, REF, 3, "rollout")
        attrs = {a["key"]: a["value"] for a in payload(event)["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["attributes"]}
        stored = json.loads(attrs["langfuse.observation.metadata.native_usage_snapshot"]["stringValue"])
        self.assertEqual(stored["input_tokens"], 150)
        self.assertEqual(stored["cached_input_tokens"], 40)
        self.assertEqual(event["native_usage_status"], "completed_observation")

    def test_partial_not_exportable_and_tampered_metadata_redacted(self):
        event = self.event()
        event["status"] = "partial"
        with self.assertRaises(ValueError):
            payload(event)
        event["status"] = "completed"
        event["run_id"] = "C:/Users/Private"
        with self.assertRaises(ValueError):
            payload(event)

    def test_all_non_snapshot_metadata_reject_nested_objects_and_non_strings(self):
        event = self.event()
        fields = ("mapped_skill", "run_id", "native_thread_id", "turn_id", "invocation_id", "parent_id", "status",
            "entity_name", "event_kind", "source_kind", "mode", "coverage", "usage_scope", "skill_mapping_basis",
            "timing_basis", "native_usage_status", "cli_version", "correlation_id", "correlation_basis",
            "observation_layer", "tool_type", "result_status_basis", "error_code")
        for key in fields:
            for bad in ({"account": "private", "path": "C:/Users/Private"}, ["sk-secret"], 7, True):
                with self.subTest(key=key, bad_type=type(bad).__name__):
                    tampered = dict(event, **{key: bad})
                    with self.assertRaises(ValueError):
                        payload(tampered)

    def test_metadata_enums_reject_unrecognized_strings(self):
        for key in ("mapped_skill", "entity_name", "event_kind", "source_kind", "mode", "coverage", "usage_scope",
                    "skill_mapping_basis", "timing_basis", "native_usage_status", "correlation_basis", "observation_layer",
                    "tool_type", "result_status_basis", "error_code"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    payload(dict(self.event(), **{key: "private_account_name"}))

    def test_nested_skill_is_dropped_before_queue_attempt_or_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = FakeOpener()
            store = LocalStore(directory)
            ex = Exporter(store, environment=ENV, opener=opener)
            event = dict(self.event(), mapped_skill={"account": "private", "path": "C:/Users/Private"})
            ex.submit(event)
            self.assertEqual(ex.counters["failed"], 1)
            self.assertEqual(ex.queue.qsize(), 0)
            self.assertFalse(store.attempts.exists())
            self.assertEqual(opener.calls, [])

    def test_endpoint_validation_and_no_configuration(self):
        for value in ("http://host/api/public/otel/v1/traces", "https://user:secret@host/api/public/otel/v1/traces",
                      "https://host/api/public/otel/v1/traces?secret=1", "https://host/other", "https://host:xyz/api/public/otel/v1/traces"):
            with self.assertRaises(ValueError):
                endpoint(value)
        with tempfile.TemporaryDirectory() as directory:
            ex = Exporter(LocalStore(directory), environment={})
            ex.submit(self.event())
            self.assertFalse(ex.summary()["configured"])
            self.assertEqual(ex.counters["not_configured"], 1)

    def test_once_export_headers_timeout_and_durable_reconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = FakeOpener()
            ex = Exporter(LocalStore(directory), environment=ENV, timeout=0.05, opener=opener)
            ex.start()
            ex.submit(self.event())
            ex.submit(self.event())
            ex.close(grace=0.3)
            self.assertEqual(len(opener.calls), 1)
            request, timeout = opener.calls[0]
            self.assertEqual(timeout, 0.05)
            self.assertEqual(request.get_header("X-langfuse-ingestion-version"), "4")
            self.assertEqual(ex.counters["exported"], 1)
            again = Exporter(LocalStore(directory), environment=ENV, opener=opener)
            again.submit(self.event())
            self.assertEqual(again.counters["duplicate"], 1)
            self.assertNotIn("sk-lf-test", json.dumps(ex.summary()))

    def test_network_failure_isolated_and_no_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = FakeOpener(fail=True)
            ex = Exporter(LocalStore(directory), environment=ENV, timeout=0.05, opener=opener)
            ex.start()
            event = self.event()
            ex.submit(event)
            ex.close(grace=0.3)
            self.assertEqual(ex.counters["failed"], 1)
            self.assertEqual(ex.counters["exported"], 0)
            self.assertEqual(len(opener.calls), 1)
            self.assertNotIn("credential", json.dumps(ex.summary()))

    def test_real_http_socket_timeout_is_bounded(self):
        class SlowHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                time.sleep(0.25)
                try:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"{}")
                except OSError:
                    pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        class LoopbackTestOpener:
            def open(self, request, timeout):
                # Test-only transport substitution; production still requires HTTPS.
                req = Request("http://127.0.0.1:" + str(server.server_port), data=request.data, method="POST")
                return urlopen(req, timeout=timeout)
        try:
            with tempfile.TemporaryDirectory() as directory:
                ex = Exporter(LocalStore(directory), environment=ENV, timeout=0.05, opener=LoopbackTestOpener())
                begun = time.monotonic()
                ex.start()
                ex.submit(self.event())
                ex.close(grace=0.2)
                self.assertEqual(ex.counters["failed"], 1)
                self.assertLess(time.monotonic() - begun, 0.5)
        finally:
            server.shutdown()
            server.server_close()

    def test_queue_overflow_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            ex = Exporter(LocalStore(directory), environment=ENV, capacity=1)
            c = Collector(NATIVE, "run")
            start(c)
            one, two = completed(c, 2, "item_0"), completed(c, 3, "item_1")
            ex.submit(one)
            ex.submit(two)
            self.assertEqual(ex.queue.qsize(), 1)
            self.assertEqual(ex.counters["dropped"], 1)
            ex.submit(two)
            self.assertEqual(ex.counters["duplicate"], 1)
            ex.close(grace=0)


if __name__ == "__main__":
    unittest.main()
