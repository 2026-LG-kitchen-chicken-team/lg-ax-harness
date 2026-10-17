"""Project public native tool calls; never evaluate a command or return its text.

Only an explicit Python Skill entry point is a Skill command. Reading a file,
mentioning a path, a progress message, and arbitrary helper code are not one.
Code-mode supports literal, unconditional exec_command calls and literal
Promise.all batches. Dynamic/conditional JavaScript is deliberately unmapped.
"""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shlex
from urllib.parse import urlsplit, unquote

OPERATIONS = json.loads((Path(__file__).resolve().parents[1] / 'shared/skill-operations.json').read_text(encoding='utf-8'))
SKILLS = frozenset(('evidence-retrieval', 'needs-structuring', 'feature-comparison',
                    'concept-writing', 'review-and-revise', 'web-evidence-collection'))
ID = re.compile(r'^[A-Za-z0-9_.:-]{1,180}$')
TOKEN = re.compile(r'''\s+|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][\w$]*|-?(?:0|[1-9]\d*)(?:\.\d+)?|[{}\[\]:,]''')


def _literal(text):
    """A small data-only JS object literal reader, with no names or expressions."""
    tokens, pos = [], 0
    for match in TOKEN.finditer(text):
        if match.start() != pos:
            return None
        pos = match.end()
        token = match.group()
        if token.isspace() or token.startswith(('//', '/*')):
            continue
        tokens.append(token)
    if pos != len(text):
        return None
    encoded = []
    try:
        for i, token in enumerate(tokens):
            if token.startswith(('"', "'")):
                value = json.loads(token) if token[0] == '"' else ast.literal_eval(token)
                encoded.append(json.dumps(value))
            elif re.fullmatch(r'[A-Za-z_$][\w$]*', token):
                if i + 1 < len(tokens) and tokens[i + 1] == ':':
                    encoded.append(json.dumps(token))
                elif token in ('true', 'false', 'null'):
                    encoded.append(token)
                else:
                    return None
            else:
                encoded.append(token)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate')
                result[key] = value
            return result
        value = json.loads(''.join(encoded), object_pairs_hook=unique)
        return value if isinstance(value, dict) else None
    except (ValueError, SyntaxError, TypeError):
        return None


def _split_batch(text):
    pieces, start, depth, quote, escape = [], 0, 0, None, False
    for i, c in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == quote:
                quote = None
        elif c in ('"', "'"):
            quote = c
        elif c in '({[':
            depth += 1
        elif c in ')}]':
            depth -= 1
        elif c == ',' and depth == 0:
            pieces.append(text[start:i]); start = i + 1
        if depth < 0:
            return []
    if quote or depth:
        return []
    pieces.append(text[start:])
    return pieces if 0 < len(pieces) <= 8 else []


def literal_commands(code):
    if not isinstance(code, str) or len(code) > 128 * 1024:
        return []
    code = re.sub(r'^\s*//[^\n]*(?:\n|$)', '', code).strip()
    # Whole-program matches exclude quoted examples, branches, loops, eval and
    # calls that would happen only after some unrelated code succeeds.
    single = re.fullmatch(r'(?:await\s+tools\.exec_command\((\{[\s\S]*\})\)\s*;?|text\(\s*await\s+tools\.exec_command\((\{[\s\S]*\})\)\s*\)\s*;?)', code)
    if single:
        value = _literal(single.group(1) or single.group(2))
        return [value] if value else []
    assigned = re.fullmatch(r'(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*await\s+tools\.exec_command\((\{[\s\S]*\})\)\s*;\s*(?:text\(\s*\1\s*\)\s*;?)?', code)
    if assigned:
        value = _literal(assigned.group(2))
        return [value] if value else []
    batch = re.fullmatch(r'(?:(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*)?await\s+Promise\.all(?:Settled)?\(\s*\[([\s\S]*)\]\s*\)\s*;?\s*(?:text\(\s*\1\s*\)\s*;?)?', code)
    if batch:
        result = []
        for piece in _split_batch(batch.group(2)):
            match = re.fullmatch(r'\s*tools\.exec_command\((\{[\s\S]*\})\)\s*', piece)
            value = _literal(match.group(1)) if match else None
            if not value:
                return []
            result.append(value)
        return result
    return []


