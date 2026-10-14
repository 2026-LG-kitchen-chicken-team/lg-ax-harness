"""Inspect the installed product and local Codex readiness; no inference."""
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

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
    sys.stdout.reconfigure(encoding="utf-8")
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
    if not codex:
        errors.append("Codex CLI is not on PATH")
    else:
        for args, field in ((["--version"], "version"), (["login", "status"], "login_status")):
            try:
                p = subprocess.run([codex, *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10)
                # Login status emits only status; credentials are never read/copied.
                runtime[field] = (p.stdout + p.stderr).strip()[:300]
                if p.returncode:
                    errors.append("Codex " + field + " failed")
            except (OSError, subprocess.TimeoutExpired):
                errors.append("Codex " + field + " unavailable")
    p = subprocess.run([sys.executable, "product-tools/cli.py", "doctor"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode:
        errors.append("Common Tool/catalog doctor failed")
    print(json.dumps({"errors": errors, "runtime": runtime, "installed_skills": manifest["skills"], "common_tool_exit_code": p.returncode,
                      "reporting_dependencies": report_dependencies, "report_generation": "unverified",
                      "scope": "files, dependency imports, CLI version/login status and local Tool only; document layout/native discovery/AI quality require actual execution"}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
