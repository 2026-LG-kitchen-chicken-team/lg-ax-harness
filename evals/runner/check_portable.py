"""Reproduce local-only portable installation; no native inference or auth."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[2]


def main():
    spec=importlib.util.spec_from_file_location("portable_validation_installer",ROOT/"adapters/common/install.py")
    installer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    base=Path(tempfile.mkdtemp(prefix="lg-portable-validation-")).resolve()
    records=[]
    for engine in ("claude","gemini"):
        target=base/engine
        prepared=installer.install(target,engine)
        sync=subprocess.run(["uv","sync","--locked"],cwd=target,capture_output=True,text=True,encoding="utf-8",timeout=90)
        doctor=subprocess.run(["uv","run","python","product-doctor.py"],cwd=target,capture_output=True,text=True,encoding="utf-8",timeout=30) if sync.returncode==0 else None
        record={"engine":engine,"target":str(target),"installed":prepared,"uv_sync_exit_code":sync.returncode,
                "uv_sync_error":sync.stderr[-1500:] if sync.returncode else None,"integrity":installer.check(target),
                "doctor_exit_code":doctor.returncode if doctor else None,"doctor":json.loads(doctor.stdout) if doctor and doctor.stdout.strip() else None,
                "doctor_error":doctor.stderr[-1500:] if doctor and doctor.returncode else None}
        records.append(record)
    result={"records":records,"native_inference_executed":False,"scope":"isolated regular files, locked Python environment and auth-free local doctor only"}
    (ROOT/".harness/portable-validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False))
    return 0 if all(r["uv_sync_exit_code"]==0 and r["doctor_exit_code"]==0 and not r["integrity"]["errors"] for r in records) else 1


if __name__=="__main__":
    raise SystemExit(main())
