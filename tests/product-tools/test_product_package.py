"""Source ZIP excludes unlisted local notes and preserves existing outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"evals/runner"))
import native_eval
spec=importlib.util.spec_from_file_location("product_packager",ROOT/"adapters/common/package.py")
package=importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class ProductPackageTests(unittest.TestCase):
    def test_unlisted_notes_auth_and_runtime_excluded_and_archive_not_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="lg-source-package-test-") as tmp:
            base=Path(tmp)
            source=base/"source"
            native_eval.freeze(ROOT,source)
            for name in ["adapters/"+n for n in package.ADAPTER_FILES]+["docs/contracts/portable-product.md"]:
                target=source/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,target)
            for name in ("adapters/private-notes.md","adapters/private.py","adapters/.env.fixture","runtime-data/private.sqlite"):
                target=source/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text("TEST_ONLY_PRIVATE_SENTINEL",encoding="utf-8")
            archive=base/"source.zip"
            package.build("codex",base/"prepared",archive,root=source)
            original=archive.read_bytes()
            with zipfile.ZipFile(archive) as output:
                self.assertFalse(any("private" in name or ".env" in name for name in output.namelist()))
                self.assertFalse(any("gemini" in name.casefold() for name in output.namelist()))
                self.assertFalse(any(b"TEST_ONLY_PRIVATE_SENTINEL" in output.read(name) for name in output.namelist()))
                manifest=json.loads(output.read("submission-source-manifest.json"))
                self.assertIn("not_final_submission",manifest["purpose"])
                for entry in manifest["files"]:
                    self.assertEqual(hashlib.sha256(output.read(entry["path"])).hexdigest(),entry["sha256"])
            with self.assertRaises(ValueError):
                package.build("codex",base/"must-not-create",archive,root=source)
            self.assertEqual(original,archive.read_bytes())
            self.assertFalse((base/"must-not-create").exists())

    def test_withdrawn_runtime_rejected_before_writing(self):
        with tempfile.TemporaryDirectory(prefix="lg-package-withdrawn-") as tmp:
            target,archive=Path(tmp)/"product",Path(tmp)/"source.zip"
            with self.assertRaisesRegex(ValueError,"Unsupported"):
                package.build("gemini",target,archive)
            self.assertFalse(target.exists())
            self.assertFalse(archive.exists())


if __name__=="__main__":
    unittest.main()
