"""CLI discovery probes known local files; never logs in or starts a model."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('claude_discovery_judge', ROOT / 'adapters/common/judge.py')
judge = importlib.util.module_from_spec(spec); spec.loader.exec_module(judge)

class ClaudeDiscoveryTests(unittest.TestCase):
    def test_existing_path_and_local_install_take_precedence(self):
        with tempfile.TemporaryDirectory() as name:
            home = Path(name); local = home / '.local/bin' / ('claude.exe' if os.name == 'nt' else 'claude')
            local.parent.mkdir(parents=True); local.write_bytes(b'fixture, never run')
            with mock.patch.object(judge.Path, 'home', return_value=home), mock.patch.object(judge.shutil, 'which', return_value='on-path'), mock.patch.object(judge, 'desktop_claude_cli') as fallback:
                self.assertEqual(judge.find_cli('claude'), 'on-path'); fallback.assert_not_called()
            with mock.patch.object(judge.Path, 'home', return_value=home), mock.patch.object(judge.shutil, 'which', return_value=None), mock.patch.object(judge, 'desktop_claude_cli') as fallback:
                self.assertEqual(judge.find_cli('claude'), str(local)); fallback.assert_not_called()

    def test_known_cache_requires_valid_executable_and_keeps_auth_separate(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name) / 'Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/claude-code'
            bad = base / '2.1.300/hash/claude.exe'; good = base / '2.1.299/hash/claude.exe'
            for path in (bad, good): path.parent.mkdir(parents=True); path.write_bytes(b'fixture, never run')
            with mock.patch.object(judge.sys, 'platform', 'win32'), mock.patch.dict(judge.os.environ, {'LOCALAPPDATA':name}), mock.patch.object(judge,'quiet',side_effect=[(0,'unrelated executable'),(0,'2.1.299 (Claude Code)')]) as probe, mock.patch.object(judge,'signed_in') as auth:
                self.assertEqual(judge.desktop_claude_cli(), str(good)); self.assertEqual(probe.call_count,2); auth.assert_not_called()

    def test_old_misreported_and_missing_cache_fall_back(self):
        with tempfile.TemporaryDirectory() as name:
            with mock.patch.object(judge.sys, 'platform', 'win32'), mock.patch.dict(judge.os.environ, {'LOCALAPPDATA':name}), mock.patch.object(judge,'quiet') as probe:
                self.assertIsNone(judge.desktop_claude_cli()); probe.assert_not_called()
            path = Path(name) / 'Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/claude-code/2.1.200/hash/claude.exe'
            path.parent.mkdir(parents=True); path.write_bytes(b'fixture')
            for response in ((1,'error'),(0,'2.1.299 (Claude Code)'),(0,'2.1.200 (Claude Code)')):
                with mock.patch.object(judge.sys,'platform','win32'), mock.patch.dict(judge.os.environ,{'LOCALAPPDATA':name}), mock.patch.object(judge,'quiet',return_value=response):
                    self.assertIsNone(judge.desktop_claude_cli())

    def test_non_windows_never_searches_store_or_probes(self):
        with mock.patch.object(judge.sys,'platform','linux'), mock.patch.object(judge,'quiet') as probe:
            self.assertIsNone(judge.desktop_claude_cli()); probe.assert_not_called()

if __name__ == '__main__': unittest.main()
