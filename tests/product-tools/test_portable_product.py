"""Claude/Gemini file preparation and local Tool checks, not native quality."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("portable_installer",ROOT/"adapters/common/install.py")
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PortableInstallTests(unittest.TestCase):
    def test_each_profile_is_isolated_linked_and_executes_common_tool(self):
        with tempfile.TemporaryDirectory(prefix="lg-portable-test-") as tmp:
            for engine,profile in installer.PROFILES.items():
                target=Path(tmp)/engine
                installer.install(target,engine)
                self.assertEqual(installer.check(target)["errors"],[])
                self.assertIn("@AGENTS.md",(target/profile["entry"]).read_text(encoding="utf-8"))
                self.assertFalse((target/".agents").exists())
                self.assertFalse((target/"evals").exists())
                self.assertFalse((target/"dev-harness").exists())
                self.assertEqual(len(list((target/profile["skills"]).glob("*/SKILL.md"))),6)
                for skill in (target/profile["skills"]).glob("*/SKILL.md"):
                    for link in re.findall(r"\]\(([^)]+)\)",skill.read_text(encoding="utf-8")):
                        self.assertTrue((skill.parent/link).is_file(),link)
                wrapper=target/profile["skills"] / "evidence-retrieval/scripts/run.py"
                doctor=subprocess.run([sys.executable,str(wrapper),"doctor"],cwd=target,capture_output=True,text=True,encoding="utf-8",timeout=15)
                self.assertEqual(doctor.returncode,0,doctor.stderr)
                self.assertTrue(json.loads(doctor.stdout)["ok"])
                self.assertNotIn("login",(target/"product-doctor.py").read_text(encoding="utf-8"))

    def test_existing_target_preserved_and_profile_or_file_drift_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lg-portable-guard-test-") as tmp:
            target=Path(tmp)/"product"
            installer.install(target,"claude")
            original=(target/"product-install.json").read_bytes()
            with self.assertRaises(ValueError):
                installer.install(target,"gemini")
            self.assertEqual(original,(target/"product-install.json").read_bytes())
            (target/"CLAUDE.md").write_text("wrong",encoding="utf-8")
            self.assertTrue(installer.check(target)["errors"])
            record=json.loads(original)
            record["profile"]["cli"]="wrong"
            (target/"product-install.json").write_text(json.dumps(record),encoding="utf-8")
            self.assertIn("Invalid portable runtime profile",installer.check(target)["errors"])
        with self.assertRaises(ValueError):
            installer.install(ROOT/"must-not-install","claude")


if __name__=="__main__":
    unittest.main()
