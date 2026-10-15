"""Existing-path resolution under a simulated sandbox volume-name denial; no real sandbox."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.dataset import Dataset
from product_tools.paths import real_path

ORIGINAL_RESOLVE = Path.resolve


def denied(winerror=5):
    """What Codex's Windows MXC sandbox returns for GetFinalPathNameByHandle(VOLUME_NAME_DOS)."""
    def resolve(self, strict=False):
        if strict:
            error = PermissionError(13, "Access is denied", str(self))
            error.winerror = winerror
            raise error
        return ORIGINAL_RESOLVE(self, strict)
    return patch.object(Path, "resolve", autospec=True, side_effect=resolve)


def link_directory(target, link):
    if os.name == "nt":
        import _winapi  # junctions need no symlink privilege
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


class RealPathTests(unittest.TestCase):
    def test_unrestricted_process_keeps_strict_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            self.assertEqual(real_path(folder), folder.resolve(strict=True))
            with self.assertRaises(FileNotFoundError):
                real_path(folder / "missing")

    def test_volume_name_denial_uses_existing_lexical_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(os.path.abspath(temporary))
            (folder / "file.txt").write_text("x", encoding="utf-8")
            with denied():
                self.assertEqual(real_path(folder / "sub" / ".." / "file.txt"), folder / "file.txt")
                with self.assertRaises(FileNotFoundError):
                    real_path(folder / "missing")
                data = Dataset(ROOT / "data/business/empty")
            self.assertEqual(data.models, [])

    def test_volume_name_denial_fails_closed_through_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(os.path.abspath(temporary))
            (folder / "outside").mkdir()
            (folder / "outside" / "file.txt").write_text("x", encoding="utf-8")
            link_directory(folder / "outside", folder / "link")
            with denied(), self.assertRaises(PermissionError):
                real_path(folder / "link" / "file.txt")

    def test_other_access_errors_are_not_masked(self):
        with tempfile.TemporaryDirectory() as temporary:
            with denied(winerror=32), self.assertRaises(PermissionError):
                real_path(temporary)


if __name__ == "__main__":
    unittest.main()
