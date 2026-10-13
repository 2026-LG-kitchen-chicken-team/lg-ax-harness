"""Product-native role installation/isolation; does not certify native delegation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = "agents/product-evidence-reviewer.md"


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


codex = load("adapters/codex/install.py", "reviewer_codex_installer")
portable = load("adapters/common/install.py", "reviewer_portable_installer")


def staged_source(base):
    """An explicitly separate fixture manifest while parent owns source registration."""
    target = base / "source"
    manifest = json.loads((ROOT / "skills/manifest.json").read_text(encoding="utf-8"))
    entries = manifest["shared_files"] + [e for skill in manifest["skills"] for e in skill["files"]]
    paths = {e["path"] for e in entries} | {CANONICAL, "THIRD_PARTY_NOTICES.md", "vendor/codex-harness/LICENSE", "vendor/codex-harness/NOTICE"}
    data = ROOT / manifest["data_path"]
    paths.update(p.relative_to(ROOT).as_posix() for p in data.iterdir() if p.is_file())
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copytree(ROOT / "adapters", target / "adapters")
    # Only the new role registration differs. Never refresh unrelated source hashes.
    canonical_entry = {"path": CANONICAL, "sha256": hashlib.sha256((target / CANONICAL).read_bytes()).hexdigest()}
    manifest["shared_files"] = [e for e in manifest["shared_files"] if e["path"] != CANONICAL] + [canonical_entry]
    (target / "skills/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return target


class ProductReviewerInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-product-reviewer-")
        self.base = Path(self.temp.name).resolve()
        self.source = staged_source(self.base)

    def tearDown(self):
        self.temp.cleanup()

    def install(self, engine):
        target = self.base / engine
        if engine == "codex":
            codex.install(target, root=self.source)
        else:
            portable.install(target, engine, root=self.source)
        return target

    def test_product_roles_are_installed_without_development_roles(self):
        for engine, folder, suffix in (("codex", ".codex/agents", ".toml"), ("claude", ".claude/agents", ".md")):
            target = self.install(engine)
            self.assertEqual([p.name for p in (target / folder).glob("*" + suffix)], sorted(slug + suffix for slug, _ in codex.PRODUCT_ROLES))
            record = json.loads((target / "product-install.json").read_text(encoding="utf-8"))
            self.assertFalse(record["native_verified"])
            self.assertEqual(len(record["skills"]), 6)
            self.assertTrue((target / CANONICAL).is_file())
            self.assertFalse((target / "dev-harness").exists())
            self.assertFalse((target / "evals").exists())
            self.assertEqual((codex if engine == "codex" else portable).check(target)["errors"], [])

    def test_codex_role_config_resolves_after_relocation_and_inherits_model(self):
        target = self.install("codex")
        moved = self.base / "moved-codex"
        target.rename(moved)
        config_file = moved / ".codex/config.toml"
        config = tomllib.loads(config_file.read_text(encoding="utf-8"))
        self.assertTrue(config["agents"]["enabled"])
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 2)
        role_path = (config_file.parent / config["agents"]["product_evidence_reviewer"]["config_file"]).resolve(strict=True)
        self.assertTrue(role_path.is_relative_to(moved))
        role = tomllib.loads(role_path.read_text(encoding="utf-8"))
        self.assertEqual(role["name"], "product_evidence_reviewer")
        self.assertEqual(role["sandbox_mode"], "read-only")
        self.assertFalse(role["agents"]["enabled"])
        self.assertEqual(role["web_search"], "disabled")
        for value in (config, role):
            self.assertNotIn("model", value)
            self.assertNotIn("model_reasoning_effort", value)
            self.assertNotIn("mcp_servers", value)
        self.assertEqual(role["developer_instructions"].strip(), (moved / CANONICAL).read_text(encoding="utf-8").strip())
        self.assertEqual(codex.check(moved)["errors"], [])

    def test_claude_role_has_read_tools_and_no_nested_agent_tool(self):
        target = self.install("claude")
        text = (target / ".claude/agents/product-evidence-reviewer.md").read_text(encoding="utf-8")
        frontmatter, body = text.split("---", 2)[1:]
        fields = dict(line.split(":", 1) for line in frontmatter.strip().splitlines())
        fields = {key.strip(): value.strip() for key, value in fields.items()}
        self.assertEqual(fields["name"], "product-evidence-reviewer")
        self.assertEqual(fields["model"], "inherit")
        self.assertEqual({x.strip() for x in fields["tools"].split(",")}, {"Read", "Glob", "Grep"})
        for blocked in ("Bash", "Write", "Edit", "Agent", "Task", "Skill", "mcp__*"):
            self.assertIn(blocked, {x.strip() for x in fields["disallowedTools"].split(",")})
        self.assertEqual(fields["maxTurns"], "6")
        self.assertEqual(body.strip(), (target / CANONICAL).read_text(encoding="utf-8").strip())
        self.assertFalse((target / ".codex").exists())
        guide = (target / "README.md").read_text(encoding="utf-8")
        self.assertIn("Desktop Code GUI", guide)
        self.assertIn("별도 CLI 설치·로그인을 요구하지 않는다", guide)
        self.assertIn("CLI를 선택하는 경우에만", guide)
        self.assertIn("`--require-native`는 CLI 진단 선택", guide)

    def test_missing_registration_is_rejected_before_target_is_created(self):
        path = self.source / "skills/manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["shared_files"] = [e for e in manifest["shared_files"] if e["path"] != CANONICAL]
        path.write_text(json.dumps(manifest), encoding="utf-8")
        target = self.base / "unregistered"
        with self.assertRaisesRegex(ValueError, "registered product reviewer"):
            codex.install(target, root=self.source)
        self.assertFalse(target.exists())

    def test_modified_role_and_unrecorded_role_are_detected(self):
        for engine, folder, suffix in (("codex", ".codex/agents", ".toml"), ("claude", ".claude/agents", ".md")):
            target = self.install(engine)
            checker = codex.check if engine == "codex" else portable.check
            role = target / folder / ("product-evidence-reviewer" + suffix)
            role.write_text("changed", encoding="utf-8")
            self.assertTrue(checker(target)["errors"])
            (target / folder / ("development-role" + suffix)).write_text("extra", encoding="utf-8")
            self.assertIn("Unexpected/missing product-native agent file", checker(target)["errors"])

    def test_existing_target_is_never_overwritten_and_source_hash_is_recorded(self):
        target = self.install("codex")
        original = (target / "product-install.json").read_bytes()
        with self.assertRaises(ValueError):
            codex.install(target, root=self.source)
        self.assertEqual(original, (target / "product-install.json").read_bytes())
        entry = next(e for e in json.loads(original)["files"] if e["path"] == ".codex/agents/product-evidence-reviewer.toml")
        self.assertEqual(entry["source_inputs"], [{"path": CANONICAL, "sha256": hashlib.sha256((self.source / CANONICAL).read_bytes()).hexdigest()}])
        self.assertEqual(entry["source_sha256"], hashlib.sha256((self.source / entry["source"]).read_bytes()).hexdigest())

    def test_native_role_contract_does_not_claim_time_or_quality_guarantees(self):
        text = (self.source / CANONICAL).read_text(encoding="utf-8")
        for marker in ("90초", "600초", "unknown", "partial", "checked_claim_ids", "unreviewed_sources", "A/B", "OS 권한"):
            self.assertIn(marker, text)
        for engine in ("codex", "claude"):
            target = self.install(engine)
            instructions = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("210초", instructions)
            self.assertIn("skipped/not_run", instructions)
            self.assertNotIn("개발 역할·다른 모델/Agent를 내부 호출하지 않는다", instructions)

    def test_installed_business_tool_runs_with_new_native_role_files(self):
        target = self.install("codex")
        command = [sys.executable, ".agents/skills/evidence-retrieval/scripts/run.py", "doctor"]
        process = subprocess.run(command, cwd=target, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["ok"])
        self.assertEqual(codex.check(target)["errors"], [])


if __name__ == "__main__":
    unittest.main()
