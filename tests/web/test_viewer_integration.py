"""Independent optional-viewer boundaries; synthetic fixtures, no native AI/browser.

Set LG_VIEWER_SOURCE_ROOT to the source checkout under review. The tests read it
only; every mutation is inside an isolated temporary fixture directory.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(os.environ.get("LG_VIEWER_SOURCE_ROOT", Path(__file__).resolve().parents[2])).resolve()
APP = ROOT / "web/prototypes/visual-viewer"


def load(name):
    spec = importlib.util.spec_from_file_location(name, APP / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_view = load("build_view")
hook = load("hook")
viewer = load("viewer")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def ref(source_id, quote="[합성 시험 자료] 원문"):
    return {"source_id": source_id, "model_id": "MODEL-TEST", "model_version": "v1",
            "document_version": "doc1", "data_version": "data1", "location": "section1",
            "quote": quote, "sha256": hashlib.sha256(quote.encode()).hexdigest(), "synthetic": True,
            "origin": {"representation": "excerpt", "source_url": "https://example.invalid/source"}}


def metadata(reference, kind):
    value = {k: reference[k] for k in ("source_id", "model_id", "model_version", "document_version", "data_version", "sha256")}
    return {**value, "kind": kind, "reference_fingerprint": hashlib.sha256(canonical(reference).encode()).hexdigest()}


def fixture(references, kinds):
    result = {"status": "completed", "evidence_refs": copy.deepcopy(references), "assumptions": ["[합성 시험 자료]"],
              "pains": [], "existing_features": [], "remaining_pains": [], "concepts": []}
    validation = {"contract_valid": True, "semantic_status": "unverified", "review": {"reported_reasoning_consistent": True}}
    candidate = {"result_key": "fixture", "result_version": 1, "result": copy.deepcopy(result),
                 "validation": validation, "source_metadata": [metadata(r, k) for r, k in zip(references, kinds)]}
    return {"session_id": "fixture-session", "requests": [], "turns": [{
        "state": {"turn_id": "fixture-turn", "status": "completed", "valid": True,
                  "latest_result": copy.deepcopy(result), "input": {"question": "[합성 시험 자료]", "model_scope": []}},
        "candidates": [candidate], "usage": [], "invocations": []}]}


class TypedSourceIntegrationTests(unittest.TestCase):
    def row(self, export):
        before = canonical(export)
        row = build_view.read_turns(export)[0]
        self.assertEqual(canonical(export), before, "Consumer mutated the original export object")
        return row

    def test_random_identity_kind_overrides_legacy_prefix_and_counts(self):
        references = [ref("DOC-random-review"), ref("REVIEW-random-fact"), ref("opaque-unclassified")]
        export = fixture(references, ["review", "product_fact", "review"])
        row = self.row(export)
        self.assertEqual([build_view.ev_type(r) for r in row["result"]["evidence_refs"]], ["후기", "제품 사실", "후기"])
        ctx = build_view.Ctx(export, Path("synthetic-export.json"), {})
        self.assertEqual(ctx.values["reviews"], 2)

    def test_explicit_unknown_does_not_turn_prefix_into_known_review(self):
        export = fixture([ref("REVIEW-legacy-with-unknown")], [None])
        row = self.row(export)
        self.assertEqual(build_view.ev_type(row["result"]["evidence_refs"][0]), "기타")
        self.assertEqual(build_view.Ctx(export, Path("synthetic-export.json"), {}).values["reviews"], 0)

    def test_legacy_unknown_without_metadata_stays_unknown(self):
        export = fixture([ref("opaque-legacy")], [None])
        export["turns"][0]["candidates"][0].pop("source_metadata")
        row = self.row(export)
        self.assertNotIn("kind", row["result"]["evidence_refs"][0])
        self.assertEqual(build_view.ev_type(row["result"]["evidence_refs"][0]), "원문 발췌")

    def test_changed_quote_or_identity_fingerprint_never_joins(self):
        for field in ("quote", "sha256", "data_version"):
            with self.subTest(field=field):
                export = fixture([ref("opaque-random")], ["review"])
                turn = export["turns"][0]
                for result in (turn["state"]["latest_result"], turn["candidates"][0]["result"]):
                    result["evidence_refs"][0][field] = "changed-after-metadata"
                row = self.row(export)
                self.assertIsNone(row["result"]["evidence_refs"][0]["kind"])
                self.assertEqual(build_view.ev_type(row["result"]["evidence_refs"][0]), "기타")

    def test_missing_malformed_or_unmatched_fingerprint_never_classifies_typed_source(self):
        for fingerprint in (None, "", "legacy", [], {}, "0"*64):
            with self.subTest(fingerprint=fingerprint):
                export = fixture([ref("REVIEW-legacy-prefix")], ["review"])
                item = export["turns"][0]["candidates"][0]["source_metadata"][0]
                if fingerprint is None:
                    item.pop("reference_fingerprint")
                else:
                    item["reference_fingerprint"] = fingerprint
                row = self.row(export)
                self.assertIsNone(row["result"]["evidence_refs"][0]["kind"])
                self.assertEqual(build_view.ev_type(row["result"]["evidence_refs"][0]), "기타")
                self.assertEqual(build_view.Ctx(export, Path("synthetic-export.json"), {}).values["reviews"], 0)

    def test_candidate_only_metadata_preserves_current_result_validation(self):
        export = fixture([ref("opaque-current")], ["review"])
        expected_validation = copy.deepcopy(export["turns"][0]["candidates"][0]["validation"])
        row = self.row(export)
        self.assertTrue(row["valid"])
        self.assertEqual(row["validation"], expected_validation)
        self.assertEqual(row["result"], row["candidates"][0]["result"])
        self.assertEqual(row["result"]["evidence_refs"][0]["kind"], "review")


@unittest.skipUnless(os.name == "nt", "Requires actual Windows directory junction semantics")
class WindowsJunctionIntegrationTests(unittest.TestCase):
    def test_named_harness_descendant_junction_is_rejected_before_any_access(self):
        with tempfile.TemporaryDirectory(prefix="lg-viewer-junction-") as temporary:
            base = Path(temporary).resolve()
            for relative in ("web", "runtime-data", ".codex", ".claude"):
                harness = base / ("harness-" + relative.strip("."))
                outside = base / ("outside-" + relative.strip("."))
                harness.mkdir()
                outside.mkdir()
                (harness / "AGENTS.md").write_text("[합성 시험 자료]", encoding="utf-8")
                (harness / "product-tools").mkdir()
                sentinel = outside / "sentinel.bin"
                sentinel.write_bytes(b"TEST_ONLY_OUTSIDE_SENTINEL")
                link = harness / relative
                self.assertTrue(link.parent.resolve().is_relative_to(base))
                self.assertTrue(outside.resolve().is_relative_to(base))
                made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                                      capture_output=True, timeout=10)
                self.assertEqual(made.returncode, 0, made.stderr.decode(errors="replace"))
                before = {p.relative_to(outside).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in outside.rglob("*") if p.is_file()}
                try:
                    for operation in (("install", "--codex"), ("status",), ("open", "--latest", "--no-browser"), ("uninstall", "--both")):
                        with self.subTest(path=relative, operation=operation):
                            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                                status = viewer.main([*operation, str(harness)])
                            self.assertEqual(status, 1)
                            after = {p.relative_to(outside).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in outside.rglob("*") if p.is_file()}
                            self.assertEqual(after, before, "Viewer accessed/wrote the outside junction destination")
                finally:
                    # Remove only this verified junction, never recurse through its destination.
                    self.assertEqual(link.resolve(), outside.resolve())
                    self.assertTrue(link.parent.resolve().is_relative_to(base))
                    os.rmdir(link)

    def make_installed_fixture(self, base):
        harness = base / "installed-harness"
        harness.mkdir()
        (harness / "AGENTS.md").write_text("[합성 시험 자료]", encoding="utf-8")
        (harness / "product-tools").mkdir()
        app = harness / "web/prototypes/visual-viewer"
        app.mkdir(parents=True)
        for name in viewer.APP_FILES:
            shutil.copyfile(APP / name, app / name)
        exports = harness / "runtime-data/exports"
        exports.mkdir(parents=True)
        value = fixture([ref("opaque-postinstall")], ["review"])
        (exports / "export-synthetic.json").write_text(canonical(value), encoding="utf-8")
        (harness / "runtime-data/visual-viewer").mkdir()
        viewer.write_launcher(harness)
        return harness

    @contextlib.contextmanager
    def redirect_owned_directory(self, base, harness, relative):
        """Move an owned fixture directory, then replace it with a real junction."""
        link = harness / relative
        outside = base / "outside-named-harness"
        # Both final absolute paths belong to this explicitly created fixture.
        self.assertTrue(link.resolve().is_relative_to(base))
        self.assertTrue(outside.resolve().is_relative_to(base))
        self.assertTrue(link.is_dir())
        self.assertFalse(link.is_symlink())
        link.rename(outside)
        (outside / "sentinel.bin").write_bytes(b"SYNTHETIC_OUTSIDE_SENTINEL")
        made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                              capture_output=True, timeout=10)
        self.assertEqual(made.returncode, 0, made.stderr.decode(errors="replace"))
        try:
            yield outside
        finally:
            self.assertEqual(link.resolve(), outside.resolve())
            self.assertTrue(link.parent.resolve().is_relative_to(base))
            os.rmdir(link)  # Only remove the verified junction, not its target.

    @staticmethod
    def tree_snapshot(directory):
        return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "directory"
                for p in directory.rglob("*")}

    def test_postinstall_hook_rejects_redirected_runtime_paths_nonblocking(self):
        for relative in ("runtime-data", "runtime-data/visual-viewer", "runtime-data/exports"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory(prefix="lg-hook-junction-") as temporary:
                base = Path(temporary).resolve()
                harness = self.make_installed_fixture(base)
                with self.redirect_owned_directory(base, harness, relative) as outside:
                    before = self.tree_snapshot(outside)
                    app = harness / "web/prototypes/visual-viewer"
                    hashes = [hashlib.sha256((app / name).read_bytes()).hexdigest() for name in ("build_view.py", "index.html")]
                    env = {**os.environ, "LGAX_VIEWER_NO_OPEN": "1", "PYTHONDONTWRITEBYTECODE": "1"}
                    run = subprocess.run([sys.executable, "-I", "-B", str(app / "hook.py"), "codex", *hashes],
                                         input=canonical({"session_id": "synthetic-only", "hook_event_name": "Stop", "cwd": str(harness)}),
                                         text=True, encoding="utf-8", capture_output=True, cwd=harness, env=env, timeout=15)
                    self.assertEqual(run.returncode, 0, "Rejected hook must not interrupt the business CLI")
                    self.assertEqual((run.stdout, run.stderr), ("", ""))
                    self.assertEqual(self.tree_snapshot(outside), before, "Postinstall hook wrote through a directory junction")
                    self.assertFalse((harness / "runtime-data/visual-viewer/view-data.js").exists())
                    self.assertFalse((harness / "runtime-data/visual-viewer/.hook-state.json").exists())

    def test_windows_launcher_guards_paths_before_mkdir_and_error_redirection(self):
        for relative in ("runtime-data", "runtime-data/visual-viewer", "runtime-data/exports"):
            with self.subTest(path=relative), tempfile.TemporaryDirectory(prefix="lg-launcher-junction-") as temporary:
                base = Path(temporary).resolve()
                harness = self.make_installed_fixture(base)
                fake_bin = base / "synthetic-bin"
                fake_bin.mkdir()
                # Prevent a real interpreter lookup/download/model invocation;
                # an unguarded launcher still exposes its pre-Python log write.
                (fake_bin / "uv.cmd").write_text("@echo off\r\nexit /b 1\r\n", encoding="ascii")
                with self.redirect_owned_directory(base, harness, relative) as outside:
                    before = self.tree_snapshot(outside)
                    app = harness / "web/prototypes/visual-viewer"
                    hashes = [hashlib.sha256((app / name).read_bytes()).hexdigest() for name in ("hook.py", "build_view.py", "index.html")]
                    hashes.append(viewer.launcher_digest())
                    env = {**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ.get("PATH", ""), "LGAX_VIEWER_NO_OPEN": "1"}
                    run = subprocess.run(["cmd.exe", "/d", "/c", str(harness / ".codex/visual-viewer-hook.cmd"), "codex", *hashes],
                                         capture_output=True, cwd=harness, env=env, timeout=15)
                    self.assertEqual(run.returncode, 0)
                    self.assertEqual((run.stdout, run.stderr), (b"", b""))
                    self.assertEqual(self.tree_snapshot(outside), before, "Launcher wrote startup directories/logs before checking a junction")
                    self.assertFalse((harness / "runtime-data/visual-viewer/hook-start-error.log").exists())

    def test_postinstall_output_leaf_reparse_links_are_rejected_silently(self):
        for leaf in (".hook-state.json", ".hook.lock", "hook-error.log", "hook-start-error.log", "view-data.js", "index.html"):
            with self.subTest(leaf=leaf), tempfile.TemporaryDirectory(prefix="lg-output-leaf-") as temporary:
                base = Path(temporary).resolve()
                harness = self.make_installed_fixture(base)
                outside = base / "outside-sentinel.json"
                outside.write_bytes(b'{"synthetic_outside": true}')
                link = harness / "runtime-data/visual-viewer" / leaf
                directory_link = False
                outside_directory = base / "outside-leaf-directory"
                try:
                    os.symlink(outside, link)
                except OSError:
                    # No privilege/global setting changes: a junction exercises
                    # the same Windows reparse rejection at this output leaf.
                    outside_directory.mkdir()
                    (outside_directory / "sentinel.bin").write_bytes(b"SYNTHETIC_OUTSIDE_LEAF")
                    made = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside_directory)],
                                          capture_output=True, timeout=10)
                    self.assertEqual(made.returncode, 0, made.stderr.decode(errors="replace"))
                    directory_link = True
                before = hashlib.sha256(outside.read_bytes()).hexdigest()
                before_directory = self.tree_snapshot(outside_directory) if directory_link else None
                app = harness / "web/prototypes/visual-viewer"
                hashes = [hashlib.sha256((app / name).read_bytes()).hexdigest() for name in ("build_view.py", "index.html")]
                env = {**os.environ, "LGAX_VIEWER_NO_OPEN": "1", "PYTHONDONTWRITEBYTECODE": "1"}
                run = subprocess.run([sys.executable, "-I", "-B", str(app / "hook.py"), "codex", *hashes],
                                     input=canonical({"session_id": "synthetic-only", "hook_event_name": "Stop", "cwd": str(harness)}),
                                     text=True, encoding="utf-8", capture_output=True, cwd=harness, env=env, timeout=15)
                self.assertEqual(run.returncode, 0)
                self.assertEqual((run.stdout, run.stderr), ("", ""))
                self.assertEqual(hashlib.sha256(outside.read_bytes()).hexdigest(), before)
                if directory_link:
                    self.assertEqual(self.tree_snapshot(outside_directory), before_directory)
                self.assertFalse((harness / "runtime-data/visual-viewer/.hook-last-export").exists())
                self.assertEqual(link.resolve(), outside_directory.resolve() if directory_link else outside.resolve())
                if directory_link:
                    os.rmdir(link)  # Verified test-owned directory link only.
                else:
                    self.assertTrue(link.is_symlink())
                    link.unlink()  # Nonrecursive removal of the file link.


if __name__ == "__main__":
    unittest.main()
