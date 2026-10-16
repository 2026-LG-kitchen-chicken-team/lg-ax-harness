"""Actual instruction bytes and installed wrappers, with no native/model calls."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product-tools"))
from product_tools.contracts import MAX_BYTES, ToolError, canonical
from product_tools.instructions import InstructionLoader, PATHS, SKILLS


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lg-instruction-")
        self.root = Path(self.temp.name)
        for key, relative in PATHS.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((key + " 실제 지침\npython skills/example/scripts/run.py\n").encode("utf-8"))
        self.seal()
        self.loader = InstructionLoader(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def seal(self, suffix=""):
        entry = lambda path: {"path": path, "sha256": digest((self.root / path).read_bytes())}
        value = {"version": "product-skills-v1", "agent": PATHS["main"], "note": suffix,
                 "shared_files": [entry(PATHS["main"])],
                 "skills": [{"name": name, "path": PATHS[name], "files": [entry(PATHS[name])] +
                             ([entry(PATHS["payload"])] if name == "review-and-revise" else [])} for name in SKILLS]}
        (self.root / "skills/manifest.json").write_text(canonical(value), encoding="utf-8")

    def request(self, ids=None, **kwargs):
        return self.loader.get_work_instructions({"context_key": "actual-request-1", "instruction_ids": ids or ["needs-structuring"], **kwargs})

    def report(self, response):
        item = response["instructions"][0]
        return {"instruction_id": item["instruction_id"], "context_key": response["context_key"],
                "manifest_sha256": response["manifest_sha256"], "source_sha256": item["source_sha256"],
                "returned_body_sha256": item["returned_body_sha256"]}

    def test_selected_actual_bytes_and_receipt_never_claim_application(self):
        value = self.request()
        self.assertEqual(len(value["instructions"]), 1)
        item = value["instructions"][0]
        raw = (self.root / PATHS["needs-structuring"]).read_bytes()
        self.assertEqual(item["body"].encode("utf-8"), raw)
        self.assertEqual(item["source_sha256"], digest(raw))
        self.assertEqual(item["returned_body_sha256"], digest(raw))
        self.assertEqual(item["canonical_path"], PATHS["needs-structuring"])
        self.assertIsNone(item["native_path"])
        self.assertEqual(value["receipt"]["body_instruction_ids"], ["needs-structuring"])
        self.assertIn("not certified", value["receipt"]["scope"])
        self.assertNotIn("applied", item)
        self.assertLessEqual(len(canonical({"ok": True, "result": value}).encode()), MAX_BYTES)

    def test_same_context_report_skips_body_but_is_not_delivery(self):
        first = self.request()
        again = self.request(known_context=[self.report(first)])
        self.assertNotIn("body", again["instructions"][0])
        self.assertEqual(again["instructions"][0]["status"], "already_in_context_reported")
        self.assertEqual(again["receipt"]["body_instruction_ids"], [])

    def test_changed_context_returns_body_again(self):
        known = self.report(self.request())
        value = self.loader.get_work_instructions({"context_key": "new-request", "instruction_ids": ["needs-structuring"], "known_context": [known]})
        self.assertIn("body", value["instructions"][0])

    def test_manifest_change_even_with_same_body_requires_redelivery(self):
        known = self.report(self.request())
        self.seal("next version")
        self.assertIn("body", self.request(known_context=[known])["instructions"][0])
        with self.assertRaises(ToolError) as error:
            self.request(expected_manifest_sha256=known["manifest_sha256"])
        self.assertEqual(error.exception.code, "instruction_version")

    def test_changed_instruction_new_manifest_returns_new_bytes(self):
        known = self.report(self.request())
        (self.root / PATHS["needs-structuring"]).write_text("new original 지침", encoding="utf-8")
        self.seal()
        result = self.request(known_context=[known])["instructions"][0]
        self.assertEqual(result["body"], "new original 지침")
        self.assertNotEqual(result["source_sha256"], known["source_sha256"])

    def test_tampered_selected_file_is_rejected_even_with_context_report(self):
        known = self.report(self.request())
        (self.root / PATHS["needs-structuring"]).write_text("tampered", encoding="utf-8")
        with self.assertRaises(ToolError) as error:
            self.request(known_context=[known])
        self.assertEqual(error.exception.code, "instruction_integrity")

    def test_id_allowlist_rejects_paths_roles_duplicates_and_empty(self):
        for ids in (["../secret"], ["/absolute"], ["product_evidence_reviewer"], ["main", "main"], []):
            with self.subTest(ids=ids), self.assertRaises(ToolError):
                self.loader.get_work_instructions({"context_key": "context", "instruction_ids": ids})

    def test_manifest_path_escape_and_wrong_identity_rejected(self):
        file = self.root / "skills/manifest.json"
        value = json.loads(file.read_text(encoding="utf-8"))
        value["shared_files"].append({"path": "../secret", "sha256": "0" * 64})
        file.write_text(canonical(value), encoding="utf-8")
        with self.assertRaises(ToolError) as error:
            self.request()
        self.assertEqual(error.exception.code, "instruction_path")
        self.seal()
        value = json.loads(file.read_text(encoding="utf-8")); value["version"] = "unknown"
        file.write_text(canonical(value), encoding="utf-8")
        with self.assertRaises(ToolError) as error:
            self.request()
        self.assertEqual(error.exception.code, "instruction_identity")

    def test_reparse_file_is_rejected_before_read(self):
        original = Path.lstat
        target = self.root / PATHS["needs-structuring"]
        def lstat(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path == target:
                return type("Reparse", (), {"st_mode": value.st_mode, "st_file_attributes": 0x400})()
            return value
        with mock.patch.object(Path, "lstat", lstat), self.assertRaises(ToolError) as error:
            self.request()
        self.assertEqual(error.exception.code, "instruction_path")

    def test_output_limit_does_not_return_truncated_instruction(self):
        for key in ("needs-structuring", "review-and-revise"):
            (self.root / PATHS[key]).write_bytes(b"x" * 40000)
        self.seal()
        with self.assertRaises(ToolError) as error:
            self.request(["needs-structuring", "review-and-revise"])
        self.assertEqual(error.exception.code, "output_limit")

    def test_install_manifest_identity_mismatch_is_rejected(self):
        (self.root / "product-install.json").write_text(canonical({"source_manifest_sha256": "0" * 64}), encoding="utf-8")
        with self.assertRaises(ToolError) as error:
            self.request()
        self.assertEqual(error.exception.code, "instruction_identity")


class InstalledInstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="lg-instruction-install-")
        cls.base = Path(cls.temp.name)
        source = cls.base / "source"
        source.mkdir()
        old = json.loads((ROOT / "skills/manifest.json").read_text(encoding="utf-8"))
        names = {x["path"] for x in old["shared_files"]} | {x["path"] for s in old["skills"] for x in s["files"]}
        names.add("skills/review-and-revise/references/meaning-preservation.md")
        names.update(("product-tools/product_tools/instructions.py", "docs/contracts/instruction-loading.md", "THIRD_PARTY_NOTICES.md", "vendor/codex-harness/LICENSE", "vendor/codex-harness/NOTICE"))
        for relative in names:
            target = source / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        shutil.copytree(ROOT / "adapters", source / "adapters")
        shutil.copytree(ROOT / "data/business/empty", source / "data/business/empty")
        builder = load("instruction_test_manifest_builder", ROOT / "scripts/build-product-manifest.py")
        builder.ROOT = source
        manifest = builder.build()
        # Root owns the real generator/manifest; only this temporary fixture gets pending registration.
        for skill in manifest["skills"]:
            if "get_work_instructions" not in skill["operations"]:
                skill["operations"].insert(0, "get_work_instructions")
        if not any(x["path"] == "docs/contracts/instruction-loading.md" for x in manifest["shared_files"]):
            manifest["shared_files"].append({"path": "docs/contracts/instruction-loading.md", "sha256": digest((source / "docs/contracts/instruction-loading.md").read_bytes())})
        (source / "skills/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        cls.codex = cls.base / "codex"
        cls.claude = cls.base / "claude"
        load("instruction_codex_installer", source / "adapters/codex/install.py").install(cls.codex, source)
        load("instruction_claude_installer", source / "adapters/common/install.py").install(cls.claude, "claude", source)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_both_native_transformations_have_actual_body_and_dual_hash(self):
        for target, prefix in ((self.codex, ".agents/"), (self.claude, ".claude/")):
            with self.subTest(prefix=prefix):
                response = InstructionLoader(target).get_work_instructions({"context_key": "current", "instruction_ids": ["needs-structuring", "payload", "main"]})
                item = response["instructions"][0]
                self.assertEqual(item["native_path"], prefix + PATHS["needs-structuring"])
                self.assertEqual(item["body"].encode(), (target / item["returned_path"]).read_bytes())
                self.assertNotEqual(item["source_sha256"], item["returned_body_sha256"])
                self.assertIn("python " + prefix + "skills/", item["body"])

    def test_meaning_guards_arrive_in_selected_main_stage_and_payload_bodies(self):
        # These are delivery/contract checks, not a semantic model evaluation.
        expected = {
            "main": ("의미 보존:", "사건 순서·부정 범위", "existing_features", "최종 답변"),
            "needs-structuring": ("사건 순서·부정 범위", "이전의 미수행", "전문가 발언"),
            "feature-comparison": ("조건 축약 점검:", "existing_features의 text 자체", "분기"),
            "concept-writing": ("제안의 text에도 핵심 적용 조건", "사건 순서·부정 범위"),
            "review-and-revise": ("의미 보존 점검", "사건 순서·부정 범위", "최종 문장만 바꿔"),
            "payload": ("각 claim.text와 decision_notes 자체", "사건 순서·부정 범위"),
        }
        for target in (self.codex, self.claude):
            loader = InstructionLoader(target)
            for instruction_id, guards in expected.items():
                with self.subTest(engine=target.name, instruction=instruction_id):
                    response = loader.get_work_instructions({"context_key": "meaning-current",
                                                           "instruction_ids": [instruction_id]})
                    self.assertEqual(response["receipt"]["body_instruction_ids"], [instruction_id])
                    body = response["instructions"][0]["body"]
                    for guard in guards:
                        self.assertIn(guard, body)
                    self.assertLessEqual(len(canonical({"ok": True, "result": response}).encode()), MAX_BYTES)

    def test_optional_meaning_reference_is_installed_without_eager_loading(self):
        relative = "skills/review-and-revise/references/meaning-preservation.md"
        original = (ROOT / relative).read_bytes()
        for target, prefix in ((self.codex, ".agents/"), (self.claude, ".claude/")):
            with self.subTest(engine=target.name):
                record = json.loads((target / "product-install.json").read_text(encoding="utf-8"))
                entry = next(x for x in record["files"] if x["path"] == prefix + relative)
                self.assertEqual(entry["sha256"], digest(original))
                self.assertEqual((target / entry["path"]).read_bytes(), original)
                response = InstructionLoader(target).get_work_instructions({
                    "context_key": "meaning-current", "instruction_ids": ["main"]})
                body = response["instructions"][0]["body"]
                self.assertIn("meaning-preservation.md", body)
                self.assertNotIn("## 일반 반례", body)
                self.assertEqual(response["receipt"]["body_instruction_ids"], ["main"])

    def test_scope_choice_guards_are_delivered_without_question_keyword_routing(self):
        for target in (self.codex, self.claude):
            for instruction_id in ("main", "evidence-retrieval"):
                with self.subTest(engine=target.name, instruction=instruction_id):
                    response = InstructionLoader(target).get_work_instructions({
                        "context_key": "new-business", "instruction_ids": [instruction_id]})
                    body = response["instructions"][0]["body"]
                    for token in ('prior_scope:"reference_only"', 'prior_scope:"inherit"', "목표·제약"):
                        self.assertIn(token, body)
                    self.assertIn("복구", body)

    def test_mutated_native_body_even_with_changed_install_hash_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="lg-instruction-tamper-") as temporary:
            target = Path(temporary) / "product"
            shutil.copytree(self.claude, target)
            relative = ".claude/" + PATHS["needs-structuring"]
            (target / relative).write_text("changed native instruction", encoding="utf-8")
            record = json.loads((target / "product-install.json").read_text(encoding="utf-8"))
            next(x for x in record["files"] if x["path"] == relative)["sha256"] = digest((target / relative).read_bytes())
            (target / "product-install.json").write_text(canonical(record), encoding="utf-8")
            with self.assertRaises(ToolError) as error:
                InstructionLoader(target).get_work_instructions({"context_key": "current", "instruction_ids": ["needs-structuring"]})
            self.assertEqual(error.exception.code, "instruction_integrity")

    def test_standalone_review_loads_main_then_complete_review_and_payload(self):
        for target in (self.codex, self.claude):
            with self.subTest(engine=target.name):
                loader = InstructionLoader(target)
                first = loader.get_work_instructions({"context_key": "review-request",
                                                      "instruction_ids": ["main"]})
                item = first["instructions"][0]
                known = {"instruction_id": "main", "context_key": first["context_key"],
                         "manifest_sha256": first["manifest_sha256"],
                         "source_sha256": item["source_sha256"],
                         "returned_body_sha256": item["returned_body_sha256"]}
                second = loader.get_work_instructions({"context_key": "review-request",
                                                       "instruction_ids": ["main", "review-and-revise", "payload"],
                                                       "known_context": [known]})
                self.assertEqual(second["receipt"]["body_instruction_ids"], ["review-and-revise", "payload"])
                self.assertEqual(second["receipt"]["already_in_context_reported_ids"], ["main"])
                self.assertNotIn("body", second["instructions"][0])
                for response in (first, second):
                    self.assertLessEqual(len(canonical({"ok": True, "result": response}).encode("utf-8")), MAX_BYTES)
                    for instruction in response["instructions"]:
                        if "body" in instruction:
                            self.assertEqual(instruction["body"].encode("utf-8"),
                                             (target / instruction["returned_path"]).read_bytes())
                self.assertFalse((target / "runtime-data/product.sqlite").exists())

    def test_six_wrappers_return_only_selected_body_without_catalog_or_DB(self):
        for name in SKILLS:
            with self.subTest(skill=name):
                payload = canonical({"context_key": "current", "instruction_ids": [name]})
                cp = subprocess.run([sys.executable, "-B", str(self.codex / ".agents/skills" / name / "scripts/run.py"),
                                     "--data", str(self.base / "missing-catalog"), "get_work_instructions"],
                                    cwd=self.codex, input=payload, capture_output=True, text=True, encoding="utf-8",
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=15)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                value = json.loads(cp.stdout)["result"]
                self.assertEqual([x["instruction_id"] for x in value["instructions"]], [name])
                self.assertIn("body", value["instructions"][0])
        self.assertFalse((self.codex / "runtime-data/product.sqlite").exists())

    def test_natural_and_explicit_use_same_six_discoverable_skills(self):
        for target, prefix in ((self.codex, ".agents"), (self.claude, ".claude")):
            skills = sorted((target / prefix / "skills").glob("*/SKILL.md"))
            self.assertEqual(len(skills), 6)
            for file in skills:
                body = file.read_text(encoding="utf-8")
                self.assertIn("user-invocable: true", body)
                self.assertNotIn("disable-model-invocation: true", body)
                self.assertIn("get_work_instructions", body)
                self.assertIn("$" + file.parent.name, body)
                self.assertIn("/" + file.parent.name, body)
        self.assertIn("/skills", (self.codex / "README.md").read_text(encoding="utf-8"))
        self.assertIn("@ subagent", (self.claude / "README.md").read_text(encoding="utf-8"))
        self.assertFalse((self.claude / ".claude/commands").exists())
        self.assertEqual(len(list((self.claude / ".claude/agents").glob("*.md"))), 3)
        self.assertEqual(len(list((self.codex / ".codex/agents").glob("*.toml"))), 3)


if __name__ == "__main__":
    unittest.main()
