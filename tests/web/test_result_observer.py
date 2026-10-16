"""Synthetic file delivery/lifecycle regressions. No model, GUI, server or browser."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import test_visual_viewer as fixture

delivery = fixture.load("delivery")
watch = fixture.load("watch")
hook = fixture.hook


def setUpModule():
    fixture.setUpModule()


def tearDownModule():
    fixture.tearDownModule()


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lgax-result-observer-")
        self.h = fixture.Harness(Path(self.tmp.name) / "harness")
        self.app = self.h.root / "web/prototypes/visual-viewer"
        self.app.mkdir(parents=True)
        for name in ("hook.py", "build_view.py", "index.html", "delivery.py", "watch.py"):
            shutil.copyfile(fixture.VIEWER / name, self.app / name)
        self.opener = mock.Mock(return_value=True)
        # Mock the OS request; no test opens a browser, including failure paths.
        self.env = mock.patch.dict(os.environ, {"LGAX_VIEWER_NO_OPEN": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def observer(self):
        return watch.Observer(self.h.root, "codex", self.opener)

    def settle(self, observer):
        first = observer.tick()
        return observer.tick() if first["status"] == "stabilizing" else first

    def test_without_stop_hook_new_export_builds_valid_two_files_and_one_os_request(self):
        o = self.observer()
        self.h.add("microwave")
        result = self.settle(o)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["business_status"], ["completed"])
        self.assertEqual(result["open_status"], "requested")
        self.assertFalse(result["display_verified"])
        self.assertFalse(result["native_end_observed"])
        self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["current_binding"], "matched_current")
        self.assertTrue((self.h.out / "index.html").is_file())
        self.assertTrue((self.h.out / "view-data.js").is_file())
        self.opener.assert_called_once()
        self.assertTrue(o.tick()["unchanged"])

    def test_old_baseline_is_not_opened_or_rebuilt(self):
        self.h.add("microwave")
        o = self.observer()
        self.assertEqual(o.tick()["status"], "baseline_ignored")
        self.opener.assert_not_called()
        self.assertFalse((self.h.out / "view-data.js").exists())

    def test_followup_same_native_session_refreshes_without_second_open(self):
        o = self.observer()
        office = self.h.root / "runtime-data/agent-office"
        office.mkdir()
        (office / "codex-follow.json").write_text(json.dumps({"sessions": {"native-one": {}}}), encoding="utf-8")
        self.h.add("microwave")
        self.assertEqual(self.settle(o)["open_status"], "requested")
        before = (self.h.out / "view-data.js").read_bytes()
        self.h.add("two_turns")
        result = self.settle(o)
        self.assertEqual(result["open_status"], "already_requested")
        self.assertNotEqual(before, (self.h.out / "view-data.js").read_bytes())
        self.opener.assert_called_once()

    def test_partial_export_has_bounded_retry_and_recovers_after_rewrite(self):
        o = self.observer()
        p = self.h.add("microwave")
        complete = p.read_bytes()
        p.write_bytes(complete[:80])
        self.assertEqual(self.settle(o)["status"], "generation_failed")
        self.assertEqual(o.tick()["status"], "generation_failed")
        self.assertEqual(o.tick()["status"], "retry_exhausted")
        self.opener.assert_not_called()
        p.write_bytes(complete)
        self.assertEqual(self.settle(o)["status"], "ready")
        self.opener.assert_called_once()

    def test_web_payload_can_arrive_after_export(self):
        o = self.observer()
        self.h.add("microwave")
        web = self.h.root / "runtime-data/web-deliveries"
        stored = [(p, p.read_bytes()) for p in web.iterdir()]
        for p, _ in stored:
            p.unlink()
        self.assertEqual(self.settle(o)["status"], "waiting_binding")
        self.assertTrue(o.tick()["unchanged"])
        self.opener.assert_not_called()
        for p, raw in stored:
            p.write_bytes(raw)
        self.assertEqual(self.settle(o)["status"], "ready")

    def test_unreviewed_current_result_does_not_open_an_old_accepted_result(self):
        o = self.observer()
        self.h.add("fourth_pending")
        self.assertEqual(self.settle(o)["binding"], "not_reviewed_current")
        self.opener.assert_not_called()

    def test_workflow_finish_export_is_required_and_native_end_remains_unknown(self):
        o = self.observer()
        body = fixture.export_of("microwave")
        key = body["turns"][-1]["state"]["request_key"]
        request = next(r for r in body["requests"] if r["input"]["request_key"] == key)
        request["workflow"] = {"tracked": True, "finished_at": None}
        p = self.h.add("microwave", data=body)
        self.assertEqual(self.settle(o)["binding"], "awaiting_workflow_finish")
        self.opener.assert_not_called()
        request["workflow"]["finished_at"] = "2026-10-16T01:00:00Z"
        p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        result = self.settle(o)
        self.assertTrue(result["local_workflow_finished"])
        self.assertFalse(result["native_end_observed"])
        self.opener.assert_called_once()

    def test_held_and_turnless_needs_input_keep_their_business_status(self):
        for key, expected in (("held", "held"), ("needs_input", "needs_input")):
            with self.subTest(key=key):
                o = self.observer()
                self.h.add(key)
                result = self.settle(o)
                self.assertEqual(result["status"], "ready")
                self.assertEqual(result["business_status"], [expected])
                if key == "needs_input":
                    self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["current_binding"], "request_only")

    def test_failed_open_is_not_success_and_retries_at_most_three_times(self):
        self.opener.side_effect = [False, OSError("mock OS failure"), True]
        o = self.observer()
        self.h.add("microwave")
        self.assertEqual(self.settle(o)["open_status"], "failed")
        self.assertFalse(self.h.state().get("opened_sessions"))
        self.assertEqual(o.tick()["open_status"], "failed")
        self.assertEqual(o.tick()["open_status"], "requested")
        self.assertTrue(self.h.state()["opened_sessions"])
        self.assertEqual(self.opener.call_count, 3)
        o.tick()
        self.assertEqual(self.opener.call_count, 3)

    def test_exhausted_open_has_no_false_success_marker(self):
        self.opener.return_value = False
        o = self.observer()
        self.h.add("microwave")
        self.settle(o)
        o.tick(); o.tick()
        self.assertEqual(o.tick()["open_status"], "retry_exhausted")
        self.assertFalse(self.h.state().get("opened_sessions"))
        self.assertEqual(self.opener.call_count, 3)

    def test_invalid_generated_payload_preserves_last_good_and_does_not_open(self):
        o = self.observer()
        first = self.h.add("microwave")
        self.settle(o)
        before = (self.h.out / "view-data.js").read_bytes()
        self.h.add("dishwasher")
        builder = hook.load_build_view(o.delivery.hashes["build_view"])
        original = builder.generate
        def broken(*args, **kwargs):
            result = original(*args, **kwargs)
            (kwargs["out_dir"] / "view-data.js").write_text('window.LGAX_VIEW = {"kind":"lgax-view","pages":[]};', encoding="utf-8")
            return result
        with mock.patch.object(hook, "load_build_view", return_value=builder), mock.patch.object(builder, "generate", side_effect=broken):
            self.assertEqual(self.settle(o)["status"], "generation_failed")
        self.assertEqual(before, (self.h.out / "view-data.js").read_bytes())
        self.assertEqual(self.h.state()["last_export"], first.name)
        self.opener.assert_called_once()

    def test_corrupt_existing_report_is_diagnosed_and_regenerated(self):
        o = self.observer()
        p = self.h.add("microwave")
        self.settle(o)
        view = fixture.read_view(self.h.out)
        view["report"] = "broken report object"
        (self.h.out / "view-data.js").write_text('window.LGAX_VIEW = '+json.dumps(view)+';', encoding="utf-8")
        self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["view_shape"], "invalid")
        self.assertEqual(o.delivery.deliver(p)["status"], "ready")
        self.assertIsInstance(fixture.read_view(self.h.out)["report"], dict)

    def test_diagnosis_distinguishes_missing_syntax_shape_and_stale_without_source_output(self):
        o = self.observer()
        self.h.add("microwave")
        self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["sidecar_syntax"], "missing")
        self.settle(o)
        p = self.h.out / "view-data.js"
        good = p.read_bytes()
        p.write_text('window.OTHER = {};', encoding="utf-8")
        self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["sidecar_syntax"], "invalid")
        p.write_text('window.LGAX_VIEW = {"kind":"lgax-view","pages":[]};', encoding="utf-8")
        self.assertEqual(delivery.diagnose(o.paths, o.delivery.hashes)["view_shape"], "invalid")
        p.write_bytes(good)
        self.h.add("dishwasher")
        report = delivery.diagnose(o.paths, o.delivery.hashes)
        self.assertEqual(report["current_binding"], "sidecar_stale")
        self.assertNotIn(fixture.SYNTH, json.dumps(report))
        self.assertNotIn(str(self.h.root), json.dumps(report))

    def test_native_hook_and_observer_share_open_deduplication(self):
        o = self.observer()
        p = self.h.add("microwave")
        o.delivery.deliver(p)
        with mock.patch.object(hook, "open_browser") as browser:
            # Existing hook has already handled this export, so force its normal rebuild branch.
            state = self.h.state(); state.pop("last_key", None); hook.write_state(o.paths, state)
            result = hook.run({"session_id": "native-hook"}, "codex", o.paths)
        self.assertFalse(result["opened_browser"])
        browser.assert_not_called()
        self.opener.assert_called_once()

    def test_active_observer_owns_generation_so_intermediate_hook_does_not_replace_last_good(self):
        o = self.observer()
        self.h.add("microwave")
        self.settle(o)
        before = (self.h.out / "view-data.js").read_bytes()
        lease_paths = hook.Paths(str(self.h.root))
        lease_paths.lock = str(self.h.out / ".result-watch.lock")
        lease = hook.Lock(lease_paths)
        self.assertTrue(lease.acquire(0))
        try:
            self.h.add("fourth_pending")
            with mock.patch.object(hook, "open_browser") as browser:
                self.assertFalse(hook.run({"session_id": "native-hook"}, "codex", o.paths)["changed"])
                browser.assert_not_called()
            self.assertEqual(before, (self.h.out / "view-data.js").read_bytes())
        finally:
            lease.release()

    def test_stale_office_native_id_does_not_suppress_new_observer_result(self):
        old = self.h.add("microwave")
        paths = hook.Paths(str(self.h.root))
        hook.write_state(paths, {"opened_sessions": ["codex:old-native"], "last_export": old.name,
                                 "last_open_request": {"status": "requested"}})
        office = self.h.root / "runtime-data/agent-office"
        office.mkdir()
        (office / "codex-follow.json").write_text(json.dumps({"sessions": {"old-native": {}}}), encoding="utf-8")
        o = self.observer()
        self.h.add("dishwasher")
        self.assertEqual(self.settle(o)["open_status"], "requested")
        self.opener.assert_called_once()

    def test_real_observer_process_establishes_baseline_then_generates_after_file_change(self):
        self.h.add("microwave")
        token = "d" * 32
        env = dict(os.environ, LGAX_VIEWER_NO_OPEN="1", PYTHONDONTWRITEBYTECODE="1")
        child = subprocess.Popen([sys.executable, str(self.app / "watch.py"), "watch", "--harness", str(self.h.root),
            "--no-dashboard", "--parent-pid", str(os.getpid()), "--stop-token", token, "--interval", ".05", "--max-seconds", "10"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        status = self.h.out / "watch-status.json"
        def wait_status(expected):
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                try:
                    value = json.loads(status.read_text(encoding="utf-8"))
                    if value.get("status") == expected:
                        return value
                except (OSError, ValueError):
                    pass
                time.sleep(.05)
            self.fail("observer status did not reach " + expected)
        try:
            self.assertEqual(wait_status("baseline_ignored")["pid"], child.pid)
            self.assertFalse((self.h.out / "view-data.js").exists())
            self.h.add("dishwasher")
            self.assertEqual(wait_status("ready")["open_status"], "disabled")
            self.assertEqual(delivery.diagnose(hook.Paths(str(self.h.root)), self.observer().delivery.hashes)["current_binding"], "matched_current")
        finally:
            stop = watch.stop_path(hook.Paths(str(self.h.root)), token)
            stop.write_text("stop", encoding="utf-8")
            try:
                self.assertEqual(child.wait(timeout=5), 0)
            finally:
                if child.poll() is None:
                    child.kill(); child.wait(timeout=3)

    def test_legacy_unknown_open_attempt_is_not_repeated_or_claimed_as_success(self):
        p = self.h.add("microwave")
        paths = hook.Paths(str(self.h.root))
        hook.write_state(paths, {"opened_sessions": ["codex:old"], "last_export": p.name})
        d = delivery.Delivery(self.h.root, "codex", self.opener)
        result = d.deliver(p)
        self.assertEqual(result["open_status"], "legacy_attempt_unknown")
        self.assertFalse(result["open_requested"])
        self.opener.assert_not_called()

    def test_outside_path_and_symlink_are_rejected(self):
        o = self.observer()
        outside = Path(self.tmp.name) / "outside.json"
        outside.write_text('{}', encoding="utf-8")
        with self.assertRaises(hook.IntegrityError):
            o.delivery.deliver(outside)
        link = self.h.exports / "linked.json"
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest("OS does not allow symlink creation")
        with self.assertRaises(hook.IntegrityError):
            o.paths.validate()

    def test_duplicate_watcher_lease_and_bounded_shutdown(self):
        paths = hook.Paths(str(self.h.root))
        paths.lock = str(self.h.out / ".result-watch.lock")
        lease = hook.Lock(paths)
        self.assertTrue(lease.acquire(0))
        try:
            self.assertEqual(watch.watch(self.h.root, "codex", dashboard=False, max_seconds=.1), 2)
        finally:
            lease.release()
        self.assertEqual(watch.watch(self.h.root, "codex", dashboard=False, max_seconds=.08, interval=.05), 0)
        self.assertTrue(lease.acquire(0))
        lease.release()

    def test_stop_token_is_guarded_and_parent_death_stops_only_owned_dashboard(self):
        with self.assertRaises(ValueError):
            watch.stop_path(hook.Paths(str(self.h.root)), "../outside")
        child = mock.Mock()
        child.poll.return_value = None
        with mock.patch.object(watch, "Parent") as parent, mock.patch.object(watch.subprocess, "Popen", return_value=child):
            parent.return_value.alive.return_value = False
            self.assertEqual(watch.watch(self.h.root, "claude", max_seconds=.1), 0)
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=3)
        child.kill.assert_not_called()
        parent.return_value.close.assert_called_once()

    def test_stop_token_and_diagnostic_cli_use_no_browser(self):
        token = "c" * 32
        stop = watch.stop_path(hook.Paths(str(self.h.root)), token)
        stop.parent.mkdir(parents=True)
        stop.write_text("stop", encoding="utf-8")
        self.assertEqual(watch.watch(self.h.root, "claude", dashboard=False, token=token, max_seconds=.1), 0)
        self.assertFalse(stop.exists())
        self.h.add("needs_input")
        env = dict(os.environ, LGAX_VIEWER_NO_OPEN="1", PYTHONDONTWRITEBYTECODE="1")
        for command in ("generate", "diagnose"):
            result = subprocess.run([sys.executable, str(self.app / "watch.py"), command, "--harness", str(self.h.root)],
                                    capture_output=True, text=True, encoding="utf-8", env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value["status"], "ready")
            self.assertFalse(value["display_verified"])
            self.assertNotIn(fixture.SYNTH, result.stdout)


if __name__ == "__main__":
    unittest.main()
