"""Build a reproducible product-source rehearsal ZIP; excludes runtime/private data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
ADAPTER_FILES=(
    "common/install.py","common/package.py","common/product-doctor.py",
    "common/package_judge.py","common/judge.py",
    "codex/install.py","codex/templates/AGENTS.md","codex/templates/README.md",
    "codex/templates/pyproject.toml","codex/templates/uv.lock",
    "codex/templates/config.toml","codex/templates/product-evidence-reviewer.toml",
    "codex/templates/product-official-researcher.toml","codex/templates/product-review-researcher.toml",
    "codex/templates/.gitignore","codex/templates/product-doctor.py",
    "claude/install.py","claude/templates/CLAUDE.md",
    "claude/templates/product-evidence-reviewer.md",
    "claude/templates/product-official-researcher.md","claude/templates/product-review-researcher.md",
) + tuple("common/launchers/start_" + engine + "_" + ui + "." + ext
          for engine in ("claude", "codex") for ui in ("gui", "cli") for ext in ("cmd", "sh"))


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(engine,target,archive,root=ROOT):
    if engine not in ("codex", "claude"):
        raise ValueError("Unsupported runtime profile")
    root=root.resolve(strict=True)
    target,archive=Path(target).resolve(),Path(archive).resolve()
    if archive.exists() or archive.is_relative_to(root) or archive.is_relative_to(target):
        raise ValueError("Use a new archive outside the repository and installed folder")
    installer=load(root/"adapters/codex/install.py","package_codex") if engine=="codex" else load(root/"adapters/common/install.py","package_portable")
    installer.install(target,root=root) if engine=="codex" else installer.install(target,engine,root=root)
    record=json.loads((target/"product-install.json").read_text(encoding="utf-8"))
    files={entry["path"]:(target/entry["path"]).read_bytes() for entry in record["files"]}
    files["product-install.json"]=(target/"product-install.json").read_bytes()
    # Include original adapter source/templates for reproducing another fresh folder.
    for name in ADAPTER_FILES:
        path=(root/"adapters"/name).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Invalid adapter source: "+name)
        files["adapters/"+name]=path.read_bytes()
    for name in ("docs/contracts/portable-product.md",):
        files[name]=(root/name).read_bytes()
    for name in files:
        parts=Path(name).parts
        if Path(name).is_absolute() or ".." in parts or any(p in parts for p in ("runtime-data",".harness",".venv",".git","__pycache__")) or Path(name).name.startswith(".env"):
            raise ValueError("Forbidden archive path: "+name)
    manifest={"purpose":"submission_source_rehearsal_not_final_submission","runtime_profile":engine,"native_support":"see release validation; file installation alone does not prove native support",
              "files":[{"path":name,"sha256":hashlib.sha256(raw).hexdigest()} for name,raw in sorted(files.items())],
              "excluded":"runtime DB/logs/auth/global settings/dependencies/development roles/evaluation rubrics/attachment PDFs",
              "limits":"No new AI/native discovery or effect validation; actual video/presentation/final submission requirements pending"}
    files["submission-source-manifest.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as output:
        for name,raw in sorted(files.items()):
            output.writestr(name,raw)
    return {"archive":str(archive),"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":len(files),"purpose":manifest["purpose"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine",choices=("codex","claude"),required=True)
    parser.add_argument("--target",type=Path,required=True)
    parser.add_argument("--archive",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build(args.engine,args.target,args.archive),ensure_ascii=False))


if __name__=="__main__":
    raise SystemExit(main())