def _unquote(value):
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in ('"', "'") else value


def command_body(command):
    if isinstance(command, list) and all(isinstance(x, str) for x in command):
        for flag in ('-Command', '-command', '-c', '/c'):
            if flag in command and len(command) == command.index(flag) + 2:
                return command[-1]
        return ' '.join(command)
    return command if isinstance(command, str) else ''


def native_cwd(value):
    """Decode the local file URI used by current Windows native command events."""
    if not isinstance(value, str) or not value.lower().startswith('file:'):
        return value
    parsed = urlsplit(value)
    if parsed.scheme.lower() != 'file' or parsed.netloc not in ('', 'localhost') or parsed.query or parsed.fragment:
        raise ValueError('nonlocal cwd')
    path = unquote(parsed.path, errors='strict')
    if '\x00' in path:
        raise ValueError('invalid cwd')
    if re.match(r'^/[A-Za-z]:/', path):
        path = path[1:]
    return path


def command_skill(command, cwd, workspace):
    """Recognize the executed entry point, not a path embedded in other code."""
    command = command_body(command)
    if len(command) > 128 * 1024 or any(c in command for c in ('\n', '\r', '`', '$', ';', '|', '<', '>')):
        return None
    try:
        tokens = [_unquote(x) for x in shlex.split(command, posix=False)]
        if tokens and tokens[0] == '&':
            tokens.pop(0)
        def program(value):
            return value.replace('\\', '/').rsplit('/', 1)[-1].lower()
        if tokens and program(tokens[0]) in ('uv', 'uv.exe'):
            tokens = tokens[1:]
            if not tokens or tokens.pop(0) != 'run':
                return None
        if not tokens or program(tokens.pop(0)) not in ('python', 'python.exe', 'python3', 'python3.exe', 'py', 'py.exe'):
            return None
        while tokens and tokens[0] in ('-B', '-u', '-I', '-3', '-3.12'):
            tokens.pop(0)
        if len(tokens) < 2:
            return None
        script, operation = tokens[:2]
        if operation not in OPERATIONS:
            return None
        folder = Path(native_cwd(cwd) or workspace)
        if not folder.is_absolute():
            return None
        target = Path(script.replace('\\', '/'))
        if '..' in target.parts:
            return None
        target = target if target.is_absolute() else folder / target
        relative = target.resolve().relative_to(Path(workspace).resolve()).as_posix()
        match = re.fullmatch(r'(?:\.agents/|\.claude/)?skills/([a-z-]+)/scripts/run\.py', relative)
        if not match or match.group(1) not in SKILLS:
            return None
        return {'skill': match.group(1), 'operation': operation,
                'category': 'instruction' if OPERATIONS[operation]['kind'] == 'instruction' else 'skill' if OPERATIONS[operation]['kind'] == 'work' else 'shell'}
    except (ValueError, OSError, TypeError):
        return None


def _args(payload):
    try:
        value = payload.get('arguments', {})
        value = json.loads(value) if isinstance(value, str) else value
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def _category(payload, args):
    name, namespace = payload.get('name', ''), payload.get('namespace', '')
    namespace = namespace if isinstance(namespace, str) else ''
    if 'cua' in namespace or 'cua' in name:
        return 'browser'
    if name in ('run', 'web__run') and ('web' in namespace or 'web' in name):
        return 'web'
    if name in ('exec_command', 'write_stdin'):
        return 'shell'
    if name in ('apply_patch', 'read_file', 'list_files', 'search'):
        return 'file'
    return 'tool'


