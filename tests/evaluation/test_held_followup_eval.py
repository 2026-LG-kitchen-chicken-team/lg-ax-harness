"""Real-source rebinding and acceptance boundaries; no native/model calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evals/runner'))
import held_followup_eval as probe


class HeldFollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.original = ROOT / 'data/business/lg-research-v3'
        self.hashes = {n: probe.ev.sha(self.original / n) for n in ('manifest.json', 'models.json', 'sources.jsonl')}

    def tearDown(self):
        self.assertEqual(self.hashes, {n: probe.ev.sha(self.original / n) for n in self.hashes})
        self.temp.cleanup()

    def clone(self):
        return probe.clone_version(self.original, self.base / 'catalog', 'diagnostic-version-1')

    def test_rebinding_preserves_every_origin_content_and_model_field(self):
        copied, old = self.clone(), probe.ev.Dataset(self.original)
        self.assertEqual(copied.models, old.models)
        self.assertNotEqual(copied.fingerprint, old.fingerprint)
        self.assertEqual(copied.sources.keys(), old.sources.keys())
        for sid in old.sources:
            self.assertEqual(copied.sources[sid], {**old.sources[sid], 'data_version': copied.version})
        self.assertIn('no_new_web_evidence', copied.manifest['provenance'])
        self.assertFalse(copied.synthetic)

    def test_synthetic_same_version_existing_or_invalid_targets_never_overwrite(self):
        for source, version in ((ROOT / 'data/synthetic/kitchen-v1', 'new-version'),
                                (self.original, probe.ev.Dataset(self.original).version), (self.original, '../invalid')):
            target = self.base / 'forbidden'
            with self.assertRaises(ValueError):
                probe.clone_version(source, target, version)
            self.assertFalse(target.exists())
        copied = self.clone()
        before = {p.name: probe.ev.sha(p) for p in copied.root.iterdir()}
        with self.assertRaises(ValueError):
            probe.clone_version(self.original, copied.root, 'another-version')
        self.assertEqual(before, {p.name: probe.ev.sha(p) for p in copied.root.iterdir()})

    def test_rebinding_stales_old_turn_without_opening_one_then_preserves_history(self):
        workspace = self.base / 'workspace'
        for name in ('skills/manifest.json', 'agents/product-planning.md'):
            p = workspace / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((ROOT / name).read_bytes())
        db = workspace / 'runtime-data/product.sqlite'
        store = probe.StateStore(db, probe.ev.Dataset(self.original))
        convo = probe.Conversation(store, workspace)
        first = convo.open_request({'model_id': 'T876MQQ012', 'question': 'first', 'user_submitted': True,
            'constraints': {'hardware_allowed': False, 'exclude_pains': [], 'max_concepts': 1}})['turn']
        held = {'status': 'held', 'pains': [], 'existing_features': [], 'remaining_pains': [], 'concepts': [],
            'assumptions': [], 'evidence_refs': [], 'validation_findings': ['missing dimensions'], 'revisions': 0,
            'usage_summary': {'status': 'unknown'}}
        saved = store.save_result(first['session_id'], first['turn_id'], 'candidate-1', held, 0)
        self.assertTrue(saved['accepted'])
        exported = convo.export_session({'session_id': first['session_id']})
        export_hash = probe.ev.sha(workspace / exported['path'])
        candidates = probe.ev.stored_candidates(workspace)
        store.close()
        copied = self.clone()
        store = probe.StateStore(db, copied)
        try:
            convo = probe.Conversation(store, workspace)
            stale = convo.current_request({k: first[k] for k in ('session_id', 'request_key')})['turn']
            self.assertFalse(stale['valid'])
            self.assertIsNone(stale['latest_result'])
            self.assertEqual(store.db.execute('SELECT count(*) FROM turns').fetchone()[0], 1)
            follow = convo.open_request({'question': 'second', 'session_id': first['session_id'],
                'prior_turn_id': first['turn_id'], 'user_submitted': True})['turn']
            self.assertEqual(follow['input']['data_version'], copied.version)
            self.assertNotEqual(follow['turn_id'], first['turn_id'])
            self.assertNotEqual(follow['request_key'], first['request_key'])
            self.assertEqual(follow['input']['constraints'], first['input']['constraints'])
            self.assertEqual(convo.historical(first['session_id'], first['turn_id'])['result'], held)
            self.assertEqual(probe.ev.stored_candidates(workspace), candidates)
            self.assertEqual(probe.ev.sha(workspace / exported['path']), export_hash)
        finally:
            store.close()

    def accepted(self):
        return {'execution': {'status': 'succeeded', 'turn_completed': True, 'native_id': 'actual-id'},
            'saved_match': True, 'saved_accepted': True, 'structural_valid': True, 'result_status': 'held',
            'original_handle_preserved': True, 'export_matches': True, 'installed_integrity': True,
            'state': {'valid': True}, 'native_final_matches': True, 'trace_integrity': True}

    def test_timeout_partial_rejected_stale_or_mismatching_export_skip_followup(self):
        row = self.accepted()
        self.assertIs(probe.can_continue(row), True)
        for field in ('saved_match', 'saved_accepted', 'structural_valid', 'original_handle_preserved',
                      'export_matches', 'installed_integrity', 'native_final_matches', 'trace_integrity'):
            bad = copy.deepcopy(row); bad[field] = False
            self.assertIs(probe.can_continue(bad), False, field)
        for field, value in (('status', 'timeout'), ('turn_completed', False), ('native_id', None)):
            bad = copy.deepcopy(row); bad['execution'][field] = value
            self.assertFalse(probe.can_continue(bad))
        bad = copy.deepcopy(row); bad['state']['valid'] = False
        self.assertFalse(probe.can_continue(bad))

    def test_export_requires_same_question_handle_state_and_final_candidate(self):
        state = {'session_id': 'session', 'turn_id': 'turn', 'request_key': 'key', 'input': {'question': 'question'}}
        answer = {'result': {'status': 'held'}, 'assessment': {'claim_checks': []}}
        export = {'session_id': 'session', 'turns': [{'state': state, 'candidates': [
            {'result': answer['result'], 'validation': {'assessment': answer['assessment']}}]}],
            'requests': [{'turn_id': 'turn', 'input': {'request_key': 'key', 'question': 'question'}}]}
        self.assertTrue(probe.export_matches(export, state, answer))
        for mode in ('question', 'key', 'candidate', 'state', 'empty'):
            bad = copy.deepcopy(export)
            if mode == 'question': bad['requests'][0]['input']['question'] = 'different'
            elif mode == 'key': bad['requests'][0]['input']['request_key'] = 'different'
            elif mode == 'candidate': bad['turns'][0]['candidates'][0]['result'] = {'status': 'completed'}
            elif mode == 'state': bad['turns'][0]['state']['input']['question'] = 'different'
            else: bad['turns'] = []
            self.assertFalse(probe.export_matches(bad, state, answer), mode)

    def test_actual_bundle_scope_and_every_cli_data_flag_are_required(self):
        data = self.clone()
        model = next(m for m in data.models if m['model_id'] == 'T876MQQ012')
        bundle = {'scope': {k: model[k] for k in ('model_id', 'model_version', 'document_version')},
            'data_version': data.version, 'dataset_fingerprint': data.fingerprint}
        command = 'uv run python skills/evidence-retrieval/scripts/run.py open_request_bundle --data runtime-data/catalog'
        item = {'command': command, 'exit_code': 0, 'aggregated_output': json.dumps({'ok': True, 'result': {'bundle': bundle}})}
        good = probe.data_commands([item], 'runtime-data/catalog', data)
        self.assertTrue(good['all_explicit_data_paths']); self.assertTrue(good['exact_bundle_scope_observed'])
        missing = {**item, 'command': command + '; uv run python product-tools/cli.py current_request --input input.json'}
        self.assertFalse(probe.data_commands([missing], 'runtime-data/catalog', data)['all_explicit_data_paths'])
        wrong = copy.deepcopy(bundle); wrong['scope']['model_id'] = 'B502S33'
        wrong_item = {**item, 'aggregated_output': json.dumps({'ok': True, 'result': {'bundle': wrong}})}
        self.assertFalse(probe.data_commands([wrong_item], 'runtime-data/catalog', data)['exact_bundle_scope_observed'])

    def test_postprocessing_failure_preserves_partial_report_and_cannot_retry(self):
        report = self.base / 'report'
        report.mkdir()
        first = self.accepted(); first['turn_usage'] = probe.ev.usage_delta(None)
        probe.ev.dump(report / 'first-result.json', first)
        before = (report / 'first-result.json').read_bytes()
        with patch.object(probe, '_run', side_effect=RuntimeError('diagnostic failed')):
            value = probe.run(report)
        self.assertEqual(value['rows'], [first]); self.assertFalse(value['flow_contract_passed'])
        self.assertEqual(before, (report / 'first-result.json').read_bytes())
        probe.ev.dump(report / 'started.json', {'actual': True})
        with patch.object(probe, '_run') as retry:
            with self.assertRaises(ValueError): probe.run(report)
            retry.assert_not_called()

    def test_second_execution_usage_survives_missing_postprocessed_result(self):
        report = self.base / 'partial'
        first_usage = {k: 100 for k in probe.ev.FIELDS}
        second_usage = {k: 130 for k in probe.ev.FIELDS}
        for arm, usage in (('first', first_usage), ('second', second_usage)):
            probe.ev.dump(report / arm / 'execution.json', {'status': 'succeeded', 'native_id': 'same-id',
                'usage': usage, 'rollout': {'cumulative_usage': usage}})
        with patch.object(probe, '_run', side_effect=RuntimeError('postprocess failed')):
            result = probe.run(report)
        self.assertEqual(result['native_inputs'], 2)
        self.assertEqual(result['rows'][1]['turn_usage']['input_tokens'], 30)
        self.assertEqual(result['usage']['input_tokens']['known_sum'], 130)
        self.assertFalse(result['flow_contract_passed'])

    def test_cli_fallback_requires_observed_scope_and_same_identity_delta(self):
        first = {'cumulative_usage': {k: 100 for k in probe.ev.FIELDS}, 'rollout': {'cumulative_usage': None}}
        second = {'cumulative_usage': {k: 130 for k in probe.ev.FIELDS}}
        self.assertIsNone(probe.cumulative(first))
        self.assertEqual(probe.cumulative(first, True), first['cumulative_usage'])
        self.assertEqual(probe.turn_usage(probe.cumulative(second, True), probe.cumulative(first, True), 1, True)['input_tokens'], 30)
        self.assertIsNone(probe.turn_usage(probe.cumulative(second, True), probe.cumulative(first, True), 1, False)['input_tokens'])
        self.assertIsNone(probe.turn_usage(probe.cumulative(first, True), probe.cumulative(second, True), 1, True)['input_tokens'])


if __name__ == '__main__':
    unittest.main()
