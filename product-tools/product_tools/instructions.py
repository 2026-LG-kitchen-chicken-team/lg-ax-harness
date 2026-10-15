"""Return selected, verified instruction bytes; never certify model understanding."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import stat

from .contracts import MAX_BYTES, MAX_INPUT_BYTES, canonical, fail, items, obj, strict_json, text
from .paths import real_path

SKILLS = ("evidence-retrieval", "web-evidence-collection", "needs-structuring",
          "feature-comparison", "concept-writing", "review-and-revise")
PATHS = {"main": "agents/product-planning.md", "payload": "skills/review-and-revise/references/payload.md",
         **{name: f"skills/{name}/SKILL.md" for name in SKILLS}}
HEX = re.compile(r"[0-9a-f]{64}")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value, name):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        fail("invalid_input", f"{name} must be a lowercase SHA-256")
    return value


class InstructionLoader:
    def __init__(self, workspace):
        self.root = real_path(workspace)

    def _path(self, relative):
        if (not isinstance(relative, str) or "\\" in relative or ":" in relative
                or PurePosixPath(relative).is_absolute() or any(p in ("", ".", "..") for p in relative.split("/"))):
            fail("instruction_path", "Instructions must use declared project-relative regular files")
        current = self.root
        for part in relative.split("/"):
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                fail("instruction_path", "Linked instruction files/directories are not allowed")
        if not current.resolve().is_relative_to(self.root) or not current.is_file():
            fail("instruction_path", "Instruction file is outside the project or is not regular")
        return current

    def _read(self, relative, maximum=MAX_BYTES):
        path = self._path(relative)
        if path.stat().st_size > maximum:
            fail("output_limit", "Instruction file exceeds byte budget; choose a smaller instruction")
        raw = path.read_bytes()
        if len(raw) > maximum:
            fail("output_limit", "Instruction file grew beyond byte budget")
        return raw

    def _identity(self):
        raw = self._read("skills/manifest.json", MAX_INPUT_BYTES)
        manifest = strict_json(raw.decode("utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("version") != "product-skills-v1"
                or manifest.get("agent") != PATHS["main"] or not isinstance(manifest.get("skills"), list)):
            fail("instruction_identity", "Unknown product instruction manifest")
        skills = manifest["skills"]
        if (len(skills) != len(SKILLS) or any(not isinstance(s, dict) for s in skills)
                or {s.get("name") for s in skills} != set(SKILLS)
                or any(s.get("path") != PATHS.get(s.get("name")) for s in skills)):
            fail("instruction_identity", "Expected the six declared business Skills")
        entries = manifest.get("shared_files")
        if not isinstance(entries, list) or any(not isinstance(s.get("files"), list) for s in skills):
            fail("instruction_identity", "Instruction manifest lacks file bindings")
        indexed = self._index(entries + [f for s in skills for f in s["files"]])
        for relative in PATHS.values():
            if relative not in indexed:
                fail("instruction_identity", "Instruction manifest lacks a declared instruction")
        install_path = self.root / "product-install.json"
        install, native_prefix = None, None
        if install_path.exists() or install_path.is_symlink():
            install = strict_json(self._read("product-install.json", 2 * MAX_INPUT_BYTES).decode("utf-8"))
            if not isinstance(install, dict) or install.get("source_manifest_sha256") != sha(raw):
                fail("instruction_identity", "Installed product manifest does not match this source manifest")
            if install.get("format") == "codex-product-install-v1":
                native_prefix = ".agents/"
            elif install.get("format") == "portable-product-install-v1" and install.get("engine") == "claude":
                native_prefix = ".claude/"
            else:
                fail("instruction_identity", "Unsupported native product installation")
            install = self._index(install.get("files"))
        return sha(raw), indexed, install, native_prefix

    def _index(self, entries):
        if not isinstance(entries, list):
            fail("instruction_identity", "File bindings must be a list")
        indexed = {}
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                fail("instruction_identity", "Invalid instruction file binding")
            name = entry["path"]
            # Validate metadata paths even when their contents are not requested.
            if ("\\" in name or ":" in name or PurePosixPath(name).is_absolute()
                    or any(p in ("", ".", "..") for p in name.split("/")) or name in indexed):
                fail("instruction_path", "Invalid or duplicate manifest file path")
            _digest(entry.get("sha256"), "file sha256")
            indexed[name] = entry
        return indexed

    def get_work_instructions(self, payload):
        obj(payload, ("context_key", "instruction_ids"), ("known_context", "expected_manifest_sha256"))
        context = text(payload["context_key"], "current instruction context key", 200)
        requested = items(payload["instruction_ids"], "instruction_ids", len(PATHS))
        if not requested or any(not isinstance(i, str) or i not in PATHS for i in requested) or len(set(requested)) != len(requested):
            fail("instruction_id", "Select unique declared instruction IDs; paths and roles are not instruction IDs")
        manifest_sha, files, installed, prefix = self._identity()
        if "expected_manifest_sha256" in payload and _digest(payload["expected_manifest_sha256"], "expected_manifest_sha256") != manifest_sha:
            fail("instruction_version", "Instruction manifest changed; use the current version")
        known = {}
        for report in items(payload.get("known_context", []), "known_context", len(PATHS)):
            obj(report, ("instruction_id", "context_key", "manifest_sha256", "source_sha256", "returned_body_sha256"))
            key = report["instruction_id"]
            if not isinstance(key, str) or key not in PATHS or key in known:
                fail("instruction_id", "Unknown or duplicate known-context instruction")
            text(report["context_key"], "reported context key", 200)
            for name in ("manifest_sha256", "source_sha256", "returned_body_sha256"):
                _digest(report[name], name)
            known[key] = report
        results = []
        for key in requested:
            relative = PATHS[key]
            original = self._read(relative)
            source_sha = sha(original)
            if source_sha != files[relative]["sha256"]:
                fail("instruction_integrity", "Canonical instruction differs from its manifest")
            native_path = prefix + relative if prefix and relative.startswith("skills/") else None
            returned_path = native_path or relative
            body_raw = original
            if installed is not None:
                for path in (relative, returned_path):
                    entry = installed.get(path)
                    if not entry or entry.get("source") != relative or entry.get("source_sha256") != source_sha:
                        fail("instruction_integrity", "Installed instruction source binding differs")
                body_raw = self._read(returned_path)
                expected = original
                if native_path and relative.endswith("SKILL.md"):
                    expected = original.decode("utf-8").replace("](../../docs/", "](../../../docs/").replace("python skills/", "python " + prefix + "skills/").encode("utf-8")
                if body_raw != expected or sha(body_raw) != installed[returned_path]["sha256"] or installed[relative]["sha256"] != source_sha:
                    fail("instruction_integrity", "Native instruction bytes differ from the declared installation transformation")
            body = body_raw.decode("utf-8")
            body_sha = sha(body_raw)
            report = known.get(key)
            skip = report == {"instruction_id": key, "context_key": context, "manifest_sha256": manifest_sha,
                              "source_sha256": source_sha, "returned_body_sha256": body_sha}
            result = {"instruction_id": key, "name": "product-planning" if key == "main" else key,
                      "canonical_path": relative, "native_path": native_path, "returned_path": returned_path,
                      "source_sha256": source_sha, "returned_body_sha256": body_sha,
                      "status": "already_in_context_reported" if skip else "returned_to_caller"}
            if not skip:
                result["body"] = body
            results.append(result)
        value = {"format": "work-instructions-v1", "context_key": context, "manifest_sha256": manifest_sha,
                 "instructions": results,
                 "receipt": {"status": "returned_to_caller", "body_instruction_ids": [x["instruction_id"] for x in results if "body" in x],
                             "already_in_context_reported_ids": [x["instruction_id"] for x in results if "body" not in x],
                             "scope": "verified selected file bytes returned by code; native receipt, reading, application and understanding are not certified"}}
        value["receipt"]["instruction_payload_sha256"] = sha(canonical({k: value[k] for k in ("format", "context_key", "manifest_sha256", "instructions")}).encode("utf-8"))
        if len(canonical({"ok": True, "result": value}).encode("utf-8")) > MAX_BYTES:
            fail("output_limit", "Selected instructions exceed response budget; request fewer IDs; no evidence or instruction body was truncated")
        return value
