"""Run the checked-in CI contract locally; no model inference or global installs."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dev-harness"))
from checks import digest, fingerprints, run_check, safe_path  # noqa: E402

WORKFLOW = [
    "python -m pip install --require-hashes -r product-tools/requirements.lock",
    "python dev-harness/cli.py validate",
    "python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/dev-harness -v",
    "python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/product-tools -v",
    "python scripts/check-product-assets.py",
    "python dev-harness/cli.py check --timeout 120 -- python -m unittest discover -s tests/evaluation -v",
]
APPS = ("web/prototypes/visual-viewer/app", "web/prototypes/agent-office/app")
PYTHON_PROBE = "import json,sys; print(json.dumps({'version':list(sys.version_info[:3]),'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def new_output(root: Path, relative: str) -> Path:
    path = safe_path(root, relative)
    if not path.relative_to(root).as_posix().startswith(".harness/"):
        raise ValueError("Use a new output directory below .harness/")
    path.mkdir(parents=True, exist_ok=False)
    return path


@contextmanager
def environment(values: dict):
    before = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def source_state(root: Path) -> dict:
    commands = []
    outputs = []
    for args in (["rev-parse", "HEAD"], ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
                 ["ls-files", "-z", "--cached", "--others", "--exclude-standard"]):
        argv = ["git", *args]
        completed = subprocess.run(argv, cwd=root, capture_output=True, timeout=30, check=False)
        stdout = completed.stdout.decode("utf-8", errors="strict")
        commands.append({"argv": argv, "exit_code": completed.returncode,
                         "stderr": completed.stderr.decode("utf-8", errors="replace")})
        if completed.returncode:
            raise ValueError("Git source inventory failed: " + json.dumps(commands[-1]))
        outputs.append(stdout)
    files = sorted(set(p for p in outputs[2].split("\0") if p))
    # A tracked deletion is captured by status and the before/after missing entry.
    values = {p: digest(safe_path(root, p, must_exist=True)) if (root / p).is_file() else None for p in files}
    return {"head": outputs[0].strip(), "dirty": bool(outputs[1]), "status_porcelain_z": outputs[1],
            "inputs": values, "git_commands": commands}


def changed(before: dict, after: dict) -> list[dict]:
    return [{"path": p, "before_sha256": before.get(p), "after_sha256": after.get(p)}
            for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]


def assets(source: dict) -> dict:
    return {p: sha for p, sha in source["inputs"].items()
            if p.startswith("web/prototypes/") or p == "skills/manifest.json"}


def skip_details(text: str, *, windows: bool) -> dict:
    rows = []
    platform_reasons = {"Windows Explorer invocation", "Requires actual Windows directory junction semantics",
                        "commandWindows runs only on Windows", "Windows PowerShell not available"}
    for line in text.splitlines():
        match = re.match(r"^(.+?) \.\.\. skipped (.+)$", line)
        if match:
            reason = match[2].strip("'\"")
            symlink_unavailable = (windows and reason == "OS does not allow symlink creation"
                and match[1] == "test_outside_path_and_symlink_are_rejected (test_result_observer.ObserverTests.test_outside_path_and_symlink_are_rejected)")
            rows.append({"test": match[1], "reason": reason,
                         "expected_platform_skip": (not windows and reason in platform_reasons) or symlink_unavailable})
    count = re.findall(r"\bskipped=(\d+)", text)
    reported = int(count[-1]) if count else len(rows)
    ran = re.findall(r"Ran (\d+) tests? in", text)
    return {"tests_run": int(ran[-1]) if ran else None, "reported_skips": reported, "skips": rows,
            "unexpected_skips": [r for r in rows if not r["expected_platform_skip"]],
            "skip_reasons_complete": reported == len(rows)}


def archive_receipt(root: Path, output: Path, relative: str, folder: str) -> tuple[dict, str]:
    path = safe_path(root, relative, must_exist=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    target = output / folder
    target.mkdir(parents=True, exist_ok=False)
    for name in ("receipt.json", "stdout.log", "stderr.log"):
        shutil.copyfile(path.parent / name, target / name)
    return data, (target / "receipt.json").relative_to(root).as_posix()


def execute_stage(root: Path, output: Path, stage: dict, inputs: list[str]) -> dict:
    """Keep raw command outcomes separate from stricter CI acceptance."""
    record = {**stage, "required": True}
    if stage.get("not_run_reason"):
        record.update(status="not_run", exit_code=None, receipt=None)
    else:
        try:
            raw, relative = run_check(root, stage["argv"], cwd=stage.get("cwd", "."), inputs=inputs,
                                      timeout=stage.get("timeout", 120), max_output_bytes=10 * 1024 * 1024)
            raw, copy = archive_receipt(root, output, relative, stage["id"])
            record.update(status=raw["status"], command_status=raw["status"], exit_code=raw["exit_code"],
                          error=raw["error"], receipt=relative, receipt_sha256=digest(root / relative),
                          receipt_copy=copy, inputs=raw["inputs"])
            logs = "\n".join((root / raw["logs"][name]["path"]).read_text(encoding="utf-8", errors="replace")
                             for name in ("stdout.log", "stderr.log"))
            if stage.get("suite"):
                # Workflow commands retain their existing CLI check wrapper and its inner receipt.
                child = json.loads((root / raw["logs"]["stdout.log"]["path"]).read_text(encoding="utf-8"))
                inner, inner_copy = archive_receipt(root, output, child["receipt"], stage["id"] + "-inner")
                record["inner_receipt"] = child["receipt"]
                record["inner_receipt_copy"] = inner_copy
                logs = "\n".join((root / inner["logs"][name]["path"]).read_text(encoding="utf-8", errors="replace")
                                 for name in ("stdout.log", "stderr.log"))
                record["unittest"] = skip_details(logs, windows=os.name == "nt")
                details = record["unittest"]
                if details["tests_run"] is None or details["tests_run"] == 0:
                    record.update(status="failed", acceptance_error="No completed unittest summary")
                if details["unexpected_skips"] or not details["skip_reasons_complete"]:
                    record.update(status="failed", acceptance_error="Unexpected skip or missing skip reason; see unittest")
            if stage.get("probe") and raw["status"] == "passed":
                stdout = (root / raw["logs"]["stdout.log"]["path"]).read_text(encoding="utf-8").strip()
                record["observed"] = json.loads(stdout) if stage["probe"] == "python" else stdout
                if stage["probe"] == "python" and record["observed"]["version"][:2] != [3, 12]:
                    record.update(status="failed", acceptance_error="Python 3.12 is required")
                if stage["probe"] == "uv" and not re.match(r"^uv \d+\.\d+\.\d+\b", stdout):
                    record.update(status="failed", acceptance_error="Selected executable did not report a uv version")
                if stage["probe"] == "node":
                    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", stdout)
                    version = tuple(map(int, match.groups())) if match else (0, 0, 0)
                    if not ((20, 19, 0) <= version < (21, 0, 0) or version >= (22, 12, 0)):
                        record.update(status="failed", acceptance_error="Vite requires Node ^20.19.0 or >=22.12.0")
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            record.update(status="failed", error=str(exc))
    write_new(output / (stage["id"] + ".json"), record)
    print(json.dumps({"stage": stage["id"], "status": record["status"], "exit_code": record.get("exit_code")}), flush=True)
    return record


def suite_stage(python: str, name: str, timeout: int) -> dict:
    return {"id": name.replace("/", "-"), "suite": name, "timeout": min(600, timeout + 30),
            "argv": [python, "dev-harness/cli.py", "check", "--timeout", str(timeout), "--",
                     python, "-m", "unittest", "discover", "-s", "tests/" + name, "-v"]}


def plan(profile: str, python: str, node: str | None, npm: str | None, output: str, install: bool) -> list[dict]:
    gated = {} if install else {"not_run_reason": "Installation requires explicit --install; no dependency installation performed"}
    stages = [{"id": "locked-python-dependencies", "timeout": 600,
               "argv": [python, "-m", "pip", "install", "--require-hashes", "-r", "product-tools/requirements.lock"], **gated},
              {"id": "validate", "argv": [python, "dev-harness/cli.py", "validate"]},
              suite_stage(python, "dev-harness", 120), suite_stage(python, "product-tools", 120),
              {"id": "product-assets", "argv": [python, "scripts/check-product-assets.py"]},
              suite_stage(python, "evaluation", 120)]
    if profile == "extended":
        for app in APPS:
            name = app.split("/")[-2]
            for command in ("ci", "build"):
                args = ["ci"] if command == "ci" else ["run", "build"]
                stages.append({"id": name + "-" + command, "cwd": app, "timeout": 600,
                               "argv": [node or "<missing-node>", npm or "<missing-npm-cli>", *args],
                               **(gated if command == "ci" else {})})
        stages += [suite_stage(python, "web", 570), suite_stage(python, "observer", 120),
                   suite_stage(python, "evals", 120)]
        for name in ("portable", "package"):
            stages.append({"id": "locked-" + name, "timeout": 600,
                           "argv": [python, "evals/runner/check_" + name + ".py", "--output", output + "/" + name + ".json"], **gated})
        stages.append({"id": "product-assets-after-build", "argv": [python, "scripts/check-product-assets.py"]})
    return stages


def absolute_tool(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError("Tool must be an existing absolute file path: " + value)
    return str(path.absolute())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("workflow", "extended"), default="workflow")
    parser.add_argument("--output", required=True, help="New project-relative directory below .harness/")
    parser.add_argument("--python", required=True, help="Absolute Python 3.12 executable; never installs into it")
    parser.add_argument("--uv", required=True, help="Absolute uv executable, also used by locked install unit checks")
    parser.add_argument("--node", help="Absolute Node executable, required for extended")
    parser.add_argument("--npm-cli", help="Absolute npm-cli.js; defaults to the npm installation next to Node/on PATH")
    parser.add_argument("--install", action="store_true", help="Authorize new output/venv dependencies and project-local npm ci")
    args = parser.parse_args(argv)
    root = ROOT.resolve(strict=True)
    output = new_output(root, args.output)
    report = {"schema_version": 1, "profile": args.profile, "started_at": datetime.now(timezone.utc).isoformat(),
              "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
                           "python_orchestrator": sys.version, "python_orchestrator_executable": sys.executable},
              "scope": "This host only; no Ubuntu inference from Windows, no native inference/auth/GUI acceptance",
              "install_authorized": args.install, "stages": [], "errors": []}
    try:
        python, uv, node, npm = map(absolute_tool, (args.python, args.uv, args.node, args.npm_cli))
        if args.profile == "extended" and not node:
            raise ValueError("extended requires --node")
        if args.profile == "extended" and not npm:
            candidates = [Path(node).parent / "node_modules/npm/bin/npm-cli.js"]
            located = shutil.which("npm")
            if located:
                candidates.append(Path(located).resolve())
            npm = next((str(p) for p in candidates if p.is_file() and p.suffix == ".js"), None)
            if npm is None:
                raise ValueError("Provide --npm-cli with the absolute npm-cli.js path")
        report["tools_requested"] = {"python": python, "uv": uv, "node": node, "npm_cli": npm}
        before = source_state(root)
        report["source_before"] = before
        inputs = [p for p, sha in before["inputs"].items() if sha is not None]
        workflow = (root / ".github/workflows/check.yml").read_text(encoding="utf-8")
        actual = re.findall(r"^\s*- run: (.+)$", workflow, re.MULTILINE)
        report["workflow_contract"] = {"path": ".github/workflows/check.yml", "sha256": digest(root / ".github/workflows/check.yml"),
                                       "commands": actual, "matches": actual == WORKFLOW}
        if actual != WORKFLOW:
            report["errors"].append("Workflow run commands changed; update the explicit local contract before claiming parity")
        probes = [{"id": "python-version", "argv": [python, "-c", PYTHON_PROBE], "probe": "python"},
                  {"id": "uv-version", "argv": [uv, "--version"], "probe": "uv"}]
        if node:
            probes += [{"id": "node-version", "argv": [node, "--version"], "probe": "node"}]
        if npm:
            probes += [{"id": "npm-version", "argv": [node, npm, "--version"], "probe": "npm"}]
        for probe in probes:
            report["stages"].append(execute_stage(root, output, probe, inputs))
        ready = all(stage["status"] == "passed" for stage in report["stages"])
        selected = python
        if args.install and ready:
            venv = output / "venv"
            created = execute_stage(root, output, {"id": "isolated-python", "timeout": 120,
                                    "argv": [python, "-m", "venv", str(venv)]}, inputs)
            report["stages"].append(created)
            ready = created["status"] == "passed"
            selected = str(venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        report["python_checks_executable"] = selected
        paths = [str(Path(selected).parent), str(Path(uv).parent)]
        if node:
            paths.append(str(Path(node).parent))
        env = {"PATH": os.pathsep.join(paths + [os.environ.get("PATH", "")]),
               "PYTHONUTF8": "1", "PYTHONNOUSERSITE": "1", "PIP_REQUIRE_VIRTUALENV": "true",
               "PIP_CONFIG_FILE": os.devnull, "PIP_TARGET": None, "PIP_PREFIX": None, "PIP_USER": "false",
               "PIP_DISABLE_PIP_VERSION_CHECK": "1", "UV_PYTHON": selected, "UV_PYTHON_DOWNLOADS": "never",
               "UV_PROJECT_ENVIRONMENT": None, "UV_PROJECT": None, "UV_WORKING_DIRECTORY": None,
               "LG_REPORT_UV": uv if args.install else None, "LG_REPORT_PYTHON": selected if args.install else None,
               "LGAX_VIEWER_NO_OPEN": "1", "npm_config_update_notifier": "false", "npm_config_audit": "false",
               "npm_config_fund": "false", "npm_config_global": "false"}
        with environment(env):
            if shutil.which("uv") is None or Path(shutil.which("uv")).resolve() != Path(uv).resolve():
                ready = False
                report["errors"].append("Selected uv is not the uv resolved by child scripts on PATH")
            for stage in plan(args.profile, selected, node, npm, args.output, args.install):
                if not ready:
                    stage["not_run_reason"] = "Required tool/Python/isolated environment preflight failed"
                report["stages"].append(execute_stage(root, output, stage, inputs))
        after = source_state(root)
        report["source_after"] = after
        report["tracked_assets_before"] = assets(before)
        report["tracked_assets_after"] = assets(after)
        report["tracked_asset_changes"] = changed(assets(before), assets(after))
        report["source_changes"] = changed(before["inputs"], after["inputs"])
        if report["source_changes"] or before["head"] != after["head"]:
            report["errors"].append("Source/assets changed during CI; inspect hashes; no manifest regenerated")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report["errors"].append(str(exc))
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "passed" if report["stages"] and not report["errors"] and all(
        stage["status"] == "passed" for stage in report["stages"]) else "failed"
    write_new(output / "report.json", report)
    print(json.dumps({"report": (output / "report.json").relative_to(root).as_posix(), "status": report["status"]}), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
