"""Judge bundle setup, one-click start and passive observation; no model/account/permission setup."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
SETUP_MARK = ('runtime-data', 'judge-setup.json')
GUIDE = {'claude': 'https://code.claude.com/docs/en/setup', 'codex': 'https://learn.chatgpt.com/docs/codex/cli',
         'desktop': 'https://code.claude.com/docs/en/desktop-quickstart'}
# The official native installer (code.claude.com/docs/en/setup); it runs only after the user answers y.
CLAUDE_INSTALL = (['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', 'irm https://claude.ai/install.ps1 | iex']
                  if os.name == 'nt' else ['bash', '-c', 'curl -fsSL https://claude.ai/install.sh | bash'])
DESKTOP_MIN = (2, 1, 285)  # `claude --desktop` opens Claude Desktop on the current folder (macOS, x64 Windows)
# The run dashboard (factory control room) beside the observer's records; the 3D office page stays next to it.
DASHBOARD = ('runtime-data', 'agent-office', 'factory.html')

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

def run_observer(argv, folder):
    if os.name == 'posix':
        # The launcher's $! must become the actual follower PID so its EXIT trap can stop it.
        os.chdir(folder)
        return os.execv(argv[0], argv)
    run(argv, folder)

def observe_command(engine, folder, latest=False, keep=False, open_page=False):
    command = [sys.executable, str(folder / 'web/prototypes/visual-viewer/watch.py'),
               'watch', '--harness', str(folder), '--engine', engine]
    if latest:
        command.append('--latest')
    if keep:
        command.append('--keep-following')
    return command + (['--open'] if open_page else [])


def runtime_path(folder, relative):
    """A launcher writes only its own guarded runtime files, never a linked directory."""
    folder = folder.resolve(strict=True)
    path = folder / relative
    current = folder
    for part in path.relative_to(folder).parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked runtime path is not supported')
    if not current.resolve().is_relative_to(folder):
        raise ValueError('Runtime path escapes the product folder')
    return path


def stop_observer(child, folder, token):
    if child.poll() is not None:
        return
    stop = runtime_path(folder, 'runtime-data/visual-viewer/.watch-stop-' + token)
    stop.parent.mkdir(parents=True, exist_ok=True)
    stop.write_text('stop\n', encoding='utf-8')
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        # Only this launcher's child, never the GUI app or an unrelated observer.
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=3)


def observer_started(value, engine, token):
    # Windows venv python.exe may be a waiting redirector with a different PID.
    # Correlate this launch by its random token; pid remains diagnostic metadata.
    return (isinstance(value, dict) and value.get('observer_token') == token
            and value.get('engine') == engine and value.get('observer_ready') is True)


def start_observer(engine, folder):
    token = uuid.uuid4().hex
    log = runtime_path(folder, 'runtime-data/visual-viewer/observer-supervisor.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    stream = log.open('a', encoding='utf-8')
    child = None
    try:
        command = observe_command(engine, folder, keep=True, open_page=True)
        command += ['--parent-pid', str(os.getpid()), '--stop-token', token]
        child = subprocess.Popen(command, cwd=folder, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        # Establish the old-export baseline before a fast native command can write a result.
        status = runtime_path(folder, 'runtime-data/visual-viewer/watch-status.json')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('결과 관찰을 시작하지 못했습니다. 다른 관찰 창과 진단 로그를 확인하세요.')
            try:
                value = json.loads(status.read_text(encoding='utf-8'))
                if observer_started(value, engine, token):
                    return child, stream, token
            except (OSError, ValueError, AttributeError):
                pass
            time.sleep(0.05)
        raise RuntimeError('결과 관찰 시작 확인 시간이 초과되었습니다. 진단 로그를 확인하세요.')
    except BaseException:
        if child is not None:
            stop_observer(child, folder, token)
        stream.close()
        raise


def native_cli_command(engine):
    exe = find_cli(engine)
    if not exe:
        raise RuntimeError('실행기 CLI를 찾지 못했습니다: ' + engine)
    if engine == 'claude':
        return [exe, '--model', 'claude-opus-5-5', '--effort', 'medium']
    command = [exe, '--search', '--sandbox', 'workspace-write', '--ask-for-approval', 'on-request']
    if os.name == 'nt':
        command += ['--config', 'windows.sandbox=mxc']
    return command + ['--model', 'gpt-6.1-sol', '--config', 'model_reasoning_effort=medium']


def launch(engine, ui, folder):
    child, stream, token = start_observer(engine, folder)
    try:
        print('실행 대시보드와 결과 파일 관찰을 시작했습니다. 열기는 OS 요청이며 화면 표시는 별도 확인하세요.', flush=True)
        if ui == 'cli':
            return subprocess.run(native_cli_command(engine), cwd=folder, check=False).returncode
        if engine == 'claude':
            code = desktop(folder)
        else:
            exe = find_cli('codex')
            if not exe:
                raise RuntimeError('Codex CLI를 찾지 못했습니다.')
            code = subprocess.run([exe, 'app', str(folder)], cwd=folder, check=False).returncode
        if code:
            return code
        print('GUI 관찰 창을 유지합니다 (최대 3시간). 관찰을 끝내려면 Ctrl+C 또는 이 창을 닫으세요. 앱은 계속 열려 있습니다.', flush=True)
        # GUI app/open commands can return immediately; their return is not GUI session completion.
        return child.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        stop_observer(child, folder, token)
        stream.close()

def venv_python(folder):
    return folder / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')

def setup(engine, folder, release):
    uv = shutil.which('uv')
    if not uv:
        raise RuntimeError('Install uv first: https://docs.astral.sh/uv/getting-started/installation/')
    run([uv, 'sync', '--locked', '--python', '3.12'], folder)
    python = venv_python(folder)
    run([str(python), 'product-doctor.py', '--local-only'] if engine == 'codex'
        else [str(python), 'product-doctor.py'], folder)
    run([str(python), 'web/prototypes/visual-viewer/viewer.py', 'install', '--' + engine, '.'], folder)
    if engine == 'claude':
        # The first question of each session opens the run dashboard (factory page) once.
        run([str(python), 'web/prototypes/agent-office/office.py', 'install', '--claude', '.', '--open-on-prompt', '--page', 'factory'], folder)
    mark = folder.joinpath(*SETUP_MARK)
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(json.dumps({'release': release, 'engine': engine}) + '\n', encoding='utf-8')

def is_set_up(engine, folder, release):
    try:
        mark = json.loads(folder.joinpath(*SETUP_MARK).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return mark == {'release': release, 'engine': engine} and venv_python(folder).is_file()

def find_cli(name):
    """PATH first, then the native installer's folder (a fresh install is not on this window's PATH yet)."""
    found = shutil.which(name)
    local = Path.home() / '.local' / 'bin' / (name + ('.exe' if os.name == 'nt' else ''))
    return found or (str(local) if local.is_file() else None)

def quiet(argv, timeout=60, env=None, cwd=None):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout,
                             env=env, cwd=cwd)
        return out.returncode, out.stdout + out.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)

def version_of(exe):
    code, out = quiet([exe, '--version'])
    found = re.search(r'(\d+)\.(\d+)\.(\d+)', out) if code == 0 else None
    return tuple(map(int, found.groups())) if found else None

def signed_in(exe, engine):
    # Exit codes only: `claude auth status` / `codex login status` are 0 when signed in. Their output is not kept.
    return quiet([exe, 'auth', 'status'] if engine == 'claude' else [exe, 'login', 'status'])[0] == 0

def ask(question):
    try:
        return input(question + ' [y/N] ').strip().lower() in ('y', 'yes')
    except EOFError:
        return False

def prepare(engine, ui, release):
    """What a double-click start does before the runner opens: setup once, the runner CLI, the product doctor."""
    folder = ROOT / engine
    if is_set_up(engine, folder, release):
        print('설치 확인: ' + str(folder))
    else:
        print('처음 한 번 준비합니다: 의존성·결과 웹 훅' + (' ·실행 대시보드 훅' if engine == 'claude' else '') + ' 설치 (1~2분)', flush=True)
        setup(engine, folder, release)
    exe = find_cli(engine)
    if engine == 'claude' and ui == 'cli' and not exe:
        print('Claude Code CLI가 없습니다. 공식 설치 명령: ' + CLAUDE_INSTALL[-1])
        if ask('지금 이 공식 설치 명령을 실행할까요?'):
            run(CLAUDE_INSTALL, folder)
            exe = find_cli('claude')
        if not exe:
            raise RuntimeError('Claude Code CLI를 설치한 뒤 다시 실행하세요: ' + GUIDE['claude'])
    if engine == 'codex':
        if not exe:
            raise RuntimeError('Codex CLI가 없습니다. 설치한 뒤 다시 실행하세요: ' + GUIDE['codex'])
        if not signed_in(exe, 'codex'):
            print('Codex에 로그인되어 있지 않습니다. 본인 계정으로 로그인을 진행합니다.', flush=True)
            run([exe, 'login'], folder)
        doctor = [str(venv_python(folder)), 'product-doctor.py']
        if os.name == 'nt' and ui == 'cli':
            doctor.append('--check-sandbox')  # the CLI start uses windows.sandbox=mxc, as in the README's Windows check
        print('product-doctor 점검 중...', flush=True)
        code, out = quiet(doctor, timeout=300, cwd=folder)
        try:
            errors = json.loads(out.strip().splitlines()[-1]).get('errors')
        except (ValueError, AttributeError, IndexError):
            errors = None
        if code != 0:
            raise RuntimeError('product-doctor 점검 실패: ' + json.dumps(errors or out[-500:], ensure_ascii=False)
                               + '\ncodex/docs/contracts/runtime-access.md의 진단 절차를 따르세요.')
        print('product-doctor 점검 통과' + (' (Windows 샌드박스 포함)' if '--check-sandbox' in doctor else ''))
    elif exe and ui == 'cli' and not signed_in(exe, 'claude'):
        print('Claude Code CLI 로그인 전입니다. 곧 열리는 화면의 안내대로 본인 계정으로 로그인하세요 '
              '(Pro·Max·Team·Enterprise 또는 Console 계정).')
    office = folder.joinpath(*DASHBOARD)
    viewer = folder / 'runtime-data' / 'visual-viewer' / 'index.html'
    print('실행 대시보드(공장 관제): ' + ('첫 질문을 보내면' if engine == 'claude' else '관찰 창이 새 Codex 세션을 찾으면')
          + ' 브라우저에 자동으로 열립니다 -> ' + str(office))
    print('결과 웹(결과 저장 후 갱신): ' + str(viewer))
    return 0

def start_app():
    """Best effort: start Claude Desktop through its own registered claude:// link; never installs or signs in."""
    try:
        if os.name == 'nt':
            import winreg
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'claude'))
            os.startfile('claude://')
            return True
        if sys.platform == 'darwin':
            return subprocess.run(['open', '-a', 'Claude'], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        pass
    return False

def copy_text(text):
    if os.name == 'nt':  # Set-Clipboard reads the value from the environment, so a Korean path stays intact
        argv = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', 'Set-Clipboard -Value $env:LGAX_COPY']
    elif sys.platform == 'darwin':
        argv = ['bash', '-c', 'printf %s "$LGAX_COPY" | pbcopy']
    else:
        return False
    return quiet(argv, env=dict(os.environ, LGAX_COPY=text))[0] == 0

def desktop(folder):
    """Claude Desktop on the claude folder: `claude --desktop` when the CLI can, otherwise the app and exact steps."""
    exe = find_cli('claude')
    supported = sys.platform == 'darwin' or (os.name == 'nt' and platform.machine().lower() in ('amd64', 'x86_64'))
    if exe and supported and (version_of(exe) or (0,)) >= DESKTOP_MIN and signed_in(exe, 'claude'):
        if subprocess.run([exe, '--desktop'], cwd=folder, check=False).returncode == 0:
            print('Claude Desktop에서 이 폴더로 Code 세션을 열었습니다: ' + str(folder))
            print('앱에서 모델 Opus 5.5 · 추론 중간과 폴더 신뢰를 확인한 뒤 질문하세요.')
            return 0
        print('claude --desktop이 열지 못해 직접 여는 방법으로 안내합니다.')
    opened = start_app()
    copied = copy_text(str(folder))
    print('Claude Desktop을 ' + ('열었습니다.' if opened else '직접 여세요. 설치 안내: ' + GUIDE['desktop']))
    print('1. 유료 Code 사용 가능 계정으로 로그인 -> 왼쪽 Code -> Local')
    print('2. 작업 폴더로 아래 폴더를 고릅니다' + (' (경로를 클립보드에 복사했습니다)' if copied else '') + ':')
    print('   ' + str(folder))
    print('3. 모델 Opus 5.5 · 추론 중간 확인 -> 새 세션에서 질문. ZIP 루트 폴더로 열면 훅이 동작하지 않습니다.')
    return 0

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('check', 'setup', 'observe', 'paths', 'prepare', 'desktop', 'launch'))
    p.add_argument('--engine', choices=('codex', 'claude'), default='codex')
    p.add_argument('--latest', action='store_true', help='Observe the existing current Codex session instead of waiting for a new one')
    p.add_argument('--keep-following', action='store_true', help='Codex: follow the new session through followups until stopped')
    p.add_argument('--open', action='store_true', help='Codex: open the dashboard once the new session is recorded')
    p.add_argument('--ui', choices=('cli', 'gui'), default='cli', help='prepare: the runner the one-click start opens next')
    a = p.parse_args(); record = checked(); folder = ROOT / a.engine
    if a.command == 'check':
        print(json.dumps({'ok': True, 'release': record['release'], 'checked_files': len(record['files'])}, ensure_ascii=False))
        return 0
    if a.command == 'setup':
        setup(a.engine, folder, record['release'])
        print('준비 완료: ' + str(folder))
        print('본인 실행기 로그인·폴더 신뢰·정상 권한/훅 승인은 README 절차로 확인하세요.')
        return 0
    if a.command == 'prepare':
        return prepare(a.engine, a.ui, record['release'])
    if a.command == 'desktop':
        if a.engine != 'claude':
            raise ValueError('desktop is for --engine claude; Codex uses: codex app codex')
        return desktop(folder)
    if a.command == 'launch':
        return launch(a.engine, a.ui, folder)
    if a.command == 'observe':
        run_observer(observe_command(a.engine, folder, a.latest, a.keep_following, a.open), folder)
        return 0
    for path in (folder / 'runtime-data' / 'visual-viewer' / 'index.html', folder.joinpath(*DASHBOARD),
                 folder / 'runtime-data' / 'agent-office' / 'index.html'):
        print(str(path))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
