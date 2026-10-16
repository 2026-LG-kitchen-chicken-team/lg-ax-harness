"""Mechanical blank candidate envelope. Never generates claims or review decisions."""
from .contracts import fail, identifier, integer


def candidate_template(turn):
    """Bind a blank candidate to an observed turn/version without changing state.

    Empty status is deliberately invalid until the AI authors a status, claims,
    reasons and assessment. Re-reading the same version gives the same key.
    """
    if (not isinstance(turn, dict) or turn.get('valid') is not True
            or turn.get('status') in ('failed', 'cancelled')):
        fail('candidate_unavailable', 'A current valid nonterminal turn is required')
    session = identifier(turn.get('session_id'), 'session_id')
    handle = identifier(turn.get('turn_id'), 'turn_id')
    version = integer(turn.get('result_version'), 'result_version', 0, 2)
    used = {r['result_key'] for r in turn.get('result_history', [])}
    base = 'candidate-' + str(version)
    key, suffix = base, 0
    while key in used:
        suffix += 1
        key = base + '-' + str(suffix)
    return {'session_id': session, 'turn_id': handle,
            'result_key': key, 'expected_result_version': version,
            'result': {'status': '', 'pains': [], 'existing_features': [],
                       'remaining_pains': [], 'concepts': [], 'assumptions': [],
                       'evidence_refs': [], 'decision_notes': [], 'validation_findings': [],
                       'revisions': version, 'usage_summary': {'status': 'unknown'}},
            'assessment': {'claim_checks': [], 'feature_matches': [], 'concept_links': []}}
