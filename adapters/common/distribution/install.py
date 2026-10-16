"""Install the released judge ZIP without cloning the development repository (Python 3.12+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

DEFAULT_REPO = '2026-LG-kitchen-chicken-team/lg-ax-agent'
DEFAULT_VERSION = 'product-v0.16.3'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXTRACTED = 256 * 1024 * 1024


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_source(repo, version):
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', repo) or repo.split('/')[1] in ('.', '..'):
        raise ValueError('Use a GitHub owner/repository name.')
    if not re.fullmatch(r'product-v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?', version):
        raise ValueError('Use an exact product release, for example product-v0.16.3.')


def download_public(url, target, maximum):
    request = urllib.request.Request(url, headers={'User-Agent': 'LG-AX-installer/1'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target.open('xb') as output:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > maximum:
                    raise ValueError('Download exceeds the allowed size.')
                output.write(block)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Public download HTTP {exc.code}. Private releases require --transport gh and repository access.') from None
    except urllib.error.URLError:
        raise RuntimeError('Download connection failed; check the network and retry in a new folder.') from None


def download_release(repo, version, transport, cache):
    archive_name = f'lg-ax-judge-{version}.zip'
    names = (archive_name, 'SHA256SUMS.txt')
    if transport == 'gh':
        gh = shutil.which('gh')
        if not gh:
            raise RuntimeError('Install GitHub CLI and run gh auth login. This private release requires read access.')
        result = subprocess.run([gh, 'release', 'download', version, '--repo', repo,
                                 '--pattern', archive_name, '--pattern', 'SHA256SUMS.txt', '--dir', str(cache)],
                                capture_output=True, timeout=180)
        if result.returncode:
            raise RuntimeError('Authenticated download failed. Check gh auth status, repository access and the exact release version.')
    else:
        for name in names:
            download_public(f'https://github.com/{repo}/releases/download/{version}/{name}',
                            cache / name, MAX_ARCHIVE if name.endswith('.zip') else 256 * 1024)
    for name in names:
        path = cache / name
        if not path.is_file() or path.stat().st_size > (MAX_ARCHIVE if name.endswith('.zip') else 256 * 1024):
            raise ValueError('Missing or oversized release asset: ' + name)
    return cache / archive_name, cache / 'SHA256SUMS.txt'


def verify_checksum(archive, checksums):
    matches = []
    for line in checksums.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)', line.strip())
        if match and match[2] == archive.name:
            matches.append(match[1].lower())
    if len(matches) != 1 or digest(archive) != matches[0]:
        raise ValueError('Release SHA256 mismatch or missing/duplicate checksum; nothing was installed.')


def safe_name(name):
    path = PurePosixPath(name)
    if not name or not path.parts or '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or path.as_posix() != name:
        raise ValueError('Unsafe archive path: ' + name)
    for part in path.parts:
        if (part.endswith((' ', '.')) or any(ord(c) < 32 for c in part)
                or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part, re.I)):
            raise ValueError('Unsupported archive path: ' + name)
    return path


def unpack_verified(archive, folder, version):
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos) > 5000 or sum(i.file_size for i in infos) > MAX_EXTRACTED:
            raise ValueError('Archive exceeds extraction limits.')
        seen = set()
        for entry in infos:
            safe_name(entry.filename)
            key = entry.filename.casefold()
            if key in seen or entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Duplicate, directory or symbolic-link archive member.')
            seen.add(key)
        record = json.loads(z.read('bundle-manifest.json'))
        if record.get('format') != 'lgax-judge-bundle-v1' or record.get('release') != version:
            raise ValueError('Bundle release/version mismatch.')
        expected = {}
        for item in record['files']:
            name = item['path']; safe_name(name)
            if name in expected or not re.fullmatch(r'[a-f0-9]{64}', item['sha256']):
                raise ValueError('Invalid bundle manifest entry.')
            expected[name] = item['sha256']
        names = {i.filename for i in infos}
        if names != set(expected) | {'bundle-manifest.json'} or not {'README.md', 'judge.py'} <= names:
            raise ValueError('Archive members do not match the bundle manifest.')
        for entry in infos:
            raw = z.read(entry)
            if entry.filename in expected and hashlib.sha256(raw).hexdigest() != expected[entry.filename]:
                raise ValueError('Bundle file SHA256 mismatch: ' + entry.filename)
            target = folder / entry.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            target.chmod(0o755 if entry.filename.endswith('.sh') else 0o644)
    return len(infos)


def install(repo, version, transport, target, engine, download_only=False):
    validate_source(repo, version)
    target = Path(target).expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ValueError('Target already exists. Use a NEW folder; previous results are never overwritten: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.parent.resolve() / target.name
    with tempfile.TemporaryDirectory(prefix='.lgax-download-', dir=target.parent) as name:
        staging = Path(name)
        archive, checksums = download_release(repo, version, transport, staging)
        verify_checksum(archive, checksums)
        unpacked = staging / 'bundle'; unpacked.mkdir()
        files = unpack_verified(archive, unpacked, version)
        # mkdir is exclusive even when another installation races us; never replace a folder.
        target.mkdir()
        for item in unpacked.iterdir():
            shutil.move(str(item), str(target / item.name))
    result = {'release': version, 'repository': repo, 'transport': transport,
              'target': str(target), 'engine': engine, 'verified_files': files, 'prepared': False}
    if not download_only:
        uv = shutil.which('uv')
        if not uv:
            raise RuntimeError('ZIP verified and extracted. Install uv, then run a start file in: ' + str(target))
        code = subprocess.run([uv, 'run', '--no-project', '--python', '3.12', 'python', 'judge.py',
                               'setup', '--engine', engine], cwd=target).returncode
        if code:
            raise RuntimeError('Preparation failed. Keep the extracted folder and rerun its start file: ' + str(target))
        result['prepared'] = True
    print(json.dumps(result, ensure_ascii=False))
    print('Open README.md, then run start_' + engine + '_cli' + ('.cmd' if os.name == 'nt' else '.sh')
          + ' (or the GUI start file on Windows/macOS). Login and workspace approvals remain yours.')
    return result


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=DEFAULT_REPO)
    parser.add_argument('--version', default=DEFAULT_VERSION)
    parser.add_argument('--engine', choices=('codex', 'claude'), default='codex')
    parser.add_argument('--transport', choices=('gh', 'public'), default='gh')
    parser.add_argument('--target', type=Path)
    parser.add_argument('--download-only', action='store_true', help='Verify/extract only; do not prepare the Python environment.')
    args = parser.parse_args()
    target = args.target or Path.cwd() / ('LG-AX-' + args.version + '-' + args.engine)
    install(args.repo, args.version, args.transport, target, args.engine, args.download_only)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print('Installation stopped: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
