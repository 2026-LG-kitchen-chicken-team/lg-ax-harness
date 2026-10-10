"""Local portable readiness; never reads auth or invokes model inference."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-native",action="store_true")
    args=parser.parse_args()
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    record=json.loads((ROOT/"product-install.json").read_text(encoding="utf-8"))
    errors=[]
    for entry in record["files"]:
        path=(ROOT/entry["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry["sha256"]:
            errors.append("Changed/missing installed file: "+entry["path"])
    cli=shutil.which(record["profile"]["cli"])
    runtime={"cli_found":cli is not None,"version":None,"authentication":"unobserved","native_discovery":"unverified","model":"unobserved"}
    if cli:
        try:
            version=subprocess.run([cli,"--version"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=10)
            runtime["version"]=(version.stdout+version.stderr).strip()[:300]
            if version.returncode:
                errors.append("CLI version check failed")
        except (OSError,subprocess.TimeoutExpired):
            errors.append("CLI version check unavailable")
    elif args.require_native:
        errors.append("Selected native CLI is not on PATH")
    common=subprocess.run([sys.executable,"product-tools/cli.py","doctor"],cwd=ROOT,capture_output=True,text=True,encoding="utf-8",timeout=20)
    if common.returncode:
        errors.append("Common Tool/catalog doctor failed")
    print(json.dumps({"errors":errors,"engine":record["engine"],"readiness":"local_only" if not cli else "native_version_only",
                      "runtime":runtime,"common_tool_exit_code":common.returncode,"installed_skills":record["skills"],
                      "scope":"files/version/common Tool only; auth/AI/native discovery/permissions not verified"},ensure_ascii=False))
    return int(bool(errors))


if __name__=="__main__":
    raise SystemExit(main())
