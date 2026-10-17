"""Build a reproducible product-source rehearsal ZIP; excludes runtime/private data."""
import argparse
import hashlib
import importlib.util
import json
import os
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

# Frontend sources are an explicit opt-in for source submission, never needed by
# the judge runtime ZIP. Copy build inputs, not an arbitrary checkout subtree.
FRONTENDS = (
    ("web/prototypes/visual-viewer/app", "build", "web/prototypes/visual-viewer/index.html",
     ("index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts", "src/main.tsx",
      "scripts/publish.mjs", "scripts/jinha-report.mjs", "scripts/planner-report.mjs",
      "vendor/jinha-report/index.html", "vendor/jinha-report/report-data-adapter.js", "vendor/jinha-report/report-app.js",
      "vendor/jinha-report/styles.css", "vendor/jinha-report/result-report.css", "vendor/jinha-report/SOURCE.md"), ()),
    ("web/prototypes/agent-office/app", "build", "web/prototypes/agent-office/index.html",
     ("index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts",
      "src/main.tsx", "scripts/publish.mjs"), ()),
    ("web/prototypes/control-room/factory-dashboard", "build:office", "web/prototypes/agent-office/factory.html",
     ("index.html", "package.json", "package-lock.json", "vite.config.js", "src/main.jsx", "scripts/publish-office.mjs"),
     ("shared/skill-operations.json", "APPROVED-UI-IMAGE-SOURCES.md", "RESEARCHER-SEATED-ASSET.md",
      "public/characters/researcher-team-v1.png", "public/characters/researcher-work-v1.png",
      "public/characters/researcher-walk-v2.png", "public/characters/researcher-seated-v1.png",
      "public/workshops/approved-researchers-original-v1.png", "public/workshops/ivory-sage-empty-v1.png",
      "public/environment/ivory-sage-wall-v2.png")),
)
FRONTEND_TREES = ("src", "scripts", "vendor")
FRONTEND_SUFFIXES = frozenset((".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts",
                              ".css", ".html", ".svg", ".png", ".jpg", ".jpeg", ".webp",
                              ".gif", ".ico", ".woff", ".woff2", ".ttf", ".otf"))
FRONTEND_NOTICES = frozenset(("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md", "NOTICE.txt",
                            "COPYING", "COPYING.md", "COPYING.txt", "SOURCE.md"))
FRONTEND_EXCLUDED = frozenset(("node_modules", "dist", "dist-office", ".git", ".harness", ".venv",
                             "__pycache__", "runtime-data", "tests", "test", "fixtures", "__tests__",
                             "auth.json", "settings.local.json"))


def frontend_sources(root):
    """Read a bounded build-source allowlist; do not follow links or copy caches."""
    files, apps = {}, []

    def read(app, name):
        path = app / name
        # Checking every component also rejects directory links/junctions even
        # when they happen to resolve inside the source checkout.
        for component in (path, *path.parents):
            if component == root:
                break
            if component.is_symlink() or component.is_junction():
                raise ValueError("Linked frontend source: " + path.relative_to(root).as_posix())
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError("Invalid frontend source: " + str(path))
        name = path.relative_to(root).as_posix()
        files[name] = path.read_bytes()
        return name

    for relative, script, output, required, assets in FRONTENDS:
        app = root / relative
        start = set(files)
        for name in (*required, *assets):
            read(app, name)
        for name in FRONTEND_NOTICES:
            if (app / name).is_file():
                read(app, name)
        for tree in FRONTEND_TREES:
            directory = app / tree
            if not directory.exists():
                if tree == "src" or tree == "scripts":
                    raise ValueError("Missing frontend build source: " + str(directory))
                continue
            if directory.is_symlink() or directory.is_junction():
                raise ValueError("Linked frontend source directory: " + str(directory))
            for folder, directories, names in os.walk(directory, followlinks=False):
                directories[:] = sorted(name for name in directories
                                        if name not in FRONTEND_EXCLUDED and not name.startswith("."))
                for name in directories:
                    child = Path(folder) / name
                    if child.is_symlink() or child.is_junction():
                        raise ValueError("Linked frontend source directory: " + str(child))
                for name in sorted(names):
                    path = Path(folder) / name
                    if (name.startswith(".") or name in FRONTEND_EXCLUDED
                            or (path.suffix.lower() not in FRONTEND_SUFFIXES and name not in FRONTEND_NOTICES)):
                        continue
                    read(app, path.relative_to(app))
        selected = sorted(set(files) - start)
        apps.append({"path": relative, "install": "npm ci", "build": "npm run " + script,
                     "output": output, "source_files": len(selected),
                     "scope": "Locked production build inputs; no dependency cache or evaluation/runtime data"})
    return files, {"included": True, "apps": apps,
                   "scope": "Sources for the three bundled HTML pages; Node/npm and locked npm install are build prerequisites. "
                            "The judge runtime needs neither Node nor these source trees; native/GUI/quality checks are separate."}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(engine,target,archive,root=ROOT,*,include_frontends=False):
    if engine not in ("codex", "claude"):
        raise ValueError("Unsupported runtime profile")
    root=root.resolve(strict=True)
    target,archive=Path(target).resolve(),Path(archive).resolve()
    if archive.exists() or archive.is_relative_to(root) or archive.is_relative_to(target):
        raise ValueError("Use a new archive outside the repository and installed folder")
    if type(include_frontends) is not bool:
        raise ValueError("include_frontends must be boolean")
    frontend_files, frontend_manifest = (frontend_sources(root) if include_frontends else
        ({}, {"included": False, "apps": [], "scope": "Bundled HTML runtime only; original frontend build sources omitted"}))
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
    files.update(frontend_files)
    for name in files:
        parts=Path(name).parts
        if Path(name).is_absolute() or ".." in parts or any(p in parts for p in ("runtime-data",".harness",".venv",".git","__pycache__")) or Path(name).name.startswith(".env"):
            raise ValueError("Forbidden archive path: "+name)
    manifest={"purpose":"submission_source_rehearsal_not_final_submission","runtime_profile":engine,"native_support":"see release validation; file installation alone does not prove native support",
              "frontends":frontend_manifest,
              "files":[{"path":name,"sha256":hashlib.sha256(raw).hexdigest()} for name,raw in sorted(files.items())],
              "excluded":"runtime DB/logs/auth/global settings/dependencies/development roles/evaluation rubrics/attachment PDFs",
              "limits":"No new AI/native discovery or effect validation; actual video/presentation/final submission requirements pending"}
    files["submission-source-manifest.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,"x",compression=zipfile.ZIP_DEFLATED) as output:
        for name,raw in sorted(files.items()):
            output.writestr(name,raw)
    return {"archive":str(archive),"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"files":len(files),"purpose":manifest["purpose"],
            "include_frontends":include_frontends}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine",choices=("codex","claude"),required=True)
    parser.add_argument("--target",type=Path,required=True)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--include-frontends",action="store_true",help="Include locked build sources for all three bundled HTML pages (not needed by judge users)")
    args=parser.parse_args()
    print(json.dumps(build(args.engine,args.target,args.archive,include_frontends=args.include_frontends),ensure_ascii=False))


if __name__=="__main__":
    raise SystemExit(main())
