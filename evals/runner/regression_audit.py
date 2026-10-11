"""Audit an immutable native fifty-input run and independent review sidecars.

Successor auditor: fixes Windows CRLF recording comparison without changing
frozen runner, input, native output or original receipt. No model calls. Historical parent receipts are evaluated at delivery time, not
reinterpreted as currently valid after a legitimate followup invalidates them.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import regression_eval as runner


def prompt_text_matches(path, job):
    # Windows text-mode recording uses CRLF. Preserve/audit original byte SHA
    # separately; normalize only that representation for frozen input equality.
    recorded = path.read_bytes().decode('utf-8').replace('\r\n', '\n')
    return (recorded == job['prompt']
            and hashlib.sha256(recorded.encode('utf-8')).hexdigest() == job['prompt_sha256'])


def recorded_json_matches(path, value):
    # Audit the original object representation, without rewriting byte evidence.
    recorded = path.read_bytes().decode('utf-8').replace('\r\n', '\n')
    return recorded == json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def semantic_pass(review):
    scores = review.get('scores')
    if not isinstance(scores, list) or len(scores) != 7:
        raise ValueError('Seven axes with explicit N/A required')
    if any(s is not None and (type(s) is not int or s not in (0, 1, 2)) for s in scores):
        raise ValueError('Invalid semantic score')
    applied = [s for s in scores if s is not None]
    if not applied or not isinstance(review.get('critical_errors'), list):
        raise ValueError('Applicable axes/critical review required')
    return (sum(applied) * 14 >= len(applied) * 2 * 12
            and min(applied) > 0 and not review['critical_errors'])


def audit(report, review_file=None):
    plan = runner.verify_plan(report)
    original = json.loads((report / 'results.json').read_text(encoding='utf-8'))
    rows = original['results']
    if len(rows) != 50 or [r['job'] for r in rows] != [j['name'] for j in plan['jobs']]:
        raise ValueError('Exactly fifty unique planned result rows required')
    reviews = {}
    review_sha = None
    if review_file:
        data = json.loads(review_file.read_text(encoding='utf-8'))
        reviews = {r['id']: r for r in data['reviews']}
        if len(reviews) != len(data['reviews']):
            raise ValueError('Duplicate semantic review IDs')
        review_sha = runner.ev.sha(review_file)
    outcomes = []
    for job, row in zip(plan['jobs'], rows):
        directory = report / row['job']
        if row['case'] != job['case']:
            raise ValueError('Recorded case differs from frozen input')
        if not recorded_json_matches(directory / 'result.json', row):
            raise ValueError('Aggregate result differs from original per-input record')
        observed = row.get('execution')
        if observed:
            for filename, key in (('prompt.txt','prompt_sha256'), ('native.jsonl','stdout_sha256'), ('stderr.txt','stderr_sha256')):
                if observed.get(key) and runner.ev.sha(directory / filename) != observed[key]:
                    raise ValueError('Native raw evidence changed: ' + row['job'] + '/' + filename)
            if (directory / 'prompt.txt').exists() and not prompt_text_matches(directory / 'prompt.txt', job):
                raise ValueError('Actual submitted prompt differs from freeze')
        if row['acceptance'] == 'contract_and_delivery_passed':
            if runner.receipt.final_message(directory, observed) != row['summary']:
                raise ValueError('Delivered final differs from original observation')
            pointer = row['pointer']
            exported = runner.receipt.artifact(Path(job['workspace']), pointer['export'])
            if job['case']['parent_id'] and row.get('followup_linked') is not True:
                raise ValueError('Accepted followup lacks native/history linkage')
            if row.get('terminal_status') == 'needs_input' and exported['turns']:
                raise ValueError('Pending clarification invented a turn')
        review = reviews.get(row['job'])
        if review and review.get('raw_result_sha256') != runner.ev.sha(directory / 'result.json'):
            raise ValueError('Semantic review not bound to original output: ' + row['job'])
        review_passed = semantic_pass(review) if review and review.get('scores') is not None else None
        overall = row['acceptance'] == 'contract_and_delivery_passed' and review_passed is True
        outcomes.append({'id':row['job'], 'category':job['case']['category'], 'model_id':job['case']['model_id'],
            'parent_id':job['case']['parent_id'], 'execution':observed.get('status') if observed else 'not_run',
            'delivery':row['acceptance'], 'terminal_status':row.get('terminal_status'),
            'seconds':observed.get('elapsed_seconds') if observed else None,
            'semantic_passed':review_passed, 'overall_passed':overall,
            'scores':review.get('scores') if review else None,
            'critical_errors':review.get('critical_errors') if review else None,
            'findings':review.get('findings') if review else [],
            'raw_result_sha256':runner.ev.sha(directory / 'result.json')})
    return {'planned_inputs':50,'conversations':40,'native_attempts':original['native_attempts'],
        'source_prepared_sha256':runner.ev.sha(report / 'prepared.json'),
        'raw_aggregate_sha256':runner.ev.sha(report / 'results.json'),
        'review_sha256':review_sha, 'collector_sha256':runner.ev.sha(Path(__file__)),
        'prompt_recording':'Raw SHA preserved; only CRLF-to-LF normalized for frozen prompt and per-row JSON representation equality',
        'execution_counts':dict(Counter(o['execution'] for o in outcomes)),
        'delivery_counts':dict(Counter(o['delivery'] for o in outcomes)),
        'terminal_counts':dict(Counter(o['terminal_status'] for o in outcomes)),
        'semantically_reviewed':sum(o['scores'] is not None for o in outcomes),
        'overall_passed':sum(o['overall_passed'] for o in outcomes),
        'critical_error_inputs':sum(bool(o['critical_errors']) for o in outcomes),
        'usage':runner.session_usage(rows), 'outcomes':outcomes,
        'official_questions':False,'independent_holdout':False,'baseline_comparison':False,
        'fault_injection':False,'billing':None,'human_time':None,
        'limitations':['AI independent review of known short sources and hinted public questions',
           'Single Codex environment / max1concept / nohardware; no Claude, browser or fault validation',
           'Native attempts/sessions/token events are not full backend calls or cash billing',
           'Scores use this suite rubric; not directly comparable to previous14-point rubrics']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--reviews',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=args.report.resolve()
    output=args.output.resolve()
    if not report.is_relative_to((runner.ev.ROOT/'.harness').resolve()) or output.exists():
        raise ValueError('Use a private existing run and a new audit sidecar')
    runner.ev.dump(output,audit(report,args.reviews.resolve() if args.reviews else None))
    print(json.dumps({'audit':str(output),'model_calls':0},ensure_ascii=False))


if __name__=='__main__':main()
