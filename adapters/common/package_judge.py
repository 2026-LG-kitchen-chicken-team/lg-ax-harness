"""Prepare one judge-only ZIP with two isolated native runtime folders."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {'.git', '.harness', '.venv', 'node_modules', '__pycache__', 'runtime-data',
             'evals', 'tests', 'dev-harness', 'adapters', 'auth.json', 'settings.local.json'}
LAUNCHERS = tuple(f'start_{engine}_{ui}.{ext}' for engine in ('claude', 'codex') for ui in ('gui', 'cli')
                  for ext in ('cmd', 'sh'))
# Each runtime folder must carry the observer and its pages: the run dashboard (factory) opens at the first question.
OBSERVER_FILES = tuple('web/prototypes/agent-office/' + name for name in
                       ('office.py', 'observe.py', 'codex_follow.py', 'factory.html', 'index.html'))

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def safe_name(name):
    p = PurePosixPath(name)
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name or p.is_absolute()
            or any(x in FORBIDDEN or x in ('..', '.') or x.startswith('.env') for x in p.parts)
            or p.as_posix() != name):
        raise ValueError('Forbidden judge archive path: ' + str(name))
    return p

def build(staging, archive, version, source_commit, root=ROOT):
    root = root.resolve(strict=True)
    staging, archive = Path(staging).resolve(), Path(archive).resolve()
    if (staging.exists() or archive.exists() or staging.is_relative_to(root)
            or root.is_relative_to(staging) or archive.is_relative_to(root)
            or archive.is_relative_to(staging)):
        raise ValueError('Use new staging and ZIP paths outside source and each other')
    if not re.fullmatch(r'product-v\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?', version):
        raise ValueError('Explicit product release version required')
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit):
        raise ValueError('Exact source commit required')
    # Validate all source assets before creating a partial staging tree.
    codex = load(root / 'adapters/codex/install.py', 'judge_codex')
    codex.source_files(root)
    portable = load(root / 'adapters/common/install.py', 'judge_portable')
    files, engines = {}, {}
    for engine in ('codex', 'claude'):
        target = staging / engine
        codex.install(target, root=root) if engine == 'codex' else portable.install(target, engine, root=root)
        record = json.loads((target / 'product-install.json').read_text(encoding='utf-8'))
        expected = {e['path']: e['sha256'] for e in record['files']}
        if len(expected) != len(record['files']):
            raise ValueError('Duplicate installation entries')
        missing = [name for name in OBSERVER_FILES if name not in expected]
        if missing:
            raise ValueError('Run dashboard/observer file missing from ' + engine + ' install: ' + ', '.join(missing))
        for relative, sha in expected.items():
            name = engine + '/' + relative
            safe_name(name)
            path = target / relative
            if path.is_symlink() or not path.resolve(strict=True).is_relative_to(target.resolve()):
                raise ValueError('Outside installed file')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError('Installed source changed: ' + name)
            files[name] = raw
        files[engine + '/product-install.json'] = (target / 'product-install.json').read_bytes()
        engines[engine] = {'files': len(expected) + 1, 'skills': record['skills'],
                           'native_agents': record['native_agents'],
                           'source_manifest_sha256': record['source_manifest_sha256']}
    files['README.md'] = (root / 'docs/contracts/judge-test.md').read_bytes()
    files['judge.py'] = (root / 'adapters/common/judge.py').read_bytes()
    # One-click starts at the ZIP root: .cmd for a Windows double-click, .sh (executable) for macOS/Linux.
    for name in LAUNCHERS:
        files[name] = (root / 'adapters/common/launchers' / name).read_bytes()
    manifest = {'format': 'lgax-judge-bundle-v1', 'release': version, 'source_commit': source_commit,
        'engines': engines, 'default_catalog': 'empty',
        'purpose': 'Judge installation and user testing; same business Agent/Skills in isolated native workspaces',
        'excluded': 'development harness/roles/evaluation/private source corpora/runtime/auth/dependency caches/front-end build tools',
        'files': [{'path': n, 'sha256': hashlib.sha256(raw).hexdigest()} for n, raw in sorted(files.items())]}
    files['bundle-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, raw in sorted(files.items()):
            safe_name(name)
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.create_system = 3  # Unix interpretation of the regular-file type and permission bits below.
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            output.writestr(entry, raw)
    return {'archive': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'files': len(files), 'release': version, 'engines': engines}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--source-commit', required=True)
    a = parser.parse_args()
    print(json.dumps(build(a.staging, a.archive, a.version, a.source_commit), ensure_ascii=False))

if __name__ == '__main__':
    main()
