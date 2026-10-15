"""Judge bundle setup and passive observation; no model/account/permission setup."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def checked(root=ROOT):
    root = root.resolve(strict=True)
    record = json.loads((root / 'bundle-manifest.json').read_text(encoding='utf-8'))
    if record.get('format') != 'lgax-judge-bundle-v1':
        raise ValueError('Unsupported bundle manifest')
    seen = set()
    for row in record['files']:
        name = row['path']; p = PurePosixPath(name)
        if (not isinstance(name, str) or '\\' in name or ':' in name or p.is_absolute()
                or '..' in p.parts or p.as_posix() != name or name in seen):
            raise ValueError('Invalid or duplicate bundle path')
        seen.add(name); path = root / name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError('Outside bundle file')
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Changed/missing release file: ' + name)
    return record

def run(argv, folder):
    result = subprocess.run(argv, cwd=folder, check=False)
    if result.returncode:
        raise RuntimeError('Command exited ' + str(result.returncode) + ': ' + str(argv))

def observe_command(engine, folder, latest=False):
    office = folder / 'web/prototypes/agent-office/office.py'
    if engine == 'claude':
        return [sys.executable, str(office), 'watch', '--claude', str(folder)]
    # A completed historical turn must not stop observation before a followup.
    command = [sys.executable, str(office), 'codex', '--harness', str(folder)]
    return command + (['--latest'] if latest else ['--wait', '--until-complete'])

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('check', 'setup', 'observe', 'paths'))
    p.add_argument('--engine', choices=('codex', 'claude'), default='codex')
    p.add_argument('--latest', action='store_true', help='Observe the existing current Codex session instead of waiting for a new one')
    a = p.parse_args(); record = checked(); folder = ROOT / a.engine
    if a.command == 'check':
        print(json.dumps({'ok': True, 'release': record['release'], 'checked_files': len(record['files'])}, ensure_ascii=False))
        return 0
    if a.command == 'setup':
        uv = shutil.which('uv')
        if not uv:
            raise RuntimeError('Install uv first: https://docs.astral.sh/uv/getting-started/installation/')
        run([uv, 'sync', '--locked', '--python', '3.12'], folder)
        python = folder / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        run([str(python), 'product-doctor.py', '--local-only'] if a.engine == 'codex'
            else [str(python), 'product-doctor.py'], folder)
        run([str(python), 'web/prototypes/visual-viewer/viewer.py', 'install', '--' + a.engine, '.'], folder)
        if a.engine == 'claude':
            run([str(python), 'web/prototypes/agent-office/office.py', 'install', '--claude', '.'], folder)
        print('준비 완료: ' + str(folder))
        print('본인 실행기 로그인·폴더 신뢰·정상 권한/훅 승인은 README 절차로 확인하세요.')
        return 0
    if a.command == 'observe':
        run(observe_command(a.engine, folder, a.latest), folder)
        return 0
    for name in ('visual-viewer', 'agent-office'):
        print(str(folder / 'runtime-data' / name / 'index.html'))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
