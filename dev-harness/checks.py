"""Execute bounded argv checks and verify local audit receipts (not signed proof)."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import time
import uuid


def safe_path(root: Path, relative: str, *, must_exist: bool = False) -> Path:
    root = root.resolve(strict=True)
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Expected project-relative path: {relative!r}")
    raw = root / candidate
    resolved = raw.resolve(strict=must_exist)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes project: {relative}")
    for component in [raw, *raw.parents]:
        if component == root:
            break
        if component.exists() or component.is_symlink():
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError(f"Symlink/reparse path is unsupported: {relative}")
    return raw


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprints(root: Path, inputs: list[str]) -> dict[str, str]:
    values = {}
    for item in sorted(set(inputs)):
        path = safe_path(root, item, must_exist=True)
        if not path.is_file():
            raise ValueError(f"Check inputs must be individual files: {item}")
        values[path.relative_to(root).as_posix()] = digest(path)
    return values


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_check(root: Path, argv: list[str], *, cwd: str = ".", inputs: list[str] | None = None,
              timeout: float = 60, max_output_bytes: int = 1048576, binding: dict | None = None) -> tuple[dict, str]:
    root = root.resolve(strict=True)
    if not argv or any(not isinstance(x, str) or not x for x in argv):
        raise ValueError("A nonempty command argv is required")
    if not 0 < timeout <= 600 or not 0 < max_output_bytes <= 10485760:
        raise ValueError("timeout must be 0–600 seconds; output limit 1–10485760 bytes")
    work = safe_path(root, cwd, must_exist=True)
    before = fingerprints(root, inputs or [])
    check_id = uuid.uuid4().hex
    directory = safe_path(root, ".harness/checks/" + check_id)
    directory.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    code, status, error = None, "not_run", None
    with (directory / "stdout.log").open("wb") as out, (directory / "stderr.log").open("wb") as err:
        try:
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            process = subprocess.Popen(argv, cwd=work, env={**os.environ, "PYTHONUTF8": "1"}, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       shell=False, **options)
            try:
                code = process.wait(timeout=timeout)
                status = "passed" if code == 0 else "failed"
            except subprocess.TimeoutExpired:
                status = "timeout"
                try:
                    if os.name == "nt":
                        cleanup = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                                                 creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                        if cleanup.returncode:
                            error = f"Process-tree cleanup exit {cleanup.returncode}"
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    error = f"Process-tree cleanup failed: {exc}"
                finally:
                    try:
                        process.kill()
                        code = process.wait(timeout=10)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        error = f"{error or ''}; direct cleanup failed: {exc}"
        except OSError as exc:
            error = str(exc)
            status = "not_run"
    logs = {}
    for name in ("stdout.log", "stderr.log"):
        path = directory / name
        size = path.stat().st_size
        truncated = size > max_output_bytes
        if truncated:
            with path.open("r+b") as stream:
                stream.truncate(max_output_bytes)
            if status == "passed":
                status = "output_limit"
        logs[name] = {"path": path.relative_to(root).as_posix(), "sha256": digest(path),
                      "original_bytes": size, "truncated": truncated}
    data = {"schema_version": 1, "check_id": check_id, "argv": argv, "cwd": cwd,
            "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.monotonic() - clock, 4), "timeout_seconds": timeout,
            "status": status, "exit_code": code, "error": error, "inputs": before, "logs": logs,
            "binding": binding}
    target = directory / "receipt.json"
    write_json(target, data)
    return data, target.relative_to(root).as_posix()


def verify_receipt(root: Path, relative: str, *, require_pass: bool = True) -> dict:
    path = safe_path(root, relative, must_exist=True)
    if not path.relative_to(root.resolve()).as_posix().startswith(".harness/checks/"):
        raise ValueError("Receipt must be under .harness/checks/")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not data.get("argv") or not data.get("started_at") or not data.get("finished_at"):
        raise ValueError("Incomplete check receipt")
    if require_pass and (data.get("status") != "passed" or type(data.get("exit_code")) is not int or data["exit_code"] != 0):
        raise ValueError(f"Check did not pass: {data.get('status')} / {data.get('exit_code')}")
    if not isinstance(data.get("inputs"), dict) or not isinstance(data.get("logs"), dict):
        raise ValueError("Missing input/log fingerprints")
    if fingerprints(root.resolve(), list(data["inputs"])) != data["inputs"]:
        raise ValueError("Check inputs changed; rerun the command")
    for name in ("stdout.log", "stderr.log"):
        log = data["logs"].get(name, {})
        target = safe_path(root, log.get("path", ""), must_exist=True)
        if target.parent != path.parent or target.name != name or digest(target) != log.get("sha256"):
            raise ValueError("Check log fingerprint/path mismatch")
    return data
