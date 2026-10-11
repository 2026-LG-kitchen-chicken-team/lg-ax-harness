"""Read actual Claude native JSONL; never synthesizes Codex delivery events.

Hidden reasoning is neither returned nor required. Usage is counted once per
native assistant message id; this is observed trace coverage, not billing proof.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path

FIELDS = ('input_tokens', 'cache_creation_input_tokens',
          'cache_read_input_tokens', 'output_tokens')


def audit_trace(path, session_id, prompt):
    raw = Path(path).read_bytes()
    rows = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    if any(r.get('sessionId') not in (None, session_id) for r in rows):
        raise ValueError('Other native session in trace')
    if any(r.get('type') in ('user', 'assistant') and not r.get('isSidechain')
           and r.get('sessionId') != session_id for r in rows):
        raise ValueError('Actual main native session identity required')
    starts = [i for i, r in enumerate(rows) if r.get('type') == 'user'
              and not r.get('isSidechain') and r.get('message', {}).get('content') == prompt]
    if len(starts) != 1:
        raise ValueError('Exactly one actual user prompt required')
    start = starts[0]
    end = next((i for i in range(start + 1, len(rows)) if rows[i].get('type') == 'user'
                and isinstance(rows[i].get('message', {}).get('content'), str)
                and not rows[i].get('isSidechain')), len(rows))
    turn = rows[start:end]
    messages, finals, tools, seen_rows, final_blocks, main_rows = {}, [], set(), set(), {}, []
    for r in turn:
        if r.get('type') != 'assistant' or r.get('isSidechain'):
            continue
        m = r.get('message', {})
        mid = m.get('id')
        if not isinstance(mid, str) or not mid:
            raise ValueError('Native assistant message id required')
        previous = messages.get(mid)
        usage = m.get('usage')
        if previous and isinstance(previous.get('usage'), dict) and isinstance(usage, dict):
            for field in FIELDS:
                before, now = previous['usage'].get(field), usage.get(field)
                if before != now:
                    raise ValueError('Conflicting duplicate native usage')
        # Missing usage must not erase an earlier observed record.
        if not previous or isinstance(usage, dict):
            messages[mid] = m
        row_id = r.get('uuid')
        if row_id and row_id in seen_rows:
            continue
        if row_id:
            seen_rows.add(row_id)
        main_rows.append(r)
        for block in m.get('content', []):
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tools.add(block.get('id'))
        texts = [b.get('text') for b in m.get('content', [])
                 if isinstance(b, dict) and b.get('type') == 'text' and isinstance(b.get('text'), str)]
        if m.get('stop_reason') == 'end_turn' and texts:
            finals.append((r, ''.join(texts)))
            index = r.get('apiBlockIndex')
            key = (mid, index) if type(index) is int else (mid, row_id or len(finals))
            previous_text = final_blocks.get(key)
            if previous_text is not None and previous_text != ''.join(texts):
                raise ValueError('Conflicting final block replay')
            final_blocks[key] = ''.join(texts)
    if not finals or main_rows[-1] != finals[-1][0]:
        raise ValueError('Last native assistant text must have actual end_turn')
    final = finals[-1][0]
    text = ''.join(value for (mid, _), value in final_blocks.items() if mid == final['message']['id'])
    totals = {}
    for field in FIELDS:
        values = [m.get('usage', {}).get(field) if isinstance(m.get('usage'), dict) else None
                  for m in messages.values()]
        known = [v for v in values if type(v) is int and v >= 0]
        totals[field] = {'known_sum': sum(known) if known else None,
                         'unknown_messages': len(values) - len(known)}
    complete = all(v['unknown_messages'] == 0 for v in totals.values())
    input_total = sum(totals[k]['known_sum'] for k in FIELDS[:3]) if complete else None
    stamp = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00'))
    elapsed = (stamp(final['timestamp']) - stamp(rows[start]['timestamp'])).total_seconds()
    if elapsed < 0:
        raise ValueError('Native timestamps reversed')
    return {'native_id': session_id, 'trace_sha256': hashlib.sha256(raw).hexdigest(),
            'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
            'elapsed_seconds': round(elapsed, 3), 'final_text': text,
            'final_sha256': hashlib.sha256(text.encode()).hexdigest(),
            'native_final_observed': True, 'assistant_messages': len(messages),
            'tool_use_ids': len(tools), 'models': sorted({m.get('model', 'unknown') for m in messages.values()}),
            'usage': totals, 'observed_input_total': input_total,
            'usage_scope': 'unique assistant message ids in this main native turn; backend/subagents/billing unverified'}
