"""Preserve Windows native raw evidence while comparing frozen prompt text."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals/runner'))
import regression_audit
import family_audit


class RecordedPromptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lg-prompt-audit-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'prompt.txt'
        self.prompt = '냉장고 불편을 찾아줘.\nBEGIN_REQUEST\n원문 질문\nEND_REQUEST'
        self.job = {'prompt': self.prompt,
                    'prompt_sha256': hashlib.sha256(self.prompt.encode()).hexdigest()}

    def check_both(self, expected):
        for auditor in (regression_audit, family_audit):
            with self.subTest(auditor=auditor.__name__):
                self.assertIs(auditor.prompt_text_matches(self.path, self.job), expected)

    def test_lf_and_observed_windows_crlf_match_without_rewriting_raw(self):
        for separator in ('\n', '\r\n'):
            original = self.prompt.replace('\n', separator).encode()
            self.path.write_bytes(original)
            self.check_both(True)
            self.assertEqual(self.path.read_bytes(), original)

    def test_changed_question_never_normalizes_to_frozen_input(self):
        self.path.write_bytes(self.prompt.replace('냉장고', '전자레인지').replace('\n', '\r\n').encode())
        self.check_both(False)

    def test_bare_carriage_return_and_bom_are_not_accepted(self):
        for raw in (self.prompt.replace('\n', '\r').encode(), b'\xef\xbb\xbf' + self.prompt.encode()):
            self.path.write_bytes(raw)
            self.check_both(False)

    def test_matching_text_with_changed_frozen_digest_is_rejected(self):
        self.path.write_bytes(self.prompt.encode())
        self.job['prompt_sha256'] = '0' * 64
        self.check_both(False)

    def test_recorded_json_lf_crlf_preserves_original_bytes(self):
        value = {'id': 'probe', 'question': self.prompt, 'accepted': True}
        expected = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
        for separator in ('\n', '\r\n'):
            original = expected.replace('\n', separator).encode()
            self.path.write_bytes(original)
            for auditor in (regression_audit, family_audit):
                self.assertTrue(auditor.recorded_json_matches(self.path, value))
            self.assertEqual(self.path.read_bytes(), original)

    def test_recorded_json_value_change_and_boolean_integer_substitution_fail(self):
        expected = {'id': 'probe', 'accepted': True}
        for value in ({'id': 'changed', 'accepted': True}, {'id': 'probe', 'accepted': 1}):
            self.path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())
            for auditor in (regression_audit, family_audit):
                self.assertFalse(auditor.recorded_json_matches(self.path, expected))

    def test_recorded_json_bare_cr_and_bom_fail(self):
        value = {'id': 'probe'}
        expected = json.dumps(value, indent=2) + '\n'
        for original in (expected.replace('\n', '\r').encode(), b'\xef\xbb\xbf' + expected.encode()):
            self.path.write_bytes(original)
            for auditor in (regression_audit, family_audit):
                self.assertFalse(auditor.recorded_json_matches(self.path, value))


if __name__ == '__main__':
    unittest.main()
