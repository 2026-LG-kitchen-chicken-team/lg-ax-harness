"""Fresh ZIP extraction and locked local Tool reproduction, no native inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]


def main():
    spec=importlib.util.spec_from_file_location("source_packager",ROOT/"adapters/common/package.py")
    package=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package)
    base=Path(tempfile.mkdtemp(prefix="lg-submission-rehearsal-")).resolve()
    result=package.build("codex",base/"prepared",base/"source.zip")
    extracted=base/"extracted"
    extracted.mkdir()
    with zipfile.ZipFile(base/"source.zip") as archive:
        for name in archive.namelist():
            destination=(extracted/name).resolve()
            if not destination.is_relative_to(extracted):
                raise ValueError("Archive path escapes fresh extraction folder")
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(archive.read(name))
    manifest=json.loads((extracted/"submission-source-manifest.json").read_text(encoding="utf-8"))
    integrity=all(hashlib.sha256((extracted/f["path"]).read_bytes()).hexdigest()==f["sha256"] for f in manifest["files"])
    sync=subprocess.run(["uv","sync","--locked"],cwd=extracted,capture_output=True,text=True,encoding="utf-8",timeout=90)
    doctor=subprocess.run(["uv","run","python",".agents/skills/evidence-retrieval/scripts/run.py","doctor"],cwd=extracted,capture_output=True,text=True,encoding="utf-8",timeout=30)
    # Rebuild a portable profile using ONLY the extracted source ZIP.
    reinstall=subprocess.run(["uv","run","python","adapters/claude/install.py","--target",str(base/"claude-from-zip")],cwd=extracted,capture_output=True,text=True,encoding="utf-8",timeout=30)
    value={**result,"manifest_integrity":integrity,"extracted":str(extracted),"uv_sync_exit_code":sync.returncode,"common_skill_doctor_exit_code":doctor.returncode,
           "portable_reinstall_exit_code":reinstall.returncode,"errors":[p.stderr[-1500:] for p in (sync,doctor,reinstall) if p.returncode],
           "native_inference_executed":False,"scope":"source archive, fresh extraction, locked common Tool and portable source reinstallation only"}
    (ROOT/".harness/submission-rehearsal.json").write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(value,ensure_ascii=False))
    return 0 if integrity and all(p.returncode==0 for p in (sync,doctor,reinstall)) else 1


if __name__=="__main__":
    raise SystemExit(main())
