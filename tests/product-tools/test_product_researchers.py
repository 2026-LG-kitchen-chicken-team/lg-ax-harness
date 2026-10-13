"""Real role isolation, installed instruction binding and registration failures."""
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from test_product_subagent import codex, portable, staged_source


class ResearchRoleTests(unittest.TestCase):
    def test_role_source_change_or_missing_registration_rejects_before_install(self):
        for slug, _ in codex.PRODUCT_ROLES[1:]:
            for corrupt in (True, False):
                with tempfile.TemporaryDirectory(prefix="lg-research-binding-") as folder:
                    base=Path(folder); root=staged_source(base); target=base/"installed"
                    if corrupt:
                        with (root/"agents"/(slug+".md")).open("a",encoding="utf-8") as stream:
                            stream.write("Changed after registration")
                    else:
                        path=root/"skills/manifest.json"
                        manifest=json.loads(path.read_text(encoding="utf-8"))
                        manifest["shared_files"]=[e for e in manifest["shared_files"] if e["path"]!="agents/"+slug+".md"]
                        path.write_text(json.dumps(manifest),encoding="utf-8")
                    with self.assertRaises(ValueError):
                        codex.install(target,root=root)
                    self.assertFalse(target.exists())

    def test_each_installed_research_role_is_bound_to_its_own_source(self):
        with tempfile.TemporaryDirectory(prefix="lg-research-runtime-") as folder:
            base=Path(folder); root=staged_source(base)
            for engine in ("codex","claude"):
                target=base/engine
                codex.install(target,root=root) if engine=="codex" else portable.install(target,engine,root=root)
                record=json.loads((target/"product-install.json").read_text(encoding="utf-8"))
                for slug,name in codex.PRODUCT_ROLES[1:]:
                    source=root/"agents"/(slug+".md")
                    native="."+engine+"/agents/"+slug+(".toml" if engine=="codex" else ".md")
                    entry=next(e for e in record["files"] if e["path"]==native)
                    self.assertEqual(entry["source_inputs"],[{"path":"agents/"+slug+".md","sha256":hashlib.sha256(source.read_bytes()).hexdigest()}])
                    body=(target/native).read_text(encoding="utf-8")
                    if engine=="codex":
                        role=tomllib.loads(body)
                        self.assertEqual(role["name"],name)
                        self.assertEqual(role["sandbox_mode"],"read-only")
                        self.assertFalse(role["agents"]["enabled"])
                        self.assertNotIn("model",role)
                        self.assertEqual(role["developer_instructions"].strip(),source.read_text(encoding="utf-8").strip())
                    else:
                        self.assertIn("tools: Read, Glob, Grep, WebFetch, WebSearch",body)
                        self.assertIn("disallowedTools: Bash, Write, Edit, Agent, Task, Skill, mcp__*",body)
                        self.assertEqual(body.split("---",2)[2].strip(),source.read_text(encoding="utf-8").strip())


if __name__=="__main__":
    unittest.main()
