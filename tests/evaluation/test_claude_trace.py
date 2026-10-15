import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'evals/runner'))
from claude_trace import audit_trace


class ClaudeTrace(unittest.TestCase):
    def rows(self):
        u = {'input_tokens': 2, 'cache_creation_input_tokens': 3,
             'cache_read_input_tokens': 7, 'output_tokens': 5}
        def row(content, usage=u, stop='end_turn'):
            return {'type': 'assistant', 'sessionId': 'native-one', 'timestamp': '2026-10-11T00:00:02Z',
                    'message': {'id': 'message-one', 'model': 'observed-model', 'content': content,
                                'stop_reason': stop, 'usage': usage}}
        return [{'type': 'user', 'sessionId': 'native-one', 'timestamp': '2026-10-11T00:00:00Z',
                 'message': {'content': 'actual prompt'}},
                row([{'type': 'thinking', 'thinking': 'never emit'}]),
                row([{'type': 'text', 'text': 'actual final'}])]

    def audit(self, rows):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'native.jsonl'
            p.write_text('\n'.join(json.dumps(r) for r in rows), encoding='utf-8')
            return audit_trace(p, 'native-one', 'actual prompt')

    def test_streamed_parts_count_once_and_hide_thinking(self):
        v = self.audit(self.rows())
        self.assertEqual(v['assistant_messages'], 1)
        self.assertEqual(v['usage']['output_tokens']['known_sum'], 5)
        self.assertEqual(v['observed_input_total'], 12)
        self.assertNotIn('never emit', json.dumps(v))

    def test_missing_usage_is_unknown_not_zero(self):
        r = self.rows()
        for x in r[1:]: x['message']['usage'] = None
        v = self.audit(r)
        self.assertIsNone(v['observed_input_total'])
        self.assertEqual(v['usage']['output_tokens']['unknown_messages'], 1)

    def test_conflicting_duplicate_usage_rejected(self):
        r = self.rows(); r[-1]['message']['usage'] = {**r[-1]['message']['usage'], 'output_tokens': 6}
        with self.assertRaises(ValueError): self.audit(r)

    def test_tool_stop_is_not_final(self):
        r = self.rows(); r[-1]['message']['stop_reason'] = 'tool_use'
        with self.assertRaises(ValueError): self.audit(r)

    def test_other_session_and_prompt_rejected(self):
        r = self.rows(); r[-1]['sessionId'] = 'other'
        with self.assertRaises(ValueError): self.audit(r)
        r = self.rows(); r[0]['message']['content'] = 'rewritten'
        with self.assertRaises(ValueError): self.audit(r)

    def test_followup_usage_not_added_to_previous_turn(self):
        r = self.rows(); r += [{**r[0], 'message': {'content': 'followup'}}, {**r[-1], 'message': {**r[-1]['message'], 'id': 'followup'}}]
        self.assertEqual(self.audit(r)['assistant_messages'], 1)

    def test_native_peer_handback_continues_same_request_after_interim_end(self):
        r = self.rows()
        r.append({**r[0], 'timestamp': '2026-10-11T00:00:03Z', 'isMeta': True,
                  'promptSource': 'system', 'turnOrigin': 'peer',
                  'origin': {'kind': 'peer', 'from': 'actual-child', 'handback': True},
                  'message': {'content': 'Another Claude session sent a message: child report'}})
        r.append({**r[2], 'timestamp': '2026-10-11T00:00:05Z',
                  'message': {**r[2]['message'], 'id': 'after-handback',
                              'content': [{'type': 'text', 'text': 'stored current result'}]}})
        value = self.audit(r)
        self.assertEqual(value['final_text'], 'stored current result')
        self.assertEqual(value['elapsed_seconds'], 5)
        self.assertEqual(value['assistant_messages'], 2)
        self.assertEqual(value['usage']['output_tokens']['known_sum'], 10)
        self.assertEqual(value['runtime_peer_messages'], 1)
        self.assertEqual(value['native_end_turn_messages'], 2)

    def test_user_pasted_handback_prefix_is_still_a_new_user_input(self):
        r = self.rows()
        r.append({**r[0], 'message': {'content': 'Another Claude session sent a message: user text'}})
        r.append({**r[2], 'message': {**r[2]['message'], 'id': 'new-human-response',
                                    'content': [{'type': 'text', 'text': 'new response'}]}})
        value = self.audit(r)
        self.assertEqual(value['final_text'], 'actual final')
        self.assertEqual(value['assistant_messages'], 1)

    def test_partial_json_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'raw'; p.write_text('{', encoding='utf-8')
            with self.assertRaises(ValueError): audit_trace(p, 'native-one', 'actual prompt')

    def test_split_final_text_and_duplicate_uuid(self):
        r = self.rows(); r[-1]['uuid'] = 'part-one'
        second = {**r[-1], 'uuid': 'part-two', 'message': {**r[-1]['message'], 'content': [{'type': 'text', 'text': ' next part'}]}}
        r += [second, second]
        self.assertEqual(self.audit(r)['final_text'], 'actual final next part')

    def test_sidechain_does_not_replace_main_final(self):
        r = self.rows(); r += [{**r[-1], 'isSidechain': True, 'message': {**r[-1]['message'], 'id': 'child', 'content': [{'type': 'text', 'text': 'child final'}]}}]
        self.assertEqual(self.audit(r)['final_text'], 'actual final')

    def test_missing_actual_session_cannot_be_invented(self):
        r = self.rows()
        for x in r: x.pop('sessionId')
        with self.assertRaises(ValueError): self.audit(r)

    def test_block_index_replay_counted_once(self):
        r = self.rows(); r[-1]['apiBlockIndex'] = 1
        r += [{**r[-1], 'uuid': 'replayed-row'}]
        self.assertEqual(self.audit(r)['final_text'], 'actual final')


if __name__ == '__main__': unittest.main()
