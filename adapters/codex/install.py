"""Create/check an isolated Codex product folder. No auth or model invocation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REVIEWER_SOURCE = "agents/product-evidence-reviewer.md"
REVIEWER_NAME = "product_evidence_reviewer"
PRODUCT_ROLES = (
    ("product-evidence-reviewer", REVIEWER_NAME),
    ("product-official-researcher", "product_official_researcher"),
    ("product-review-researcher", "product_review_researcher"),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def source_files(root):
    manifest = json.loads((root / "skills/manifest.json").read_text(encoding="utf-8"))
    listed = manifest["shared_files"] + [f for s in manifest["skills"] for f in s["files"]]
    for entry in listed:
        path = (root / entry["path"]).resolve(strict=True)
        if not path.is_relative_to(root) or digest(path.read_bytes()) != entry["sha256"]:
            raise ValueError("Changed/missing source asset: " + entry["path"])
    paths = {entry["path"] for entry in listed} | {"skills/manifest.json"}
    data = (root / manifest.get("data_path", "data/business/lg-research-v3")).resolve(strict=True)
    if not data.is_relative_to((root / "data/business").resolve()):
        raise ValueError("Business data must stay below data/business")
    paths.update(p.relative_to(root).as_posix() for p in data.iterdir() if p.is_file())
    paths.update(["THIRD_PARTY_NOTICES.md", "vendor/codex-harness/LICENSE", "vendor/codex-harness/NOTICE"])
    return manifest, sorted(paths)


def reviewer_assets(root, engine):
    """Render registered product roles, without development roles or model calls."""
    manifest = json.loads((root / "skills/manifest.json").read_text(encoding="utf-8"))
    entry = next((x for x in manifest["shared_files"] if x["path"] == REVIEWER_SOURCE), None)
    source = root / REVIEWER_SOURCE
    if entry is None or not source.is_file() or digest(source.read_bytes()) != entry["sha256"]:
        raise ValueError("Missing/changed registered product reviewer asset: " + REVIEWER_SOURCE)
    instructions = source.read_text(encoding="utf-8")
    if engine == "codex":
        templates = ((".codex/config.toml", "adapters/codex/templates/config.toml"),
                     (".codex/agents/product-evidence-reviewer.toml", "adapters/codex/templates/product-evidence-reviewer.toml"))
    elif engine == "claude":
        templates = ((".claude/agents/product-evidence-reviewer.md", "adapters/claude/templates/product-evidence-reviewer.md"),)
    else:
        raise ValueError("Unsupported reviewer runtime")
    assets = []
    for target, relative in templates:
        template = root / relative
        raw = template.read_bytes()
        text = raw.decode("utf-8")
        if "{{instructions}}" in text:
            # Escape TOML multiline literal delimiters without changing the role text.
            value = instructions.replace("\\", "\\\\").replace('"', '\\"') if target.endswith(".toml") else instructions
            text = text.replace("{{instructions}}", value)
        assets.append((target, text.encode("utf-8"), relative, digest(raw),
                       [{"path": REVIEWER_SOURCE, "sha256": entry["sha256"]}]))
    for slug, _ in PRODUCT_ROLES[1:]:
        relative_source = "agents/" + slug + ".md"
        entry = next((x for x in manifest["shared_files"] if x["path"] == relative_source), None)
        role_source = root / relative_source
        if entry is None or not role_source.is_file() or digest(role_source.read_bytes()) != entry["sha256"]:
            raise ValueError("Missing/changed registered product role asset: " + relative_source)
        extension = ".toml" if engine == "codex" else ".md"
        relative = "adapters/" + engine + "/templates/" + slug + extension
        raw = (root / relative).read_bytes()
        instructions = role_source.read_text(encoding="utf-8")
        value = instructions.replace("\\", "\\\\").replace('"', '\\"') if extension == ".toml" else instructions
        rendered = raw.decode("utf-8").replace("{{instructions}}", value).encode("utf-8")
        assets.append(("." + engine + "/agents/" + slug + extension, rendered, relative, digest(raw),
                       [{"path": relative_source, "sha256": entry["sha256"]}]))
    return assets


def install(target, root=ROOT):
    root = root.resolve(strict=True)
    target = Path(target).expanduser().resolve()
    if target == root or target.is_relative_to(root) or root.is_relative_to(target):
        raise ValueError("Product target must be outside the development repository")
    if target.exists():
        raise ValueError("Target already exists; install into a new folder without overwriting state")
    for parent in target.parents:
        if (parent / ".git").exists():
            raise ValueError("Target has an ancestor Git project; choose an isolated folder")
    manifest, paths = source_files(root)
    native_assets = reviewer_assets(root, "codex")
    entries = []
    target.mkdir(parents=True)
    # No recursive cleanup on failure: leave partial output for inspection, never reuse it.
    def write(relative, raw, source=None, source_sha=None, change="unchanged", source_inputs=None):
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        entry = {"path": relative, "sha256": digest(raw), "source": source, "source_sha256": source_sha, "transformation": change}
        if source_inputs:
            entry["source_inputs"] = source_inputs
        entries.append(entry)
    for relative in paths:
        source = root / relative
        raw = source.read_bytes()
        write(relative, raw, relative, digest(raw))
    for skill in manifest["skills"]:
        for entry in skill["files"]:
            relative = entry["path"]
            raw = (root / relative).read_bytes()
            change = "unchanged"
            if relative.endswith("SKILL.md"):
                raw = raw.decode("utf-8").replace("](../../docs/", "](../../../docs/").replace("python skills/", "python .agents/skills/").encode("utf-8")
                change = "Rewrite relative contract links and commands for .agents/skills installation"
            write(".agents/" + relative, raw, relative, entry["sha256"], change)
    for name in ("AGENTS.md", "README.md", "pyproject.toml", "uv.lock", ".gitignore", "product-doctor.py"):
        source = root / "adapters/codex/templates" / name
        raw = source.read_bytes()
        original_sha = digest(raw)
        if name == "README.md":
            raw += ("\n자연어 요청에 맞는 Skill 자동 선택이 기본이다. `/skills` 또는 `$evidence-retrieval` 등 설치된6개 이름으로 명시 호출해도 같은 업무 경로를 쓴다. "
                    "product-planning은 메인 지침이고 별도7번째 호출 Skill이 아니다. 선택 자식은 .codex/agents의 product_official_researcher/product_review_researcher/product_evidence_reviewer 역할명을 자연어로 지정한다. "
                    "Claude의 /Skill이름·@ subagent 선택과 구별하며 Codex @agent 명령을 만들지 않는다.\n"
                    "필요 본문이 현재 문맥에 없으면 get_work_instructions로 main/선택 Skill/payload만 받고 동일 문맥·지문은 known_context 신고로 중복 반환을 생략한다. "
                    "반환 receipt는 독해·이해·적용 인증이 아니다. docs/contracts/instruction-loading.md를 따른다.\n"
                    "공식 안내: https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills\n").encode("utf-8")
        write(name, raw, source.relative_to(root).as_posix(), original_sha,
              "Product-only template; README adds native invocation/loading guide" if name == "README.md" else "Product-only template")
    for relative, raw, source, source_sha, inputs in native_assets:
        write(relative, raw, source, source_sha, "Product reviewer only; model/effort inherited; native invocation unverified", inputs)
    record = {"format": "codex-product-install-v1", "source_manifest_sha256": digest((root / "skills/manifest.json").read_bytes()),
              "files": entries, "skills": [s["name"] for s in manifest["skills"]],
              "native_agents": [name for _, name in PRODUCT_ROLES], "native_verified": False,
              "scope": "regular project files only; auth/global settings not copied; discovery/quality require actual native tests"}
    (target / "product-install.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"target": str(target), "installed_skills": len(manifest["skills"]), "files": len(entries), "native_verified": False}


def check(target):
    target = Path(target).resolve(strict=True)
    manifest = json.loads((target / "product-install.json").read_text(encoding="utf-8"))
    errors = []
    for entry in manifest["files"]:
        path = (target / entry["path"]).resolve()
        if not path.is_relative_to(target) or not path.is_file() or digest(path.read_bytes()) != entry["sha256"]:
            errors.append("Changed/missing installed file: " + entry["path"])
    if "native_agents" in manifest:
        if manifest["native_agents"] != [name for _, name in PRODUCT_ROLES]:
            errors.append("Invalid product-native agent list")
        actual = sorted(p.name for p in (target / ".codex/agents").glob("*.toml"))
        if actual != sorted(slug + ".toml" for slug, _ in PRODUCT_ROLES):
            errors.append("Unexpected/missing product-native agent file")
    return {"errors": errors, "scope": "installed file integrity only; not native invocation/quality"}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = check(args.target) if args.check else install(args.target)
        print(json.dumps(result, ensure_ascii=False))
        return int(bool(result.get("errors")))
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