def project_calls(rows, workspace):
    """Bounded sanitized call lifecycles for the already-selected main request."""
    calls, groups, pending, processes = [], {}, [], {}
    turn = next((r.get('payload', {}).get('turn_id') for r in rows if r.get('type') == 'event_msg' and r.get('payload', {}).get('type') == 'task_started'), None)
    terminal = None
    for i, row in enumerate(rows):
        payload = row.get('payload', {})
        if not isinstance(payload, dict):
            continue
        kind, ptype, ts = row.get('type'), payload.get('type'), row.get('timestamp')
        if kind == 'event_msg' and ptype in ('task_complete', 'turn_aborted'):
            if payload.get('turn_id') not in (None, turn):
                continue
            terminal = 'cancelled' if ptype == 'turn_aborted' else 'unknown'
            for call in calls:
                if call['status'] == 'running':
                    call.update(status=terminal, ended_at=ts)
        if kind == 'response_item' and ptype in ('function_call', 'custom_tool_call') and not terminal:
            key = payload.get('call_id')
            if not isinstance(key, str) or not ID.fullmatch(key):
                continue
            args = _args(payload)
            commands = [args] if payload.get('name') == 'exec_command' else literal_commands(payload.get('input')) if payload.get('name') == 'exec' else []
            group = []
            for n, argument in enumerate(commands or [None]):
                spec = command_skill(argument.get('cmd'), argument.get('workdir'), workspace) if argument else None
                call = {'id': key + (':' + str(n) if len(commands) > 1 else ''), 'category': 'shell' if argument else _category(payload, args),
                        'status': 'running', 'started_at': ts, 'ended_at': None,
                        'skill': None, 'operation': None, 'observer_call_id': None, 'basis': 'native_tool_call'}
                if spec:
                    call.update(spec)
                calls.append(call); group.append(call)
                if argument:
                    pending.append((call, command_body(argument.get('cmd')), argument.get('workdir') or str(workspace)))
            groups[key] = group
        if kind == 'event_msg' and ptype in ('item_started', 'item_completed'):
            item = payload.get('item', {})
            if not isinstance(item, dict) or item.get('type') != 'CommandExecution':
                continue
            body = command_body(item.get('command'))
            try:
                cwd = native_cwd(item.get('cwd')) or str(workspace)
            except (ValueError, UnicodeError):
                continue
            matches = [c for c, command, directory in pending if c['status'] == 'running' and body.strip() == command.strip() and os.path.normcase(os.path.abspath(directory)) == os.path.normcase(os.path.abspath(cwd))]
            call = matches[0] if matches else processes.get(str(item.get('process_id')))
            spec = command_skill(body, cwd, workspace)
            if call is None:
                key = item.get('id')
                if not isinstance(key, str) or not ID.fullmatch(key):
                    continue
                start = ts
                duration = item.get('duration')
                if isinstance(duration, dict) and isinstance(duration.get('secs'), int) and 0 <= duration['secs'] <= 3600:
                    try:
                        start = (datetime.fromisoformat(ts.replace('Z', '+00:00')) - timedelta(seconds=duration['secs'], microseconds=(duration.get('nanos', 0) or 0) / 1000)).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
                    except (ValueError, TypeError, OverflowError):
                        pass
                call = {'id': key, 'category': 'shell', 'skill': None, 'operation': None, **(spec or {}), 'status': 'running', 'started_at': start, 'ended_at': None,
                        'observer_call_id': key, 'basis': 'native_command_result'}
                calls.append(call)
            if call:
                call['observer_call_id'] = item.get('id')
                if ptype == 'item_completed':
                    status = item.get('status')
                    code = item.get('exit_code')
                    if isinstance(code, int):
                        call.update(status='failed' if code != 0 or status in ('failed', 'cancelled') else 'completed', ended_at=ts)
                        try:
                            result = json.loads(item.get('aggregated_output') or item.get('stdout') or '{}')
                            if isinstance(result, dict) and result.get('ok') is False:
                                call['status'] = 'failed'
                        except (ValueError, TypeError):
                            pass
                    elif status in ('in_progress', 'running') and item.get('process_id') is not None:
                        processes[str(item['process_id'])] = call
                    elif status not in ('in_progress', 'running'):
                        call.update(status='unknown', ended_at=ts)
                    if terminal:
                        call.update(status=terminal, ended_at=ts)
        if kind == 'response_item' and ptype in ('function_call_output', 'custom_tool_call_output'):
            for call in groups.get(payload.get('call_id'), []):
                if call['status'] == 'running' and not any(value is call for value in processes.values()):
                    # A tool return alone does not certify that a subprocess
                    # succeeded, or that a yielded background command ended.
                    call.update(status='unknown' if call['skill'] else 'completed', ended_at=ts)
    # Internal command text exists only above. None is returned or persisted.
    return calls[-64:]
