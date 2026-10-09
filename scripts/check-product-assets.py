"""Check packaged instructions/scripts, not automatic invocation or AI quality."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    manifest = json.loads((ROOT / "skills/manifest.json").read_text(encoding="utf-8"))
    if len(manifest["skills"]) != 6:
        errors.append("Expected six product skills")
    for skill in manifest["skills"]:
        body = (ROOT / skill["path"]).read_text(encoding="utf-8")
        if not body.startswith("---\n") or not re.search(r"^name: " + re.escape(skill["name"]) + r"$", body, re.M):
            errors.append("Invalid name/frontmatter: " + skill["name"])
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if "://" not in target and not (ROOT / skill["path"]).parent.joinpath(target.split("#")[0]).is_file():
                errors.append("Missing reference: " + target)
        for entry in skill["files"]:
            path = (ROOT / entry["path"]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                errors.append("Changed/missing skill asset: " + entry["path"])
    for entry in manifest["shared_files"]:
        path = (ROOT / entry["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Changed/missing shared asset: " + entry["path"])
    print(json.dumps({"errors": errors, "product_agents": 1, "product_skills": 6, "scope": "asset consistency only; native installation/discovery/AI quality not verified"}, ensure_ascii=False))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
