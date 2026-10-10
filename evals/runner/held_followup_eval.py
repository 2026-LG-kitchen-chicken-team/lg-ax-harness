"""Development-only, bounded real-source held/resume and dataset-rebinding probe.

The version-only clone preserves all observed source content/origin. It is a
diagnostic registration, not fresh web evidence or a product/demo dataset.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import native_eval as ev
from extended_eval import command_for, turn_usage
from source_instruction_eval import command_outputs, final_observation, json_objects
from product_tools.conversation import Conversation
from product_tools.state import StateStore
from product_tools.planning import review_product_result

QUESTIONS = (
    "T876MQQ012의 실제 후기와 기존 수납 기능을 비교해서, 폭300·깊이200·높이250mm 용기 두 개를 같은 선반에 넣고 꺼내기 쉬운 개선안을 검토해줘. 수납 가능 여부는 실제 내부 선반 치수로 확인해줘. 이번에는 저장된 자료만 사용해줘.",
    "내부 치수로 용기 두 개의 수납을 보증하는 조건은 제외할게. 같은 모델의 실제 후기와 기존 기능을 기준으로, 추가 하드웨어 없는 적재·사용 안내 개선안 1개 이내를 다시 검토해줘.",
)


def cumulative(execution, cli_scope_verified=False):
    """CLI fallback only for a version whose resumed cumulative scope was observed."""
    rollout = (execution.get('rollout') or {}).get('cumulative_usage')
    return rollout if rollout is not None else execution.get('cumulative_usage') if cli_scope_verified else None


def clone_version(source, target, version):
    """Rebind an immutable real catalog, without fabricating web observations."""
    source, target = Path(source).resolve(strict=True), Path(target).resolve()
    original = ev.Dataset(source)
    if original.synthetic or version == original.version or target.exists() or target.is_relative_to(source):
        raise ValueError("Use real sources, a new version and a fresh separate target")
    # Validate version syntax before any filesystem write.
    from product_tools.contracts import identifier
    identifier(version, 'data_version')
    old_hashes = {name: ev.sha(source / name) for name in ('manifest.json', 'models.json', 'sources.jsonl')}
    target.mkdir(parents=True)
    shutil.copyfile(source / 'models.json', target / 'models.json')
    records = [{**record, 'data_version': version} for record in original.sources.values()]
    (target / 'sources.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records), encoding='utf-8')
    manifest = {**original.manifest, 'data_version': version,
        'provenance': 'diagnostic_rebinding; no_new_web_evidence; exact original sources/origin preserved; not demonstration material',
        'files': [{'path': name, 'sha256': ev.sha(target / name)} for name in ('models.json', 'sources.jsonl')]}
    ev.dump(target / 'manifest.json', manifest)
    copied = ev.Dataset(target)
    if copied.models != original.models or copied.fingerprint == original.fingerprint:
        raise ValueError('Diagnostic scope or fingerprint incorrect')
    for sid, record in original.sources.items():
        expected = {**record, 'data_version': version}
        if copied.sources[sid] != expected:
            raise ValueError('Source meaning/provenance changed')
    if old_hashes != {name: ev.sha(source / name) for name in old_hashes}:
        raise ValueError('Original source files changed')
    return copied


def can_continue(row):
    execution = row.get('execution') or {}
    return bool(execution.get('status') == 'succeeded' and execution.get('turn_completed') is True
        and bool(execution.get('native_id')) and row.get('saved_match') is True
        and row.get('structural_valid') is True and row.get('saved_accepted') is True and row.get('result_status') == 'held'
        and row.get('original_handle_preserved') is True and row.get('export_matches') is True
        and row.get('installed_integrity') is True and row.get('state', {}).get('valid') is True
        and row.get('native_final_matches') is True and row.get('trace_integrity') is True)


def export_matches(export, state, answer):
    """Require the actual request and final candidate, not just any export file."""
    if not answer or export.get('session_id') != state.get('session_id'):
        return False
    turns = [t for t in export.get('turns', []) if t.get('state', {}).get('turn_id') == state.get('turn_id')]
    requests = [r for r in export.get('requests', []) if r.get('turn_id') == state.get('turn_id')]
    if len(turns) != 1 or len(requests) != 1 or not turns[0].get('candidates'):
        return False
    candidate = turns[0]['candidates'][-1]
    return (turns[0]['state'] == state and candidate.get('result') == answer['result']
        and candidate.get('validation', {}).get('assessment') == answer['assessment']
        and requests[0].get('input', {}).get('request_key') == state['request_key']
        and requests[0].get('input', {}).get('question') == state['input']['question'])


def data_commands(items, path, data):
    """Audit observed direct CLI invocations and an exact successful bundle."""
    pattern = r'(?:scripts[\\/]run\.py|product-tools[\\/]cli\.py)[\'"]?\s+([^\r\n;]+)'
    invocations = []
    scope_observed = False
    model = next(m for m in data.models if m['model_id'] == 'T876MQQ012')
    expected_scope = {k: model[k] for k in ('model_id', 'model_version', 'document_version')}
    for item in items:
        matches = re.findall(pattern, item.get('command', ''))
        for match in matches:
            flags = re.findall(r'--data\s+[\'"]?([^\s\'"]+)', match)
            invocations.append({'item_id': item.get('id'), 'command': match,
                'data_path_matches': flags == [path], 'exit_code': item.get('exit_code')})
        if item.get('exit_code') != 0 or not matches:
            continue
        for output in json_objects(item.get('aggregated_output', '')):
            result = output.get('result')
            bundle = result.get('bundle') if output.get('ok') is True and isinstance(result, dict) else None
            if isinstance(bundle, dict) and bundle.get('scope') == expected_scope and bundle.get('data_version') == data.version and bundle.get('dataset_fingerprint') == data.fingerprint:
                scope_observed = True
    return {'invocations': invocations, 'all_explicit_data_paths': bool(invocations) and all(i['data_path_matches'] for i in invocations),
        'exact_bundle_scope_observed': scope_observed, 'scope': 'observed direct CLI invocations; not hidden backend calls'}


def observe(workspace, directory, execution, dataset_path, expected_handle=None):
    ev.dump(directory / 'execution.json', execution)
    row = {'execution': execution, 'result_status': None, 'structural_valid': False,
           'saved_match': None, 'exports': [], 'export_matches': False, 'semantic_status': 'unverified'}
    try:
        data = ev.Dataset(dataset_path)
        row['installation_check'] = ev.load_installer(directory.parent / 'source').check(workspace)
        row['installed_integrity'] = not row['installation_check']['errors']
        row['data_commands'] = data_commands(command_outputs(directory / 'native.jsonl'),
            Path(dataset_path).relative_to(workspace).as_posix(), data)
        raw, origin, completed = final_observation(directory)
        messages = [json.loads(line).get('item', {}) for line in (directory / 'native.jsonl').read_text(encoding='utf-8').splitlines() if line.strip().startswith('{')]
        finals = [m['text'] for m in messages if m.get('type') == 'agent_message' and isinstance(m.get('text'), str)]
        row['native_final_matches'] = bool(completed and finals and finals[-1].strip() == raw.strip()
            and ev.parse_cli(directory / 'native.jsonl')['native_id'] == execution.get('native_id'))
        row['trace_integrity'] = all(ev.sha(directory / filename) == execution.get(key)
            for filename, key in (('prompt.txt', 'prompt_sha256'), ('native.jsonl', 'stdout_sha256'), ('stderr.txt', 'stderr_sha256')))
        answer = ev.parse_answer(raw)
        candidates = ev.stored_candidates(workspace)
        row.update(answer=answer, candidates=candidates, final_origin=origin, native_completed=completed,
                   final_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(), dataset_fingerprint=data.fingerprint)
        if candidates:
            latest = candidates[-1]
            store = StateStore(workspace / 'runtime-data/product.sqlite', data)
            try:
                state = store.get_turn(latest['session_id'], latest['turn_id'])
                validation = review_product_result(data, {'input': state['input'], **answer}) if answer else None
            finally:
                store.close()
            row.update(state=state, structure=validation, result_status=answer['result']['status'] if answer else None,
                saved_match=answer == {'result': latest['result'], 'assessment': latest['validation'].get('assessment')},
                saved_accepted=(latest['validation'].get('contract_valid') is True
                    and latest['validation'].get('review', {}).get('can_finalize_reported_result') is True
                    and state['valid'] is True and bool(answer) and state['status'] == answer['result']['status']),
                structural_valid=bool(validation and validation.get('contract_valid')),
                original_handle_preserved=(expected_handle is None or
                    (all(c['turn_id'] == expected_handle['turn_id'] for c in candidates)
                     and latest['session_id'] == expected_handle['session_id']
                     and state['request_key'] == expected_handle['request_key'])))
        for path in sorted((workspace / 'runtime-data/exports').glob('*.json')):
            export = json.loads(path.read_text(encoding='utf-8'))
            row['exports'].append({'path': path.relative_to(workspace).as_posix(), 'sha256': ev.sha(path),
                'session_id': export['session_id'], 'turns': export['turns'], 'requests': export['requests']})
            if candidates and export_matches(export, state, answer):
                row['export_matches'] = True
    except Exception as exc:
        row['observation_error'] = str(exc)
    return row


def prepare(root, report):
    root, report = Path(root).resolve(), Path(report).resolve()
    if not report.is_relative_to(root / '.harness') or report.exists():
        raise ValueError('Fresh report below ignored .harness required')
    report.mkdir(parents=True)
    hashes = ev.freeze(root, report / 'source')
    workspace = Path(tempfile.mkdtemp(prefix='lg-v51-held-followup-')).resolve() / 'product'
    ev.load_installer(report / 'source').install(workspace, root=report / 'source')
    sync = subprocess.run(['uv', 'sync', '--locked'], cwd=workspace, capture_output=True, timeout=90)
    if sync.returncode:
        raise RuntimeError('Isolated sync failed')
    request = {'question': QUESTIONS[0], 'model_id': 'T876MQQ012', 'user_submitted': True,
               'constraints': {'max_concepts': 1, 'hardware_allowed': False, 'exclude_pains': []}}
    input_path = workspace / 'runtime-data/received-question.json'
    ev.dump(input_path, request)
    prepared = subprocess.run(['uv', 'run', 'python', 'product-tools/cli.py', 'open_request_bundle',
        '--input', str(input_path)], cwd=workspace, capture_output=True, timeout=30)
    (report / 'initial-reception.stdout').write_bytes(prepared.stdout)
    (report / 'initial-reception.stderr').write_bytes(prepared.stderr)
    if prepared.returncode:
        raise RuntimeError('Actual initial Tool reception failed')
    handle = json.loads(prepared.stdout)['result']['turn']
    ev.dump(report / 'prepared.json', {'workspace': str(workspace), 'source': hashes,
        'handle': {k: handle[k] for k in ('session_id', 'request_key', 'turn_id')},
        'first_input': request, 'native_inputs_limit': 2, 'timeout_seconds': 420, 'automatic_retry': False,
        'preopen_scope': 'general Tool reception before native recovery, not native-created handle',
        'version_change': 'diagnostic version-only copy; no fresh web observation/import', 'sync_exit_code': 0})


def _run(report):
    report = Path(report).resolve()
    plan = json.loads((report / 'prepared.json').read_text(encoding='utf-8'))
    if (report / 'started.json').exists():
        raise ValueError('No silent retry of native inputs')
    codex = shutil.which('codex')
    if not codex or (sys.platform == 'win32' and Path(codex).suffix.lower() != '.exe'):
        raise RuntimeError('Native executable required')
    version = subprocess.run([codex, '--version'], capture_output=True, text=True, timeout=10)
    cli_version = version.stdout.strip() if version.returncode == 0 else None
    # S05-R06 actual same-ID resume: CLI total == rollout total for 0.162.0.
    cli_scope_verified = cli_version == 'codex-cli 0.162.0'
    workspace, handle = Path(plan['workspace']), plan['handle']
    original_data = workspace / 'data/business/lg-research-v3'
    ev.dump(report / 'started.json', {'at': datetime.now(timezone.utc).isoformat(), 'native_inputs_limit': 2,
        'observed_cli_version': cli_version, 'cli_cumulative_scope_verified': cli_scope_verified,
        'runner_sha256': ev.sha(Path(__file__)), 'helper_sha256': ev.sha(Path(ev.__file__))})
    shutil.copyfile(__file__, report / 'runner-frozen.py')
    shutil.copyfile(ev.__file__, report / 'helper-frozen.py')
    first_prompt = (QUESTIONS[0] + '\n이 업무 요청은 중단 전 일반 Tool로 이미 접수돼 있다. 같은 요청을 재개한다. '
        + json.dumps(handle, ensure_ascii=False) + '\n현재 저장된 data/business/lg-research-v3만 사용하고 외부 웹/API/다른자료·소스/설정 변경은 금지다. 설치된 업무 Agent·Skill로 조회·검토·저장·export한다. 새 요청으로 초기화하지 않는다. 다른 Agent를 생성하거나 위임하지 않고 메인이 직접 수행한다.\n' + ev.OUTPUT_CONTRACT)
    first_dir = report / 'first'
    execution = ev.execute(command_for(codex, workspace, first_dir / 'final.txt'), workspace, first_prompt, first_dir, 420)
    first = observe(workspace, first_dir, execution, original_data, handle)
    first['turn_usage'] = execution['usage']
    ev.dump(report / 'first-result.json', first)
    if not can_continue(first):
        value = {'rows': [first], 'native_inputs': 1, 'followup': 'not_run_first_not_accepted',
                 'flow_contract_passed': False, 'semantic_status': 'unverified'}
        ev.dump(report / 'results.json', value)
        return value
    # The second evaluation input arrives before diagnostic rebinding/new turn.
    ev.dump(report / 'second-input-arrived.json', {'question': QUESTIONS[1], 'at': datetime.now(timezone.utc).isoformat(),
        'session_id': handle['session_id'], 'prior_turn_id': handle['turn_id']})
    version = 'lg-research-v3-diagnostic-rebinding-20261010'
    target = workspace / 'runtime-data/catalogs' / version
    copied = clone_version(original_data, target, version)
    store = StateStore(workspace / 'runtime-data/product.sqlite', copied)
    try:
        count_before = store.db.execute('SELECT count(*) FROM turns').fetchone()[0]
        stale = Conversation(store, workspace).current_request({k: handle[k] for k in ('session_id', 'request_key')})
        count_after = store.db.execute('SELECT count(*) FROM turns').fetchone()[0]
    finally:
        store.close()
    ev.dump(report / 'diagnostic-transition.json', {'data_path': target.relative_to(workspace).as_posix(),
        'data_version': copied.version, 'fingerprint': copied.fingerprint, 'old_current_request': stale,
        'turn_count_before': count_before, 'turn_count_after': count_after, 'fresh_web_or_import': False})
    next_prompt = (QUESTIONS[1] + '\n실제 평가 추가 입력이며 같은 업무 session_id=' + handle['session_id']
        + ', prior_turn_id=' + handle['turn_id'] + '를 연결한다. 이번 입력이 도착한 뒤 turn 시작 전에 일반 코드가 동일한 실제 원문을 진단용 새 data_version으로 등록했다. 새 웹 원문 관측이나 import가 아니며 출처 내용/위치/지문/origin은 동일하다. 모든 업무 Tool에 --data '
        + target.relative_to(workspace).as_posix() + '를 명시한다. 이전 결과는 역사적 참조이며 변경 조건으로 재검토하고 이력은 보존한다. 외부 웹/API/다른자료·소스/설정 변경과 서브에이전트 위임을 하지 않는다. 실제 저장·export 뒤 결과를 반환한다.\n' + ev.OUTPUT_CONTRACT)
    second_dir = report / 'second'
    second_execution = ev.execute(command_for(codex, workspace, second_dir / 'final.txt', execution['native_id']),
                                  workspace, next_prompt, second_dir, 420)
    second = observe(workspace, second_dir, second_execution, target)
    same_id = second_execution.get('native_id') == execution['native_id']
    second['turn_usage'] = turn_usage(cumulative(second_execution, cli_scope_verified),
        cumulative(execution, cli_scope_verified), 1, same_id)
    ev.dump(report / 'second-result.json', second)
    old_candidates_preserved = bool(second.get('candidates')) and second['candidates'][:len(first['candidates'])] == first['candidates']
    old_exports_preserved = all((workspace / e['path']).is_file() and ev.sha(workspace / e['path']) == e['sha256'] for e in first['exports'])
    state = second.get('state') or {}
    flow = {'same_native_id': same_id, 'same_business_session': state.get('session_id') == handle['session_id'],
        'new_turn': state.get('turn_id') not in (None, handle['turn_id']),
        'new_request': state.get('input', {}).get('request_key') not in (None, handle['request_key']),
        'new_dataset': state.get('input', {}).get('data_version') == version,
        'exact_followup_question': state.get('input', {}).get('question') == QUESTIONS[1],
        'same_model_scope': state.get('input', {}).get('model_scope') == first.get('state', {}).get('input', {}).get('model_scope'),
        'same_explicit_constraints': state.get('input', {}).get('constraints') == first.get('state', {}).get('input', {}).get('constraints'),
        'source_content_preserved': copied.models == ev.Dataset(original_data).models,
        'old_current_stale': stale['turn']['turn_id'] == handle['turn_id'] and stale['turn']['valid'] is False and stale['turn']['latest_result'] is None,
        'old_current_did_not_create_turn': count_before == count_after == 1,
        'old_candidates_preserved': old_candidates_preserved, 'old_exports_preserved': old_exports_preserved,
        'second_succeeded': second_execution['status'] == 'succeeded' and second_execution.get('turn_completed') is True,
        'second_structural_saved_match': second.get('structural_valid') is True and second.get('saved_match') is True and second.get('saved_accepted') is True,
        'second_fresh_state': state.get('valid') is True,
        'second_native_final_and_trace': second.get('native_final_matches') is True and second.get('trace_integrity') is True,
        'product_source_unchanged': first.get('installed_integrity') is True and second.get('installed_integrity') is True,
        'second_export_matches': second.get('export_matches') is True,
        'second_all_explicit_data': second.get('data_commands', {}).get('all_explicit_data_paths') is True,
        'second_exact_bundle_scope': second.get('data_commands', {}).get('exact_bundle_scope_observed') is True,
        'two_distinct_business_turns': len({r['turn_id'] for r in second.get('candidates', [])}) == 2,
        'second_prior_turn': any(r.get('turn_id') == state.get('turn_id') and r.get('input', {}).get('prior_turn_id') == handle['turn_id']
            for e in second['exports'] for r in e.get('requests', [])),
        'second_session_exported': any(len(e['turns']) == 2 and e['session_id'] == handle['session_id'] for e in second['exports'])}
    value = {'rows': [first, second], 'native_inputs': 2, 'flow_checks': flow,
        'flow_contract_passed': all(flow.values()), 'usage': ev.usage_totals([first['turn_usage'], second['turn_usage']]),
        'semantic_status': 'unverified', 'whole_backend_calls_or_cost': None, 'fresh_web_or_native_import': False}
    ev.dump(report / 'results.json', value)
    return value


def run(report):
    """Preserve partial actual observations if diagnostic/postprocessing fails."""
    report = Path(report).resolve()
    if (report / 'started.json').exists():
        raise ValueError('No silent retry of native inputs')
    try:
        return _run(report)
    except Exception as exc:
        rows = []
        previous = None
        started_path = report / 'started.json'
        cli_scope_verified = (json.loads(started_path.read_text(encoding='utf-8')).get('cli_cumulative_scope_verified') is True) if started_path.exists() else False
        for index, arm in enumerate(('first', 'second')):
            result_path, execution_path = report / (arm + '-result.json'), report / arm / 'execution.json'
            if result_path.exists():
                row = json.loads(result_path.read_text(encoding='utf-8'))
            elif execution_path.exists() or (report / arm / 'prompt.txt').exists():
                execution = json.loads(execution_path.read_text(encoding='utf-8')) if execution_path.exists() else {
                    'status': 'unobserved', 'native_id': None, 'usage': ev.usage_delta(None)}
                row = {'execution': execution, 'postprocess_status': 'failed', 'semantic_status': 'unverified'}
                same_id = bool(previous and execution.get('native_id') and execution.get('native_id') == previous.get('native_id'))
                row['turn_usage'] = (execution.get('usage', ev.usage_delta(None)) if index == 0 else
                    turn_usage(cumulative(execution, cli_scope_verified),
                        cumulative(previous, cli_scope_verified) if previous else None, index, same_id))
            else:
                continue
            rows.append(row)
            previous = row.get('execution')
        attempts = sum((report / name / 'prompt.txt').exists() for name in ('first', 'second'))
        value = {'rows': rows, 'native_inputs': len(rows), 'native_input_attempts': attempts,
            'flow_contract_passed': False, 'semantic_status': 'unverified', 'runner_error': str(exc),
            'usage': ev.usage_totals([r.get('turn_usage', ev.usage_delta(None)) for r in rows]),
            'whole_backend_calls_or_cost': None, 'fresh_web_or_native_import': False}
        ev.dump(report / 'partial-failure.json', value)
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run'))
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(ev.ROOT, args.report)
        return 0
    result = run(args.report)
    print(json.dumps({'native_inputs': result['native_inputs'], 'flow_contract_passed': result['flow_contract_passed'],
                      'semantic_status': result['semantic_status']}))
    return 0 if result['flow_contract_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
