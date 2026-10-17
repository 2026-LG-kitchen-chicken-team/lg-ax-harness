"""Observe result files, or synchronously generate/diagnose them. Standard library only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import delivery
import hook


class Parent:
    def __init__(self, pid):
        self.pid, self.handle = pid, None
        if pid and os.name == "nt":
            import ctypes
            from ctypes import wintypes
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            self.kernel.OpenProcess.restype = wintypes.HANDLE
            self.kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
            self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            self.handle = self.kernel.OpenProcess(0x100000, False, pid)

    def alive(self):
        if not self.pid:
            return True
        if os.name == "nt":
            return bool(self.handle) and self.kernel.WaitForSingleObject(self.handle, 0) == 258
        try:
            os.kill(self.pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def stop_path(paths, token):
    if not token or len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        raise ValueError("invalid_stop_token")
    return Path(hook.checked_path(paths.harness, str(Path(paths.out) / (".watch-stop-" + token))))


def stop_child(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)


def office_command(harness, engine, latest=False, keep=False, open_page=False):
    office = harness / "web/prototypes/agent-office/office.py"
    if engine == "claude":
        return [sys.executable, str(office), "watch", "--claude", str(harness)]
    argv = [sys.executable, str(office), "codex", "--harness", str(harness)]
    argv += ["--latest"] if latest else ["--wait"] + ([] if keep else ["--until-complete"])
    return argv + (["--open"] if open_page else [])


class Observer:
    def __init__(self, harness, engine, opener=None, require_native=False):
        self.delivery = delivery.Delivery(harness, engine, opener)
        self.paths = self.delivery.paths
        initial = hook.newest_export(self.paths)
        self.baseline = hook.export_key(initial) if initial else None
        self.previous = self.done = None
        self.last_result = None
        self.failures = 0
        self.require_native = require_native
        self.delivered_signature = None

    def tick(self):
        latest = hook.newest_export(self.paths)
        if not latest:
            return {"status": "waiting_export"}
        key = hook.export_key(latest)
        if key == self.baseline:
            return {"status": "baseline_ignored", "export": latest.name}
        signature = hook.failure_key(self.paths, latest)
        if signature == self.done:
            return {**(self.last_result or {}), "unchanged": True}
        if signature != self.previous:
            self.previous, self.failures = signature, 0
            return {"status": "stabilizing", "export": latest.name}
        if self.failures >= 2:
            return {"status": "retry_exhausted", "export": latest.name}
        try:
            completion = {"status": "not_required"}
            if self.require_native:
                body = json.loads(delivery.read_bytes(self.paths, Path(latest.path)).decode("utf-8-sig"))
                current = (body.get("turns") or [{}])[-1].get("state") or {}
                if current.get("status") == "completed":
                    completion = delivery.native_completion(self.paths, body)
            allow_open = completion["status"] in ("not_required", "native_completed")
            if not allow_open and self.delivered_signature == signature:
                self.last_result = {**(self.last_result or {}), "status": completion["status"],
                                    "native_end_observed": False}
                return {**self.last_result, "unchanged": True}
            result = self.delivery.deliver(Path(latest.path), allow_open=allow_open)
            if result.get("status") == "ready":
                self.delivered_signature = signature
            if not allow_open and result.get("status") == "ready":
                # Build/update files now; open only after the same native request
                # has ended. Do not freeze this export's signature while waiting.
                result.update(status=completion["status"], native_end_observed=False)
            elif completion["status"] == "native_completed":
                result["native_end_observed"] = True
        except (Exception, SystemExit):
            self.failures += 1
            return {"status": "generation_failed", "attempt": self.failures, "export": latest.name}
        if result.get("status") == "ready" and result.get("open_status") in (
                "requested", "already_requested", "disabled", "retry_exhausted", "legacy_attempt_unknown"):
            self.done = signature
        if result.get("status") == "waiting_binding":
            self.done = signature  # Retry only when the export or matching web files change.
        self.last_result = result
        return result


def watch(harness, engine, *, latest=False, keep=False, open_page=False, dashboard=True,
          parent_pid=0, token=None, max_seconds=10800, interval=0.5):
    observer = Observer(harness, engine, require_native=True)
    paths = observer.paths
    lease_paths = hook.Paths(str(harness))
    lease_paths.lock = hook.checked_path(paths.harness, str(Path(paths.out) / ".result-watch.lock"))
    lease = hook.Lock(lease_paths)
    if not lease.acquire(0):
        return 2
    child = stream = None
    parent = None
    stopping = False
    previous_handlers = {}
    def stop(*_):
        nonlocal stopping
        stopping = True
    stop_file = None
    last = None
    started = time.monotonic()
    try:
        parent = Parent(parent_pid)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, stop)
        status_path = Path(hook.checked_path(paths.harness, str(Path(paths.out) / "watch-status.json")))
        stop_file = stop_path(paths, token) if token else None
        if dashboard:
            office = harness / "runtime-data/agent-office"
            hook.checked_path(paths.harness, str(office / "observer.log"))
            office.mkdir(parents=True, exist_ok=True)
            stream = (office / "observer.log").open("a", encoding="utf-8")
            child = subprocess.Popen(office_command(harness, engine, latest, keep, open_page), cwd=harness,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        while not stopping and parent.alive() and time.monotonic() - started < max_seconds:
            if stop_file and stop_file.exists():
                break
            result = observer.tick()
            if result != last:
                paths.validate()
                tmp = status_path.with_suffix(".json.tmp")
                hook.checked_path(paths.harness, str(tmp))
                tmp.write_text(json.dumps({**result, "pid": os.getpid(), "engine": engine,
                    "observer_token": token, "observer_ready": True,
                    "display_verified": False}, ensure_ascii=False) + "\n", encoding="utf-8")
                os.replace(tmp, status_path)
                last = result
            time.sleep(interval)
        return 0
    finally:
        try:
            stop_child(child)
        finally:
            try:
                if stream:
                    stream.close()
                if stop_file and stop_file.exists():
                    hook.checked_path(paths.harness, str(stop_file))
                    stop_file.unlink()
            finally:
                if parent:
                    parent.close()
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)
                lease.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("watch", "diagnose", "generate"))
    parser.add_argument("--harness", type=Path, default=HERE.parents[2])
    parser.add_argument("--engine", choices=("codex", "claude"), default="codex")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--keep-following", action="store_true")
    parser.add_argument("--open", action="store_true", help="Open the dashboard once; result open requests are automatic")
    parser.add_argument("--no-dashboard", action="store_true")
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--stop-token")
    parser.add_argument("--max-seconds", type=float, default=10800)
    parser.add_argument("--interval", type=float, default=0.5)
    a = parser.parse_args(argv)
    harness = a.harness.resolve(strict=True)
    if a.max_seconds <= 0 or a.interval < 0.05:
        parser.error("positive bounded duration and interval >= 0.05 required")
    if a.command == "watch":
        return watch(harness, a.engine, latest=a.latest, keep=a.keep_following, open_page=a.open,
                     dashboard=not a.no_dashboard, parent_pid=a.parent_pid, token=a.stop_token,
                     max_seconds=a.max_seconds, interval=a.interval)
    d = delivery.Delivery(harness, a.engine)
    if a.command == "generate":
        latest = hook.newest_export(d.paths)
        result = d.deliver(Path(latest.path), allow_open=False) if latest else {"status": "waiting_export"}
    else:
        result = delivery.diagnose(d.paths, d.hashes)
        result["status"] = "ready" if (result["view_shape"] == "valid" and result["index_matches_installed"]
            and result["current_binding"] in ("matched_current", "request_only")) else "not_ready"
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status", "ready") == "ready" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit) and (exc.code is None or isinstance(exc.code, int)):
            raise
        # Diagnostics never print exception text, source bodies or private absolute paths.
        print(json.dumps({"status": "diagnostic_failed", "category": type(exc).__name__, "display_verified": False}))
        raise SystemExit(1)
