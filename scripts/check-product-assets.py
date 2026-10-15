"""Check packaged instructions/scripts, not automatic invocation or AI quality."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    manifest = json.loads((ROOT / "skills/manifest.json").read_text(encoding="utf-8"))
    optional = manifest.get('optional_agents', [])
    registered = {e['path'] for e in manifest['shared_files']}
    if not isinstance(optional,list) or any(not isinstance(p,str) or p not in registered for p in optional):
        errors.append('Optional product role must be a registered shared asset')
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
            elif path.suffix == ".md":
                for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                    if "://" not in target:
                        reference = (path.parent / target.split("#")[0]).resolve()
                        if not reference.is_relative_to(ROOT) or not reference.is_file():
                            errors.append("Missing/outside skill reference: " + entry["path"] + " -> " + target)
    for entry in manifest["shared_files"]:
        path = (ROOT / entry["path"]).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Changed/missing shared asset: " + entry["path"])
    def normalized(name):
        return name.casefold().replace("_", "-")
    requirement_pins = {normalized(name): version for name, version in re.findall(r"^([A-Za-z0-9_-]+)==([^\s]+)", (ROOT / "product-tools/requirements.in").read_text(encoding="utf-8"), re.M)}
    locked_pins = {normalized(name): version for name, version in re.findall(r"^([A-Za-z0-9_-]+)==([^\s]+)", (ROOT / "product-tools/requirements.lock").read_text(encoding="utf-8"), re.M)}
    template = tomllib.loads((ROOT / "adapters/codex/templates/pyproject.toml").read_text(encoding="utf-8"))
    template_pins = {normalized(name): version for name, version in (value.split("==", 1) for value in template["project"]["dependencies"])}
    uv_lock = tomllib.loads((ROOT / "adapters/codex/templates/uv.lock").read_text(encoding="utf-8"))
    uv_pins = {normalized(package["name"]): package["version"] for package in uv_lock["package"]}
    if requirement_pins != template_pins:
        errors.append("Product requirements and installed template dependency pins differ")
    for name, version in requirement_pins.items():
        if locked_pins.get(name) != version or uv_pins.get(name) != version:
            errors.append("Reporting dependency lock mismatch: " + name)
    print(json.dumps({"errors": errors, "product_agents": 1, "optional_product_roles": len(optional) if isinstance(optional,list) else None, "product_skills": 6, "scope": "main Agent asset and optional role assets separately; asset/reference/dependency-lock consistency only; native runs and AI quality not verified"}, ensure_ascii=False))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
