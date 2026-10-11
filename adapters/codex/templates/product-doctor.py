"""Inspect the installed product and local Codex readiness; no inference."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    errors = []
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
                      "scope": "files, CLI version/login status and local Tool only; native discovery/quality require actual execution"}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
