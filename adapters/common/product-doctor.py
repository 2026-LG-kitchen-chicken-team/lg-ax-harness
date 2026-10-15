"""Local portable readiness; never reads auth or invokes model inference."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def reporting_dependencies():
    """Check local imports only; no native AI or document rendering."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-native",action="store_true")
    args=parser.parse_args()
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    python={"version":sys.version.split()[0],"supported":sys.version_info[:2]==(3,12)}
    if not python["supported"]:
        print(json.dumps({"errors":["Python 3.12 is required; run uv sync --locked --python 3.12, then uv run python product-doctor.py"],
                          "python":python,"readiness":"unsupported_python","native_permissions":"unverified"}))
        return 1
    record=json.loads((ROOT/"product-install.json").read_text(encoding="utf-8"))
    errors=[]
    warnings=[]
    report_dependencies = reporting_dependencies()
    for name, detail in report_dependencies.items():
        if not detail["available"]:
            errors.append("Reporting dependency unavailable: " + name + "; run uv sync --locked")
    for entry in record["files"]:
        path=(ROOT/entry["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry["sha256"]:
            errors.append("Changed/missing installed file: "+entry["path"])
    cli=shutil.which(record["profile"]["cli"])
    runtime={"cli_found":cli is not None,"version":None,"authentication":"unobserved","native_discovery":"unverified","model":"unobserved"}
    if cli:
        try:
            version=subprocess.run([cli,"--version"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=10)
            runtime["version"]=(version.stdout+version.stderr).strip()[:300] if version.returncode == 0 else None
            if version.returncode:
                (errors if args.require_native else warnings).append("Optional CLI version check failed; Desktop Code readiness is separate")
        except (OSError,subprocess.TimeoutExpired):
            (errors if args.require_native else warnings).append("Optional CLI version check unavailable; Desktop Code readiness is separate")
    elif args.require_native:
        errors.append("Selected native CLI is not on PATH")
    common=subprocess.run([sys.executable,"product-tools/cli.py","doctor"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=20)
    if common.returncode:
        errors.append("Common Tool/catalog doctor failed")
    print(json.dumps({"errors":errors,"warnings":warnings,"python":python,"engine":record["engine"],"readiness":"local_only" if not runtime["version"] or warnings else "native_version_only",
                      "runtime":runtime,"common_tool_exit_code":common.returncode,"installed_skills":record["skills"],
                      "workspace_storage":"local_process_checked" if common.returncode==0 else "failed",
                      "native_permissions":"unverified","network":"not_checked","model_access":"unverified",
                      "reporting_dependencies":report_dependencies,"report_generation":"unverified",
                      "scope":"files/dependency imports/version/common Tool only; document layout/auth/AI/native discovery/permissions not verified"},ensure_ascii=False))
    return int(bool(errors))


if __name__=="__main__":
    raise SystemExit(main())
