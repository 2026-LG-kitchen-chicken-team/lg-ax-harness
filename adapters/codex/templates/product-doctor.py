"""Inspect the installed product and local Codex readiness; no inference."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


def tool_python():
    """The product venv interpreter that the installed instructions name for Windows business Tools."""
    return ROOT / ".venv" / "Scripts" / "python.exe"


def check_windows_sandbox(codex, backend):
    """Run the local doctor under a real sandbox with the Tool interpreter; no model or global config writes."""
    result = {"requested_backend": backend, "status": "failed", "exit_code": None, "tool_python": ".venv/Scripts/python.exe",
              "scope": "Windows sandbox process startup with the product venv Python used by business Tools and product-local SQLite; uv run launcher reported only; no AI, browser, approval escalation or network test"}
    if sys.platform != "win32":
        result["error"] = "This optional sandbox diagnostic is Windows-only"
        return result
    python = tool_python()
    if not python.is_file():
        result["error"] = "Product venv Python is missing (.venv/Scripts/python.exe); run uv sync --locked --python 3.12"
        return result
    command = [codex]
    if backend == "mxc":
        command += ["-c", "windows.sandbox=mxc"]
    command += ["sandbox", "--include-managed-config", "--permission-profile", ":workspace", "--",
                str(python), str(ROOT / "product-doctor.py"), "--local-only"]
    started = time.monotonic()
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
        result["exit_code"] = process.returncode
        if process.returncode:
            result["error"] = (process.stderr or process.stdout).strip()[-1500:]
        else:
            local = json.loads(process.stdout)
            if local.get("errors") or local.get("workspace_storage") != "local_process_checked" or local.get("readiness") != "local_only":
                result["error"] = "Sandbox started but the product-local doctor did not pass"
            else:
                result["workspace_storage"] = local["workspace_storage"]
                result["status"] = "passed"
                # Windows business Tools start with the venv Python, so uv run is reported but not required.
                result["uv_run"] = check_sandboxed_uv(command[:command.index("--") + 1])
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        result["error"] = type(exc).__name__
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def check_sandboxed_uv(sandbox):
    """The same local doctor through `uv run`; some MXC tokens cannot let uv query the interpreter."""
    uv = shutil.which("uv")
    if not uv:
        return {"status": "failed", "required": False, "exit_code": None, "error": "uv is not on PATH"}
    try:
        process = subprocess.run([*sandbox, uv, "run", "python", "product-doctor.py", "--local-only"],
                                 cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "required": False, "exit_code": None, "error": type(exc).__name__}
    if process.returncode:
        return {"status": "failed", "required": False, "exit_code": process.returncode, "error": (process.stderr or process.stdout).strip()[-1500:]}
    return {"status": "passed", "required": False, "exit_code": 0}

ROOT = Path(__file__).resolve().parent


def reporting_dependencies():
    """Check local imports only; does not generate files or test native AI."""
    result = {}
    for distribution, module in (("python-docx", "docx"), ("openpyxl", "openpyxl"),
                                 ("reportlab", "reportlab"), ("Pillow", "PIL"), ("pypdf", "pypdf")):
        try:
            importlib.import_module(module)
            result[distribution] = {"available": True, "version": importlib.metadata.version(distribution)}
        except (ImportError, OSError, importlib.metadata.PackageNotFoundError) as exc:
            result[distribution] = {"available": False, "version": None, "error": type(exc).__name__}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stage = parser.add_mutually_exclusive_group()
    stage.add_argument("--local-only", action="store_true", help="Check local installation before CLI installation/sign-in")
    stage.add_argument("--check-sandbox", action="store_true", help="Also run a real Windows sandbox/local SQLite diagnostic; no model call")
    parser.add_argument("--sandbox-backend", choices=("mxc", "configured"), default="mxc",
                        help="For --check-sandbox: MXC or the already configured backend; never full access")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    python = {"version": sys.version.split()[0], "supported": sys.version_info[:2] == (3, 12)}
    if not python["supported"]:
        print(json.dumps({"errors": ["Python 3.12 is required; run uv sync --locked --python 3.12, then uv run python product-doctor.py"],
                          "python": python, "readiness": "unsupported_python", "native_permissions": "unverified"}))
        return 1
    errors = []
    report_dependencies = reporting_dependencies()
    for name, detail in report_dependencies.items():
        if not detail["available"]:
            errors.append("Reporting dependency unavailable: " + name + "; run uv sync --locked")
    manifest = json.loads((ROOT / "product-install.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = (ROOT / entry["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Changed/missing installed file: " + entry["path"])
    codex = shutil.which("codex")
    runtime = {"version": None, "login_status": "unobserved"}
    if args.local_only:
        runtime["login_status"] = "not_checked_local_only"
    elif not codex:
        errors.append("Codex CLI is not on PATH")
    else:
        for cli_args, field in ((["--version"], "version"), (["login", "status"], "login_status")):
            try:
                p = subprocess.run([codex, *cli_args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10)
                # Login status emits only status; credentials are never read/copied.
                runtime[field] = (p.stdout + p.stderr).strip()[:300]
                if p.returncode:
                    errors.append("Codex " + field + " failed")
            except (OSError, subprocess.TimeoutExpired):
                errors.append("Codex " + field + " unavailable")
    p = subprocess.run([sys.executable, "product-tools/cli.py", "doctor"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode:
        errors.append("Common Tool/catalog doctor failed")
    sandbox = {"status": "not_checked"}
    if args.check_sandbox and not errors:
        import re
        version = re.search(r"codex-cli (\d+)\.(\d+)\.(\d+)", runtime["version"] or "")
        if not version or tuple(map(int, version.groups())) < (0, 162, 0):
            errors.append("Sandbox diagnostic requires Codex CLI 0.162.0 or later; update using the official CLI instructions")
        else:
            sandbox = check_windows_sandbox(codex, args.sandbox_backend)
            if sandbox["status"] != "passed":
                errors.append("Windows sandbox diagnostic failed; see sandbox.error and docs/contracts/runtime-access.md")
    print(json.dumps({"errors": errors, "python": python, "runtime": runtime, "installed_skills": manifest["skills"], "common_tool_exit_code": p.returncode,
                      "readiness": "local_only" if args.local_only else "cli_status_checked",
                      "workspace_storage": "local_process_checked" if p.returncode == 0 else "failed",
                      "native_permissions": "sandbox_process_checked" if sandbox["status"] == "passed" else "unverified",
                      "sandbox": sandbox, "network": "not_checked", "model_access": "unverified",
                      "reporting_dependencies": report_dependencies, "report_generation": "unverified",
                      "scope": "files, dependency imports, CLI version/login status and local Tool only; document layout/native discovery/AI quality require actual execution"}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
