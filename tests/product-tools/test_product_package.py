"""Source ZIP excludes unlisted local notes and preserves existing outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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
                self.assertFalse(manifest["frontends"]["included"])
                self.assertFalse(any('/app/src/' in name for name in output.namelist()))
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


class FrontendSourcePackageTests(unittest.TestCase):
    def source(self, base):
        source = base / 'source'
        native_eval.freeze(ROOT, source)
        names = ['adapters/' + name for name in package.ADAPTER_FILES] + ['docs/contracts/portable-product.md']
        frontend_files, _ = package.frontend_sources(ROOT)
        for name in [*names, *frontend_files]:
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        return source, frontend_files

    def test_opt_in_contains_all_locked_build_inputs_but_no_unlisted_data(self):
        with tempfile.TemporaryDirectory(prefix='lg-frontends-source-') as tmp:
            base = Path(tmp)
            source, expected = self.source(base)
            app = 'web/prototypes/control-room/factory-dashboard'
            unwanted = ('src/.env', 'src/auth.json', 'src/private-notes.md', 'src/fixtures/reviews.json',
                        'src/nested/node_modules/private.js', 'src/nested/runtime-data/run.js',
                        'node_modules/private.js', 'dist/private.js', 'dist-office/private.js',
                        'backend/private.py', 'tests/private.test.mjs', 'public/media/private.mp4',
                        'public/characters/unapproved.png', 'private-notes.md')
            for relative in unwanted:
                path = source / app / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('TEST_ONLY_PRIVATE_SENTINEL', encoding='utf-8')
            archive = base / 'source.zip'
            result = package.build('codex', base / 'prepared', archive, root=source, include_frontends=True)
            self.assertTrue(result['include_frontends'])
            with zipfile.ZipFile(archive) as output:
                names = set(output.namelist())
                manifest = json.loads(output.read('submission-source-manifest.json'))
                frontends = manifest['frontends']
                self.assertTrue(frontends['included'])
                self.assertEqual(3, len(frontends['apps']))
                self.assertEqual(len(expected), sum(app['source_files'] for app in frontends['apps']))
                self.assertIn('Node/npm', frontends['scope'])
                for name, raw in expected.items():
                    self.assertEqual(raw, output.read(name), name)
                for relative in unwanted:
                    self.assertNotIn(app + '/' + relative, names)
                self.assertFalse(any(b'TEST_ONLY_PRIVATE_SENTINEL' in output.read(name) for name in names))
                for entry in manifest['files']:
                    self.assertEqual(entry['sha256'], hashlib.sha256(output.read(entry['path'])).hexdigest())
                for app in frontends['apps']:
                    self.assertIn(app['path'] + '/package-lock.json', names)
                    self.assertIn(app['path'] + '/index.html', names)
                    self.assertIn(app['output'], names)
                self.assertIn('web/prototypes/visual-viewer/app/scripts/planner-report.mjs', names)
                self.assertIn('web/prototypes/visual-viewer/app/vendor/jinha-report/SOURCE.md', names)
                self.assertIn('web/prototypes/control-room/factory-dashboard/shared/skill-operations.json', names)

    def test_extracted_source_cli_repackages_frontends_for_both_runtime_profiles(self):
        with tempfile.TemporaryDirectory(prefix='lg-frontends-roundtrip-') as tmp:
            base = Path(tmp)
            source, expected = self.source(base)
            original = base / 'original.zip'
            package.build('codex', base / 'prepared', original, root=source, include_frontends=True)
            extracted = base / 'extracted'
            with zipfile.ZipFile(original) as archive:
                archive.extractall(extracted)
                original_manifest = json.loads(archive.read('submission-source-manifest.json'))
            for engine in ('codex', 'claude'):
                with self.subTest(engine=engine):
                    rebuilt = base / (engine + '.zip')
                    done = subprocess.run([sys.executable, str(extracted / 'adapters/common/package.py'),
                        '--engine', engine, '--target', str(base / (engine + '-installed')),
                        '--archive', str(rebuilt), '--include-frontends'], cwd=base,
                        capture_output=True, text=True, encoding='utf-8', timeout=90)
                    self.assertEqual(0, done.returncode, done.stdout + done.stderr)
                    self.assertTrue(json.loads(done.stdout)['include_frontends'])
                    with zipfile.ZipFile(rebuilt) as archive:
                        manifest = json.loads(archive.read('submission-source-manifest.json'))
                        self.assertEqual(original_manifest['frontends'], manifest['frontends'])
                        for name, raw in expected.items():
                            self.assertEqual(raw, archive.read(name), name)

    def test_missing_lock_or_required_static_asset_fails_before_installing(self):
        with tempfile.TemporaryDirectory(prefix='lg-frontends-missing-') as tmp:
            base = Path(tmp)
            source, _ = self.source(base)
            names = ('web/prototypes/visual-viewer/app/package-lock.json',
                     'web/prototypes/visual-viewer/app/src/main.tsx',
                     'web/prototypes/visual-viewer/app/vendor/jinha-report/report-app.js',
                     'web/prototypes/control-room/factory-dashboard/public/characters/researcher-seated-v1.png')
            for i, name in enumerate(names):
                with self.subTest(name=name):
                    path = source / name
                    raw = path.read_bytes()
                    path.unlink()
                    target, archive = base / ('prepared-' + str(i)), base / (str(i) + '.zip')
                    with self.assertRaises(FileNotFoundError):
                        package.build('codex', target, archive, root=source, include_frontends=True)
                    self.assertFalse(target.exists())
                    self.assertFalse(archive.exists())
                    path.write_bytes(raw)

    def test_linked_source_file_and_directory_are_rejected_before_read(self):
        with tempfile.TemporaryDirectory(prefix='lg-frontends-linked-') as tmp:
            base = Path(tmp)
            source, _ = self.source(base)
            app = source / 'web/prototypes/visual-viewer/app/src'
            file = app / 'linked.ts'
            file.write_text('TEST_ONLY_LINKED_SENTINEL', encoding='utf-8')
            with mock.patch.object(Path, 'is_symlink', lambda path: path == file):
                with self.assertRaisesRegex(ValueError, 'Linked frontend source'):
                    package.frontend_sources(source)
            directory = app / 'linked-directory'
            directory.mkdir()
            with mock.patch.object(Path, 'is_junction', lambda path: path == directory):
                with self.assertRaisesRegex(ValueError, 'Linked frontend source directory'):
                    package.frontend_sources(source)


if __name__=="__main__":
    unittest.main()
