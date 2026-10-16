"""시각자료 뷰어 설치·해제·열기 (Claude Code·Codex CLI 공용, 표준 라이브러리만 사용).

    uv run python web/prototypes/visual-viewer/viewer.py install --claude <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py install --codex <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py uninstall --claude|--codex|--both <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py open --latest [<하네스 폴더>]
    uv run python web/prototypes/visual-viewer/viewer.py status [<하네스 폴더>]
    uv run python web/prototypes/visual-viewer/viewer.py selftest [--claude|--codex] [<하네스 폴더>]

- install: 뷰어 파일을 `<하네스>/web/prototypes/visual-viewer/`에 복사하고(이미 그 자리면 생략), 훅을
  `.claude/settings.local.json` 또는 `.codex/hooks.json`에 합친다. 기존 설정·다른 훅은 지우거나 옮기지 않는다.
  훅 명령에는 사용자별 절대 경로가 없고, 설치한 hook.py·build_view.py·index.html의 SHA-256이 들어간다.
  그래서 파일이 바뀌면 훅이 실행하지 않고(로그만 남김), Codex에서는 명령이 바뀌어 다시 신뢰해야 한다.
  공유 파일이 바뀌면 이미 등록된 다른 CLI의 항목도 같은 지문으로 다시 맞춘다.
- uninstall: 이 뷰어의 훅 항목만 지운다. 뷰어 파일과 runtime-data의 화면·insights는 남긴다.
- open --latest: 가장 최근 export로 화면을 다시 만들고 브라우저로 연다(훅이 없거나 놓쳤을 때).
- 업무·모델·Tool을 실행하지 않는다. 개발 레포(dev-harness 폴더가 있는 곳)에는 설치하지 않는다.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_view  # noqa: E402
import hook  # noqa: E402

APP_REL = ("web", "prototypes", "visual-viewer")
APP_FILES = ("index.html", "build_view.py", "hook.py", "viewer.py", "delivery.py", "watch.py", "README.md")
# uv: 작업 폴더의 .python-version·uv.toml·pyproject를 따르지 않고 3.12를 쓰며 Python을 내려받지 않는다.
UV_PREFIX = "uv run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c"
# Python 코드 부분은 Git Bash·PowerShell·cmd 어디서나 같게 해석되도록 $ % ! ` \ ^ & | < > 를 쓰지 않는다.
# hook.py의 SHA-256이 맞을 때만 읽은 바이트 그대로 실행한다. 없거나 다르면 실행하지 않고 로그에 한 줄 남긴다.
_BASE = {"claude": "os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()", "codex": "os.getcwd()"}
_GUARD_RELATIVES = (
    "web/prototypes/visual-viewer/hook.py", "web/prototypes/visual-viewer/build_view.py",
    "web/prototypes/visual-viewer/index.html", ".codex", ".claude", "runtime-data/exports",
    "runtime-data/visual-viewer/index.html", "runtime-data/visual-viewer/view-data.js",
    "runtime-data/visual-viewer/.hook-state.json", "runtime-data/visual-viewer/.hook.lock",
    "runtime-data/visual-viewer/.hook-last-export", "runtime-data/visual-viewer/hook-error.log",
    "runtime-data/visual-viewer/hook-start-error.log",
)
_GUARD_PARTS = repr(tuple(tuple(p.split("/")) for p in _GUARD_RELATIVES))
_PATH_GUARD_CODE = ("g=[os.path.join(d,*p[:n]) for p in " + _GUARD_PARTS + " for n in range(1,len(p)+1)];"
                    "good=not any(stat.S_ISLNK(os.lstat(p).st_mode) or "
                    "getattr(os.lstat(p),'st_file_attributes',0).__and__(1024) for p in g if os.path.lexists(p));")
_CODE = ("import hashlib,os,time,stat;d={base};" + _PATH_GUARD_CODE +
         "p=os.path.join(d,'web','prototypes','visual-viewer','hook.py');"
         "l=os.path.join(d,'runtime-data','visual-viewer','hook-error.log');"
         "b=open(p,'rb').read() if good and os.path.isfile(p) else b'';"
         "exec(compile(b,p,'exec'),{{'__name__':'__main__','__file__':p}}) if good and hashlib.sha256(b).hexdigest()=='{digest}' "
         "else good and os.path.isdir(os.path.dirname(l)) and open(l,'a').write("
         "time.ctime()+' hook.py is missing or differs from the installed fingerprint. Run viewer.py install again.'+chr(10))")
LOG_POSIX = "runtime-data/visual-viewer"
START_LOG = "hook-start-error.log"  # Codex 셸이 쓰는 uv·Python 시작 오류(마지막 실행분만)
# Codex는 Windows에서 commandWindows를 버전·설정에 따라 cmd(`COMSPEC /C "<명령>"`, 0.146) 또는 사용자 셸인 PowerShell
# (`powershell.exe|pwsh.exe -NoProfile -Command <명령>`, 0.162)로 실행한다. 두 셸에서 똑같이 해석되는 명령은
# "상대 경로 실행 파일 + 16진수 인자"뿐이라, 셸 문법이 필요한 일은 하네스 `.codex\`의 실행기(.cmd)가 한다.
# `.codex\`는 Codex 샌드박스가 쓰기를 막는 폴더다. 실행기가 하는 일:
# - 작업 폴더 실행 파일 검색 끄기, 출력 버리기, 시작 오류 기록, 항상 exit 0
# - 빠른 길: 가장 최근 export 이름이 hook.py가 마지막으로 처리한 이름(.hook-last-export)과 같으면 Python 없이 끝낸다.
#   비교는 지연 확장으로 해서 샌드박스가 쓸 수 있는 파일 내용이 명령으로 해석되지 않는다. 다르거나 모르면 Python으로 넘어간다.
# - 인터프리터: 샌드박스가 쓸 수 없는 %SystemRoot%\System32에서 `uv python find --system`으로 가상 환경이 아닌 Python 3.12를
#   찾아 직접 `-I -B`로 실행한다. 하네스 .venv·.python-version·.pth는 쓰이지 않는다. 하네스 경로는 인자로 넘긴다.
LAUNCHER_REL = (".codex", "visual-viewer-hook.cmd")
MARKER = ".hook-last-export"
FIND_PYTHON = "uv python find --system --no-config --no-python-downloads 3.12"
_LAUNCHER_CODE = ("import hashlib,os,sys,time,stat;d=os.path.abspath(sys.argv.pop(2));h=sys.argv.pop(2);" + _PATH_GUARD_CODE +
                  "p=os.path.join(d,'web','prototypes','visual-viewer','hook.py');"
                  "l=os.path.join(d,'runtime-data','visual-viewer','hook-error.log');"
                  "b=open(p,'rb').read() if good and os.path.isfile(p) else b'';"
                  "exec(compile(b,p,'exec'),{'__name__':'__main__','__file__':p}) if good and hashlib.sha256(b).hexdigest()==h "
                  "else good and os.path.isdir(os.path.dirname(l)) and open(l,'a').write("
                  "time.ctime()+' hook.py is missing or differs from the installed fingerprint. Run viewer.py install again.'+chr(10))")
LAUNCHER_PATH_GUARD = (
    "$ErrorActionPreference='Stop';try{$r=[IO.Path]::GetFullPath($env:H);"
    "$rels=@(" + ",".join("'" + r + "'" for r in _GUARD_RELATIVES) + ");"
    "foreach($rel in $rels){$p=$r;foreach($part in $rel.Split('/')){$p=[IO.Path]::Combine($p,$part);"
    "try{$a=[IO.File]::GetAttributes($p)}catch [IO.FileNotFoundException]{continue}"
    "catch [IO.DirectoryNotFoundException]{continue};"
    "if($a -band [IO.FileAttributes]::ReparsePoint){exit 1}}};"
    "foreach($rel in @('runtime-data/exports','runtime-data/visual-viewer')){"
    "$p=[IO.Path]::Combine($r,$rel);if([IO.Directory]::Exists($p)){"
    "foreach($e in (Get-ChildItem -LiteralPath $p -Force)){if($e.Attributes -band [IO.FileAttributes]::ReparsePoint){exit 1}}}};"
    "exit 0}catch{exit 1}"
)
_WINDOWS_PYTHON_CODE = ("import hashlib,os,sys,time;d=os.path.abspath(sys.argv.pop(2));h=sys.argv.pop(2);p=os.path.join(d,'web','prototypes','visual-viewer','hook.py');"
                "l=os.path.join(d,'runtime-data','visual-viewer','hook-error.log');b=open(p,'rb').read() if os.path.isfile(p) else b'';"
                "exec(compile(b,p,'exec'),{'__name__':'__main__','__file__':p}) if hashlib.sha256(b).hexdigest()==h else os.path.isdir(os.path.dirname(l)) and open(l,'a').write('hook.py is missing or differs'+chr(10))")


def windows_runner(source, digests=None):
    """UTF-8 process capture; no cmd for/f decoding of interpreter paths."""
    guard = (
        "function G($r){try{foreach($x in @('web','web/prototypes','web/prototypes/visual-viewer','.codex','.claude','runtime-data','runtime-data/exports','runtime-data/visual-viewer')){"
        "$p=[IO.Path]::Combine($r,$x);try{$a=[IO.File]::GetAttributes($p)}catch [IO.FileNotFoundException]{continue}catch [IO.DirectoryNotFoundException]{continue};if($a -band 1024){return $false}};"
        "foreach($x in @('web/prototypes/visual-viewer','runtime-data/exports','runtime-data/visual-viewer')){$p=[IO.Path]::Combine($r,$x);if([IO.Directory]::Exists($p)){foreach($e in (Get-ChildItem -LiteralPath $p -Force)){if($e.Attributes -band 1024){return $false}}}};return $true}catch{return $false}};"
    )
    runner = (
        "function P($f,$a,$d,[byte[]]$b){$i=[Diagnostics.ProcessStartInfo]::new();$i.FileName=$f;$i.Arguments=$a;$i.WorkingDirectory=$d;$i.UseShellExecute=$false;$i.CreateNoWindow=$true;"
        "$i.RedirectStandardOutput=$true;$i.RedirectStandardError=$true;$i.StandardOutputEncoding=[Text.Encoding]::UTF8;$i.StandardErrorEncoding=[Text.Encoding]::UTF8;"
        "$i.RedirectStandardInput=$null -ne $b;$p=[Diagnostics.Process]::Start($i);if($null -ne $b){$p.StandardInput.BaseStream.Write($b,0,$b.Length);$p.StandardInput.Close()};"
        "$o=$p.StandardOutput.ReadToEnd();$e=$p.StandardError.ReadToEnd();$p.WaitForExit();return ,@($p.ExitCode,$o,$e)};"
    )
    if source == 'codex':
        root = "$r=$env:H;"
        fast = ("$n=Get-ChildItem -LiteralPath ([IO.Path]::Combine($r,'runtime-data/exports')) -Filter '*.json' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1;"
                "if(-not $n){exit 0};$m=[IO.Path]::Combine($o,'.hook-last-export');if([IO.File]::Exists($m) -and [IO.File]::ReadAllText($m).Trim() -eq $n.Name){exit 0};")
        # PowerShell guards all directories/leaves before loading pinned Python.
        code = _WINDOWS_PYTHON_CODE
        execution = ("$v=P 'uv' 'python find --system --no-config --no-python-downloads 3.12' ($env:SystemRoot+'/System32') $null;"
                     "[IO.File]::WriteAllText($l,$v[2],$u);if($v[0] -ne 0){exit 0};$py=$v[1].Trim();"
                     "$a='-I -B -c '+[char]34+'" + code.replace("'", "''") + "'+[char]34+' codex '+[char]34+$r+'/.'+[char]34+' '+$env:LGAX_HOOK_SHA+' '+$env:LGAX_BUILD_SHA+' '+$env:LGAX_INDEX_SHA;"
                     "$v=P $py $a ($env:SystemRoot+'/System32') $b;if($v[2]){[IO.File]::AppendAllText($l,$v[2],$u)};")
    else:
        root = "$r=$env:CLAUDE_PROJECT_DIR;if(-not $r){$r=(Get-Location).Path};"
        fast = ''
        code = _WINDOWS_PYTHON_CODE
        args = "run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c "
        execution = ("$a='" + args + "'+[char]34+'" + code.replace("'", "''") + "'+[char]34+' claude '+[char]34+$r+'/.'+[char]34+' " + digests['hook'] + " " + digests['build_view'] + " " + digests['index'] + "';"
                     "$v=P 'uv' $a $r $b;[IO.File]::WriteAllText($l,$v[2],$u);")
    return ("# LG_AX_VISUAL_VIEWER_V1\n$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';" + guard + runner + "try{" + root +
            "if(-not (G $r)){exit 0};$o=[IO.Path]::Combine($r,'runtime-data/visual-viewer');" + fast +
            "[void][IO.Directory]::CreateDirectory($o);$l=[IO.Path]::Combine($o,'hook-start-error.log');$u=[Text.UTF8Encoding]::new($false);"
            "$m=[IO.MemoryStream]::new();[Console]::OpenStandardInput().CopyTo($m);$b=$m.ToArray();" + execution +
            "}catch{if($l -and (G $r)){[IO.File]::WriteAllText($l,[string]$_,$u)}};exit 0")


def encoded_windows_runner(source, digests=None):
    return base64.b64encode(windows_runner(source, digests).encode('utf-16le')).decode('ascii')


LAUNCHER_TEXT = "\r\n".join([
    "@echo off",
    "rem LG AX visual viewer - Codex Stop hook launcher written by viewer.py install. Do not edit, reinstall instead.",
    "setlocal EnableExtensions DisableDelayedExpansion",
    "set NoDefaultCurrentDirectoryInExePath=1",
    'cd /d "%~dp0.." || exit /b 0',
    'set "H=%CD%"',
    'set "LGAX_HOOK_SHA=%2"',
    'set "LGAX_BUILD_SHA=%3"',
    'set "LGAX_INDEX_SHA=%4"',
    '"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -NonInteractive -EncodedCommand ' + encoded_windows_runner('codex') + ' 1>nul 2>nul',
    "exit /b 0", "",
])

TARGETS = {
    "claude": {"file": (".claude", "settings.local.json"), "event": "PostToolUse", "matcher": "Bash|PowerShell",
               "name": "Claude Code", "async": True, "timeout": 60, "keep_positions": False},
    # Codex는 답변이 끝날 때 한 번 도는 Stop(동기)에 둔다. 셸 명령마다 도는 PostToolUse의 지연이 없다.
    # Stop은 0.146.0·0.162.1 모두에 있고 matcher를 쓰지 않는다. 0.146은 async 훅을 건너뛰므로 동기로 둔다.
    # 신뢰 키가 `이벤트:묶음 번호:처리기 번호` 위치라서 다른 훅의 위치를 지킨다.
    "codex": {"file": (".codex", "hooks.json"), "event": "Stop", "matcher": None,
              "name": "Codex CLI", "async": False, "timeout": 30, "keep_positions": True},
}
PLACEHOLDER = {"type": "command", "command": ""}  # Codex는 빈 명령을 건너뛰지만 그 자리 번호는 센다
HEX64 = re.compile(r"[0-9a-f]{64}")
# 이 뷰어의 훅을 실제로 확인한 CLI 버전. 다른 버전이면 status가 경고하고 selftest·/hooks 재확인을 안내한다.
TESTED_VERSIONS = {"codex": ("0.162.1",), "claude": ("2.1.289",)}


class ViewerError(Exception):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def app_digests(app: Path) -> dict:
    return {"hook": digest(app / "hook.py"), "build_view": digest(app / "build_view.py"), "index": digest(app / "index.html")}


def hook_code(source: str, digests: dict) -> str:
    return _CODE.format(base=_BASE[source], digest=digests["hook"])


def hook_command(source: str, digests: dict) -> str:
    """Guard first, capture startup output, preserve silent nonblocking hooks."""
    if source == 'claude' and os.name == 'nt':
        powershell = 'powershell.exe'
        return powershell + ' -NoProfile -NonInteractive -EncodedCommand ' + encoded_windows_runner(source, digests)
    command = f'{UV_PREFIX} "{hook_code(source, digests)}" {source} {digests["build_view"]} {digests["index"]}'
    if source == 'claude':
        import shlex
        components = list(dict.fromkeys('/'.join(p.split('/')[:i]) for p in _GUARD_RELATIVES for i in range(1,len(p.split('/'))+1)))
        guard = 'for Q in ' + ' '.join('"$H/' + p + '"' for p in components) + ' "$O"/* "$O"/.[!.]*; do [ -L "$Q" ] && exit 0; done; '
        script = 'H="${CLAUDE_PROJECT_DIR:-$(pwd)}"; O="$H/runtime-data/visual-viewer"; ' + guard + 'mkdir -p "$O" 2>/dev/null || exit 0; cd "$H" || exit 0; ' + command + ' >/dev/null 2>"$O/hook-start-error.log"; exit 0'
        return 'sh -c ' + shlex.quote(script)
    return command


def launcher_digest() -> str:
    return hashlib.sha256(LAUNCHER_TEXT.encode("ascii")).hexdigest()


def write_launcher(harness: Path) -> bool:
    """하네스 `.codex\\`에 Windows용 실행기를 쓴다. 내용이 같으면 그대로 둔다. 바꿨으면 True."""
    path = harness.joinpath(*LAUNCHER_REL)
    raw = LAUNCHER_TEXT.encode("ascii")
    if path.is_file() and path.read_bytes() == raw:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)
    return True


def remove_launcher(harness: Path) -> bool:
    path = harness.joinpath(*LAUNCHER_REL)
    if path.is_file() and path.read_bytes().startswith(b"@echo off\r\nrem LG AX visual viewer"):
        path.unlink()
        return True
    return False


def codex_commands(digests: dict) -> dict:
    """Codex는 동기 훅이라 uv·Python이 시작조차 못 해도 exit 0·무출력이어야 한다(exit 2면 셸 결과를 바꿔 버린다).

    셸의 stderr(uv·Python 시작 오류)는 hook-error.log가 아닌 hook-start-error.log에 매번 덮어쓴다. Windows cmd의
    리다이렉트는 파일을 쓰기 공유 없이 열어 두므로, 같은 파일이면 hook.py의 로그 쓰기가 막힌다.
    - command(macOS·Linux, sh -c): 실행기와 같은 일(빠른 길, `/`에서 가상 환경이 아닌 Python 3.12 찾기, 출력 버리기,
      시작 오류 기록, exit 0)을 sh 문법으로 한다.
    - commandWindows: `.codex\\visual-viewer-hook.cmd codex <지문 4개>`. cmd·Windows PowerShell 5.1·pwsh 7이 같게
      읽는다. 지문이 명령에 있으니 뷰어 파일이나 실행기가 바뀌면 Codex가 다시 신뢰를 요구한다.
    """
    guard_components = list(dict.fromkeys("/".join(p.split("/")[:i])
                                         for p in _GUARD_RELATIVES for i in range(1, len(p.split("/"))+1)))
    posix_guard = ("for Q in " + " ".join('"$H/' + p + '"' for p in guard_components)
                   + ' "$O"/* "$O"/.[!.]* "$H/runtime-data/exports/"*; do [ -L "$Q" ] && exit 0; done; ')
    posix = (f'H="$(pwd)"; O="$H/{LOG_POSIX}"; ' + posix_guard + 'mkdir -p "$O" 2>/dev/null; '
             f'N="$(ls -t "$H/runtime-data/exports/" 2>/dev/null | grep "[.]json$" | head -n 1)"; [ -n "$N" ] || exit 0; '
             f'[ "$N" = "$(cat "$O/{MARKER}" 2>/dev/null)" ] && exit 0; cd / || exit 0; '
             f'P="$({FIND_PYTHON} 2>"$O/{START_LOG}")" || exit 0; '
             f'"$P" -I -B -c "{_LAUNCHER_CODE}" codex "$H" {digests["hook"]} {digests["build_view"]} {digests["index"]} '
             f'>/dev/null 2>>"$O/{START_LOG}"; exit 0')
    return {
        "command": posix,
        "commandWindows": (f"{LAUNCHER_REL[0]}\\{LAUNCHER_REL[1]} codex {digests['hook']} {digests['build_view']} "
                           f"{digests['index']} {launcher_digest()}"),
    }


def where(source: str) -> str:
    target = TARGETS[source]
    return f"{target['event']}({target['matcher']})" if target["matcher"] else target["event"]


def handler(source: str, digests: dict) -> dict:
    target = TARGETS[source]
    if source == "codex":
        value = {"type": "command", **codex_commands(digests), "timeout": target["timeout"]}
    else:
        value = {"type": "command", "command": hook_command(source, digests), "timeout": target["timeout"]}
    if target["async"]:
        value["async"] = True
    return value


def is_ours(item) -> bool:
    if not isinstance(item, dict):
        return False
    text = " ".join(v for v in (item.get("command"), item.get("commandWindows")) if isinstance(v, str))
    encoded = re.search(r"-EncodedCommand\s+([A-Za-z0-9+/=]+)", text)
    if encoded:
        try:
            if base64.b64decode(encoded.group(1), validate=True).decode("utf-16le").startswith("# LG_AX_VISUAL_VIEWER_V1\n"):
                return True
        except (ValueError, UnicodeError):
            pass
    return ("visual-viewer" in text and "hook.py" in text) or LAUNCHER_REL[1] in text


def is_placeholder(item) -> bool:
    return isinstance(item, dict) and item.get("command") == "" and not item.get("commandWindows")


# ---------------------------------------------------------------- settings files

def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ViewerError(f"{path}가 UTF-8이 아니어서(UTF-16·cp949 등) 고치지 않았습니다. UTF-8로 저장한 뒤 다시 실행하세요.") from exc
    except OSError as exc:
        raise ViewerError(f"{path}를 읽지 못했습니다: {exc}") from exc
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise ViewerError(f"{path}가 JSON 형식이 아니어서 고치지 않았습니다: {exc}") from exc
    if not isinstance(value, dict):
        raise ViewerError(f"{path}의 최상위 값이 객체가 아니어서 고치지 않았습니다.")
    return value


def save_config(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def hooks_table(config: dict, path: Path) -> dict:
    table = config.get("hooks", {})
    if not isinstance(table, dict):
        raise ViewerError(f"{path}의 hooks가 객체가 아니어서 고치지 않았습니다.")
    for event, groups in table.items():
        if not isinstance(groups, list):
            raise ViewerError(f"{path}의 hooks.{event}가 목록이 아니어서 고치지 않았습니다.")
        for group in groups:
            if isinstance(group, dict) and "hooks" in group and not isinstance(group["hooks"], list):
                raise ViewerError(f"{path}의 hooks.{event}의 hooks가 목록이 아니어서 고치지 않았습니다.")
    return table


def our_positions(config: dict) -> list[tuple[str, int, int]]:
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    found = []
    for event, groups in table.items():
        for gi, group in enumerate(groups if isinstance(groups, list) else []):
            items = group.get("hooks") if isinstance(group, dict) else None
            for hi, item in enumerate(items if isinstance(items, list) else []):
                if is_ours(item):
                    found.append((event, gi, hi))
    return found


def remove_positions(config: dict, positions: list[tuple[str, int, int]], keep_positions: bool) -> list[str]:
    """주어진 처리기를 지운다. keep_positions면 뒤에 있는 다른 처리기·묶음의 번호가 바뀌지 않게 자리표시를 남긴다.

    돌려주는 목록은 사용자에게 알릴 말이다(빈 명령 자리표시를 남긴 경우 등).
    """
    notes = []
    table = config.get("hooks") or {}
    for event, gi, hi in sorted(positions, reverse=True):
        groups = table[event]
        items = groups[gi]["hooks"]
        last_handler = hi == len(items) - 1
        if keep_positions and not last_handler:
            items[hi] = dict(PLACEHOLDER)
            notes.append(f"{event} 묶음 {gi}의 뒤쪽 훅 {len(items) - hi - 1}개가 신뢰를 잃지 않도록 빈 명령 자리표시를 남겼습니다"
                         " (Codex 시작 때 'skipping empty hook command' 경고가 보일 수 있습니다).")
            continue
        del items[hi]
        if keep_positions:
            while items and is_placeholder(items[-1]):  # 맨 뒤 자리표시는 번호에 영향이 없다
                items.pop()
        if not items:
            if gi == len(groups) - 1 or not keep_positions:
                del groups[gi]
            else:
                groups[gi]["hooks"] = []  # 뒤 묶음의 번호를 지키는 빈 묶음
    for event in list(table):
        if not table[event]:
            del table[event]
    if "hooks" in config and not config["hooks"]:
        del config["hooks"]
    return notes


def place_ours(config: dict, path: Path, source: str, new: dict) -> tuple[str, list[str]]:
    """이 뷰어 항목을 올바른 이벤트·matcher 자리에 넣는다.

    1) 올바른 자리(PostToolUse·target matcher)의 기존 항목은 그 자리에서 바꾼다.
    2) 다른 이벤트·matcher에 있던 항목과 중복 항목은 위치를 지키며 지운다.
    3) 기존 항목이 없으면 해제 때 남긴 자리표시(빈 명령·빈 묶음)를 다시 쓰고, 없으면 맨 끝에 붙인다.
    """
    target = TARGETS[source]
    hooks_table(config, path)
    table = config.setdefault("hooks", {})
    positions = our_positions(config)
    good = [p for p in positions if p[0] == target["event"] and table[p[0]][p[1]].get("matcher") == target["matcher"]]
    if good:
        event, gi, hi = good[0]
        table[event][gi]["hooks"][hi] = new
        notes = remove_positions(config, [p for p in positions if p != good[0]], target["keep_positions"])
        return "갱신", notes
    notes = remove_positions(config, positions, target["keep_positions"])
    if positions:
        notes.append(f"다른 이벤트·matcher에 있던 이 뷰어 항목 {len(positions)}개를 {where(source)}로 옮겼습니다.")
    table = config.setdefault("hooks", {})
    groups = table.setdefault(target["event"], [])
    for group in groups:
        if isinstance(group, dict) and group.get("matcher") == target["matcher"] and isinstance(group.get("hooks"), list):
            for hi, item in enumerate(group["hooks"]):
                if is_placeholder(item):
                    group["hooks"][hi] = new
                    return "추가(이전 자리)", notes
            if not group["hooks"]:
                group["hooks"] = [new]
                return "추가(이전 자리)", notes
    groups.append({"matcher": target["matcher"], "hooks": [new]} if target["matcher"] else {"hooks": [new]})
    return "추가", notes


def remove_ours(config: dict, path: Path, keep_positions: bool = True) -> tuple[int, list[str]]:
    """이 뷰어의 처리기만 지운다. 지운 개수와 알릴 말을 돌려준다."""
    if "hooks" not in config:
        return 0, []
    hooks_table(config, path)
    positions = our_positions(config)
    return len(positions), remove_positions(config, positions, keep_positions)


def count_others(config: dict) -> int:
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    return sum(1 for groups in table.values() if isinstance(groups, list) for g in groups if isinstance(g, dict)
               for h in (g.get("hooks") if isinstance(g.get("hooks"), list) else []) if not is_ours(h) and not is_placeholder(h))


def registered(config: dict, source: str) -> dict:
    """등록된 이 뷰어 명령, 올바른 자리(이벤트·matcher)인지, 그 명령에 든 파일 지문."""
    target = TARGETS[source]
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    found = []
    for event, groups in table.items():
        for group in groups if isinstance(groups, list) else []:
            items = group.get("hooks") if isinstance(group, dict) else None
            for item in items if isinstance(items, list) else []:
                if is_ours(item):
                    found.append((event, group.get("matcher"), item))
    if not found:
        return {"registered": False}
    placed = [f for f in found if f[0] == target["event"] and f[1] == target["matcher"]]
    event, matcher, item = (placed or found)[0]
    digests = []
    for key in ("command", "commandWindows"):
        text = item.get(key) or ""
        encoded = re.search(r"-EncodedCommand\s+([A-Za-z0-9+/=]+)", text)
        if encoded:
            try:
                text = base64.b64decode(encoded.group(1), validate=True).decode("utf-16le")
            except (ValueError, UnicodeError):
                text = ""
        hexes = HEX64.findall(text)
        if hexes:
            names = ("hook", "build_view", "index") + (("launcher",) if LAUNCHER_REL[1] in (item.get(key) or "") else ())
            digests.append(dict(zip(names, hexes)) if len(hexes) == len(names) else None)
    return {"registered": bool(placed), "misplaced": len(found) - len(placed), "event": event, "matcher": matcher,
            "async": bool(item.get("async")), "timeout": item.get("timeout"), "digests": digests}


# ---------------------------------------------------------------- harness

def is_dev_repo(path: Path) -> bool:
    """개발 레포(Git checkout·ZIP 내려받기·git archive 모두). 제품 하네스에는 dev-harness 폴더가 없다."""
    return (path / "dev-harness").is_dir()


def checked_descendant(root: Path, relative: str) -> Path:
    """Reject linked/reparse components before any viewer-owned file access."""
    import stat
    current = root
    for part in Path(relative).parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if current.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ViewerError(f"하네스 하위 연결 경로에는 쓰지 않습니다: {current}")
    if not current.resolve().is_relative_to(root):
        raise ViewerError(f"하네스 밖 경로입니다: {current}")
    return current


def resolve_harness(value: str | None, for_install: bool = False) -> Path:
    if value:
        harness = Path(value).expanduser().resolve()
    else:
        harness = HERE.parents[2]
        if is_dev_repo(harness):
            raise ViewerError("개발 레포에서 실행했습니다. 설치된 하네스 폴더 경로를 지정하세요(예: install --claude C:/내-하네스).")
    if not harness.is_dir():
        raise ViewerError(f"하네스 폴더가 없습니다: {harness}")
    if not (harness / "AGENTS.md").is_file() or not ((harness / "product-tools").is_dir() or (harness / "skills").is_dir()):
        raise ViewerError(f"하네스 폴더가 아닙니다(AGENTS.md와 product-tools 또는 skills가 필요): {harness}")
    if for_install and is_dev_repo(harness):
        raise ViewerError(f"개발 레포에는 설치하지 않습니다: {harness}. 제품 ZIP으로 설치한 하네스 폴더를 지정하세요.")
    for relative in ("web/prototypes/visual-viewer", "runtime-data", ".codex", ".claude",
                     ".codex/hooks.json", ".codex/visual-viewer-hook.cmd", ".claude/settings.local.json"):
        checked_descendant(harness, relative)
    try:
        hook.Paths(str(harness)).validate()
    except hook.IntegrityError as exc:
        raise ViewerError(str(exc)) from exc
    return harness


def copy_app(harness: Path) -> tuple[Path, list[str]]:
    """뷰어 파일을 하네스의 web/prototypes/visual-viewer로 복사한다. 내용이 같으면 건너뛴다."""
    target = harness.joinpath(*APP_REL)
    if target.resolve() == HERE:
        return target, []
    target.mkdir(parents=True, exist_ok=True)
    changed = []
    for name in APP_FILES:
        source = HERE / name
        dest = target / name
        if dest.is_file() and dest.read_bytes() == source.read_bytes():
            continue
        tmp = dest.with_name(f"{name}.{os.getpid()}.tmp")
        shutil.copyfile(source, tmp)
        os.replace(tmp, dest)
        changed.append(name)
    return target, changed


def update_state(paths: hook.Paths, change) -> None:
    """훅과 같은 OS 잠금 아래에서 상태 파일을 고친다(동시에 도는 훅의 기록을 덮어쓰지 않게)."""
    lock = hook.Lock(paths)
    if not lock.acquire(15):
        raise ViewerError("다른 훅이 화면을 만드는 중이라 상태 파일을 고치지 못했습니다. 잠시 뒤 다시 실행하세요.")
    try:
        state = hook.read_state(paths)
        if change(state) is not False:
            hook.write_state(paths, state)
    finally:
        lock.release()


def set_baseline(paths: hook.Paths) -> str | None:
    """설치 순간의 최신 export를 이미 본 것으로 둔다. 다시 설치할 때도(남은 상태가 있어도) 매번 한다.

    화면을 만든 것(built_key)과는 따로 기록하므로 status가 그리지 않은 화면을 최신이라고 하지 않는다.
    """
    latest = hook.newest_export(paths)
    if latest is None:
        return None
    key = hook.export_key(latest)
    moved = []

    def change(state):
        if state.get("last_key") == key:
            return False
        state.update({"last_key": key, "last_export": latest.name, "baseline": True})
        state.pop("failed_key", None)
        moved.append(latest.name)

    update_state(paths, change)
    return moved[0] if moved else None


def codex_feature_layers(harness: Path) -> list[dict]:
    """Codex의 [features] hooks(옛 이름 codex_hooks)를 하네스·사용자 config.toml에서 읽는다.

    관리자 requirements.toml·managed 설정은 위치가 환경마다 달라 읽지 않는다(결과에 그렇게 적는다).
    """
    try:
        import tomllib
    except ImportError:  # Python 3.10
        tomllib = None
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    layers = []
    for name, path in (("project", harness / ".codex" / "config.toml"), ("user", home / "config.toml")):
        entry = {"layer": name, "path": str(path), "exists": path.is_file(), "hooks": None}
        if path.is_file() and tomllib:
            try:
                features = tomllib.loads(path.read_text(encoding="utf-8-sig")).get("features")
                features = features if isinstance(features, dict) else {}
                value = features.get("hooks", features.get("codex_hooks"))
                entry["hooks"] = value if isinstance(value, bool) else None
            except (OSError, ValueError, UnicodeDecodeError) as exc:
                entry["error"] = str(exc)[:200]
        layers.append(entry)
    return layers


def codex_hooks_effective(layers: list[dict]) -> bool:
    """신뢰한 프로젝트 설정이 사용자 설정보다 우선한다. 둘 다 없으면 Codex 기본값(켜짐)."""
    for layer in layers:  # project, user 순서
        if layer["hooks"] is not None:
            return layer["hooks"]
    return True


def codex_hooks_disabled(harness: Path) -> bool:
    return not codex_hooks_effective(codex_feature_layers(harness))


# ---------------------------------------------------------------- commands

def selected(args) -> list[str]:
    sources = [s for s in ("claude", "codex") if getattr(args, s) or args.both]
    if not sources:
        raise ViewerError("--claude, --codex, --both 중 하나를 주세요.")
    return sources


def cmd_install(args) -> int:
    harness = resolve_harness(args.harness, for_install=True)
    sources = selected(args)
    configs = {}
    for source in sources:  # 선택한 CLI 설정을 모두 읽을 수 있을 때만 바꾼다
        path = harness.joinpath(*TARGETS[source]["file"])
        configs[source] = (path, load_config(path))
        hooks_table(configs[source][1], path)
    app, changed = copy_app(harness)
    digests = app_digests(app)
    paths = hook.Paths(str(harness))
    os.makedirs(paths.out, exist_ok=True)
    page = Path(paths.out, "index.html")
    if not page.is_file() or page.read_bytes() != (app / "index.html").read_bytes():  # 첫 export 전에도 열 수 있는 빈 화면
        shutil.copyfile(app / "index.html", page)
    baseline = set_baseline(paths)
    print(f"뷰어 파일: {app} ({'갱신 ' + ', '.join(changed) if changed else '변경 없음'})")
    print(f"화면 위치: {page}")
    if baseline:
        print(f"설치 전 export({baseline})는 자동으로 띄우지 않습니다. 보려면 open --latest를 쓰세요.")
    for source in sources:
        path, config = configs[source]
        target = TARGETS[source]
        if source == "codex" and write_launcher(harness):
            print(f"Windows용 Codex 실행기: {harness.joinpath(*LAUNCHER_REL)}")
        how, notes = place_ours(config, path, source, handler(source, digests))
        save_config(path, config)
        rel = "/".join(target["file"])
        print(f"[{target['name']}] {rel}에 {where(source)} 훅을 {how}했습니다. "
              f"다른 훅 {count_others(config)}개는 내용과 위치를 그대로 둡니다.")
        for note in notes:
            print(f"  {note}")
        if source == "claude":
            print("  다음: 이 하네스 폴더에서 Claude Code를 새로 열고 질문하세요. export가 저장되면 브라우저가 한 번 열립니다.")
        else:
            print("  다음: 이 하네스 폴더에서 `codex --search`를 열고 `/hooks`에서 이 훅을 검토·신뢰(trust)하세요.")
            print("        신뢰하기 전에는 실행되지 않습니다. 뷰어 파일을 갱신하면 명령의 지문이 바뀌어 다시 신뢰해야 합니다.")
            print("        답변이 끝날 때(Stop) 한 번 돌고, 새 export가 없으면 Python 없이 바로 끝납니다. 신뢰 우회 옵션은 쓰지 마세요.")
            if codex_hooks_disabled(harness):
                print("  주의: [features] hooks = false(프로젝트 설정이 없으면 사용자 설정 기준)라 Codex가 훅을 실행하지 않습니다.")
    # 공유 파일이 바뀌었을 수 있으니, 이번에 고르지 않은 CLI에 이미 등록된 항목도 새 지문으로 맞춘다.
    for source in (s for s in TARGETS if s not in sources):
        target = TARGETS[source]
        path = harness.joinpath(*target["file"])
        try:
            config = load_config(path)
            info = registered(config, source)
            if not (info["registered"] or info.get("misplaced")):
                continue
            wanted = {**digests, "launcher": launcher_digest()}
            if source == "codex":
                write_launcher(harness)
            if info.get("registered") and all(d is not None and all(d[k] == wanted[k] for k in d) for d in info.get("digests") or [None]):
                continue
            how, notes = place_ours(config, path, source, handler(source, digests))
            save_config(path, config)
        except ViewerError as exc:
            print(f"[{target['name']}] 주의: 이미 등록된 훅의 지문을 새 파일에 맞추지 못했습니다. 그 CLI의 훅은 실행되지 않습니다. {exc}")
            continue
        print(f"[{target['name']}] 이미 등록된 훅도 새 파일 지문으로 갱신했습니다."
              + (" Codex에서는 `/hooks`에서 다시 신뢰해야 실행됩니다." if source == "codex" else ""))
        for note in notes:
            print(f"  {note}")
    if not shutil.which("uv"):
        print("주의: uv가 PATH에 없습니다. 훅 명령은 uv로 Python 3.12를 실행합니다.")
    return 0


def cmd_uninstall(args) -> int:
    harness = resolve_harness(args.harness)
    for source in selected(args):
        target = TARGETS[source]
        path = harness.joinpath(*target["file"])
        if not path.exists():
            print(f"[{target['name']}] {'/'.join(target['file'])} 없음 · 지울 훅이 없습니다.")
            continue
        config = load_config(path)
        removed, notes = remove_ours(config, path, target["keep_positions"])
        if not removed:
            print(f"[{target['name']}] 이 뷰어의 훅이 없습니다.")
            continue
        if source == "codex" and not config:
            path.unlink()  # 이 뷰어의 훅만 있던 파일
            print(f"[{target['name']}] 훅 {removed}개를 지우고 빈 {'/'.join(target['file'])}를 삭제했습니다.")
        else:
            save_config(path, config)
            print(f"[{target['name']}] 훅 {removed}개를 지웠습니다. 다른 훅의 내용과 위치는 그대로 둡니다.")
        if source == "codex" and remove_launcher(harness):
            print(f"[{target['name']}] Windows용 실행기 {'/'.join(LAUNCHER_REL)}를 지웠습니다.")
        for note in notes:
            print(f"  {note}")
    print("뷰어 파일과 runtime-data/visual-viewer의 화면·insights는 남겨 둡니다(필요 없으면 직접 지우세요).")
    return 0


def cmd_open(args) -> int:
    harness = resolve_harness(args.harness)
    paths = hook.Paths(str(harness))
    if args.export:
        export = Path(args.export).expanduser().resolve()
    else:
        latest = hook.newest_export(paths)
        if latest is None:
            raise ViewerError(f"export가 없습니다: {paths.exports}")
        export = Path(latest.path)
    insights = Path(args.insights) if args.insights else None
    try:
        summary = build_view.generate(export, insights, args.focus or "auto", out_dir=Path(paths.out),
                                      insights_dir=None if insights else Path(paths.out))
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - 사람에게 이유를 보여주고 traceback은 내지 않는다
        raise ViewerError(f"화면을 만들지 못했습니다({export.name}): {type(exc).__name__}: {exc}") from exc
    stat = export.stat()
    key = f"{export.name}:{stat.st_mtime_ns}:{stat.st_size}"
    in_exports = Path(paths.exports).resolve() == export.parent

    def change(state):
        # 화면에 그린 export를 기록한다. 최신이 아닌 export를 열었으면 훅이 최신을 다시 그리도록 last_key는 두지 않는다.
        state.update({"built_key": key if in_exports else f"{export.name}:manual", "insights": summary["insights"],
                      "insights_file": summary.get("insights_file"), "warnings": summary["warnings"],
                      "web_delivery": summary.get("web_delivery"), "web_signature": hook.web_signature(paths)})
        latest = hook.newest_export(paths)
        if in_exports and latest is not None and hook.export_key(latest) == key:
            state.update({"last_key": key, "last_export": export.name})
            state.pop("failed_key", None)
            state.pop("baseline", None)
        else:
            # A manually selected historical/external result is not the current
            # export. Clear the fast-path marker so the next hook restores it.
            state.pop("last_key", None)
            state.pop("baseline", None)

    update_state(paths, change)
    index = Path(summary["outputs"]["index"]).resolve()
    if not args.no_browser:
        import webbrowser

        webbrowser.open(index.as_uri())
    print(json.dumps({"export": export.name, "insights": summary["insights"], "insights_file": summary.get("insights_file"),
                      "focus": summary["focus"], "pages": summary["pages"], "index": str(index), "warnings": summary["warnings"]},
                     ensure_ascii=False, indent=1))
    return 0


def cli_version(name: str) -> str | None:
    """`<cli> --version`의 x.y.z. 없으면 None. 대화 세션을 열지 않는다(짧은 시간 제한)."""
    exe = shutil.which(name)
    if not exe:
        return None
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return "확인 실패"
    found = re.search(r"\d+\.\d+\.\d+", proc.stdout + proc.stderr)
    return found.group(0) if found else "확인 실패"


def version_report() -> tuple[dict, list[str]]:
    versions = {"codex": cli_version("codex"), "claude": cli_version("claude")}
    warnings = [f"{name} {version}은(는) 확인한 버전({', '.join(TESTED_VERSIONS[name])})이 아닙니다. "
                f"`viewer.py selftest`를 실행하고 {'/hooks' if name == 'codex' else '/hooks 화면'}에서 훅을 다시 확인하세요."
                for name, version in versions.items() if version and version not in TESTED_VERSIONS[name]]
    return versions, warnings


def cmd_status(args) -> int:
    harness = resolve_harness(args.harness)
    paths = hook.Paths(str(harness))
    app = harness.joinpath(*APP_REL)
    report = {"harness": str(harness), "app_files": {n: (app / n).is_file() for n in APP_FILES}}
    current = app_digests(app) if all((app / n).is_file() for n in ("hook.py", "build_view.py", "index.html")) else None
    launcher = harness.joinpath(*LAUNCHER_REL)
    if current is not None:
        current["launcher"] = digest(launcher) if launcher.is_file() else None
    for source, target in TARGETS.items():
        path = harness.joinpath(*target["file"])
        try:
            info = registered(load_config(path), source)
        except ViewerError as exc:
            info = {"registered": False, "error": str(exc)}
        info["file"] = "/".join(target["file"])
        if "digests" in info:
            info["files_match_command"] = bool(current) and bool(info["digests"]) and all(
                d is not None and all(d[k] == current.get(k) for k in d) for d in info["digests"])
            del info["digests"]
        report[source] = info
    layers = codex_feature_layers(harness)
    report["codex"]["launcher"] = "/".join(LAUNCHER_REL) if launcher.is_file() else None
    report["codex_features"] = layers
    report["codex_hooks_disabled"] = not codex_hooks_effective(layers)
    report["codex_features_note"] = "프로젝트 설정이 사용자 설정보다 우선합니다. 관리자 requirements.toml·managed 설정은 확인하지 않았습니다."
    latest = hook.newest_export(paths)
    state = hook.read_state(paths)
    built = Path(paths.out, "view-data.js").is_file() and bool(state.get("built_key"))
    report["latest_export"] = latest.name if latest else None
    report["view_built"] = built
    report["last_built"] = state["built_key"].rsplit(":", 2)[0] if built else None
    report["baseline_only"] = bool(state.get("baseline")) and not built
    report["up_to_date"] = bool(latest) and built and state.get("built_key") == hook.export_key(latest)
    report["insights"] = state.get("insights") if built else None
    report["view_warnings"] = len(state.get("warnings") or []) if built else 0
    report["opened_sessions"] = len(state.get("opened_sessions") or [])
    # hook-error.log(훅 자신)과 hook-start-error.log(Codex 셸이 남긴 uv·Python 시작 오류) 중 더 최근에 쓴 쪽의 마지막 줄.
    latest_line = None
    for path in (Path(paths.error_log), Path(paths.out, START_LOG)):
        try:
            lines = [line for line in path.read_bytes().decode("utf-8", errors="replace").splitlines() if line.strip()]
            stamp = path.stat().st_mtime_ns
        except OSError:
            continue
        if lines and (latest_line is None or stamp >= latest_line[0]):
            latest_line = (stamp, lines[-1], path.name)
    report["last_error"] = latest_line[1] if latest_line else None
    report["last_error_file"] = latest_line[2] if latest_line else None
    report["uv_on_path"] = bool(shutil.which("uv"))
    report["cli_versions"], report["version_warnings"] = version_report()
    report["tested_versions"] = TESTED_VERSIONS
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


# ---------------------------------------------------------------- selftest

def git_bash() -> str | None:
    if os.name != "nt":
        return shutil.which("bash")
    candidates = []
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parents[1]
        candidates += [root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"]
    candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe")
    found = next((str(c) for c in candidates if c.is_file()), None)
    if found:
        return found
    which = shutil.which("bash")
    return which if which and "system32" not in which.lower() else None  # WSL bash는 쓰지 않는다


def selftest_shells(source: str, item: dict) -> list[tuple[str, object]]:
    """CLI가 이 OS에서 훅을 실행하는 셸들과 실행 인자(문자열이면 raw 명령줄). 없는 셸은 빼고 이름만 남긴다."""
    shells = []
    if os.name == "nt":
        system = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        powershell = os.path.join(system, "WindowsPowerShell", "v1.0", "powershell.exe")
        pwsh = shutil.which("pwsh") or r"C:\Program Files\PowerShell\7\pwsh.exe"
        if source == "codex":
            command = item["commandWindows"]
            comspec = os.environ.get("COMSPEC") or os.path.join(system, "cmd.exe")
            shells.append(("cmd", f'{comspec} /C "{command}"'))  # codex 0.146(그리고 세션 셸이 없을 때)
            shells.append(("powershell", [powershell, "-NoProfile", "-Command", command]))  # codex 0.162 기본
            shells.append(("pwsh", [pwsh, "-NoProfile", "-Command", command] if os.path.isfile(pwsh) else None))
        else:
            command = item["command"]
            bash = git_bash()
            shells.append(("git-bash", [bash, "-c", command] if bash else None))  # Claude Code 기본
            shells.append(("powershell", [powershell, "-NoProfile", "-Command", command]))  # Git Bash가 없을 때
    else:
        shells.append(("sh", ["/bin/sh", "-c", item["command"]]))
        bash = shutil.which("bash")
        shells.append(("bash", [bash, "-c", item["command"]] if bash else None))
    return shells


def synthetic_export(name: str) -> dict:
    return {"session_id": f"selftest-{name}", "turns": [], "semantic_status": "unverified", "acceptance_ready": False,
            "usage_summary": {"status": "unknown"},
            "requests": [{"input": {"question": "[합성 시험 자료] viewer.py selftest"}, "turn_id": None, "request_version": 0,
                          "events": [], "response": {"status": "needs_input", "reason": {"code": "selftest", "message": "synthetic"}},
                          "research_usage": {"status": "unknown"}}]}


def cmd_selftest(args) -> int:
    """등록된 정확한 훅 명령을 각 셸에서 임시 사본으로 실행한다. 실제 화면·상태는 건드리지 않고 브라우저·모델을 쓰지 않는다."""
    harness = resolve_harness(args.harness)
    wanted = [s for s in ("claude", "codex") if getattr(args, s) or args.both] or list(TARGETS)
    entries = {}
    for source in wanted:
        target = TARGETS[source]
        config = load_config(harness.joinpath(*target["file"]))
        table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
        items = [h for g in table.get(target["event"]) or [] if isinstance(g, dict) and g.get("matcher") == target["matcher"]
                 for h in (g.get("hooks") or []) if is_ours(h)]
        if items:
            entries[source] = items[0]
        elif source in [s for s in ("claude", "codex") if getattr(args, s) or args.both]:
            raise ViewerError(f"{target['name']} 훅이 등록되어 있지 않습니다. install을 먼저 실행하세요.")
    if not entries:
        raise ViewerError("등록된 훅이 없습니다. install을 먼저 실행하세요.")
    results = []
    with tempfile.TemporaryDirectory(prefix="lgax-viewer-selftest-") as tmp:
        copy = Path(tmp) / "harness"
        app = copy.joinpath(*APP_REL)
        app.mkdir(parents=True)
        (copy / "product-tools").mkdir()
        (copy / "AGENTS.md").write_text("# viewer selftest copy\n", encoding="utf-8")
        for name in APP_FILES:
            if harness.joinpath(*APP_REL, name).is_file():
                shutil.copyfile(harness.joinpath(*APP_REL, name), app / name)
        if harness.joinpath(*LAUNCHER_REL).is_file():
            copy.joinpath(LAUNCHER_REL[0]).mkdir()
            shutil.copyfile(harness.joinpath(*LAUNCHER_REL), copy.joinpath(*LAUNCHER_REL))
        exports = copy / "runtime-data" / "exports"
        exports.mkdir(parents=True)
        paths = hook.Paths(str(copy))
        base_env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        base_env["LGAX_VIEWER_NO_OPEN"] = "1"
        for source, item in entries.items():
            for shell, argv in selftest_shells(source, item):
                row = {"cli": source, "shell": shell}
                if argv is None:
                    results.append({**row, "result": "skip", "reason": "이 PC에 없는 셸"})
                    continue
                name = f"{source}-{shell}"
                export = exports / f"export-selftest-{name}.json"
                export.write_text(json.dumps(synthetic_export(name), ensure_ascii=False), encoding="utf-8")
                stamp = time.time() + len(results) + 1
                os.utime(export, (stamp, stamp))
                payload = ({"session_id": f"selftest-{name}", "turn_id": "selftest", "hook_event_name": "Stop", "stop_hook_active": False,
                            "last_assistant_message": "[합성 시험 자료] selftest", "cwd": str(copy)} if source == "codex"
                           else {"session_id": f"selftest-{name}", "hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": str(copy)})
                env = dict(base_env, CLAUDE_PROJECT_DIR=str(copy)) if source == "claude" else base_env
                started = time.perf_counter()
                try:
                    proc = subprocess.run(argv, input=json.dumps(payload).encode("utf-8"), capture_output=True, cwd=copy, env=env, timeout=120)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    results.append({**row, "result": "fail", "reason": f"{type(exc).__name__}: {exc}"})
                    continue
                state = hook.read_state(paths)
                built = (state.get("last_export") == export.name and Path(paths.out, "index.html").is_file()
                         and Path(paths.out, "view-data.js").is_file())
                opened = bool(state.get("opened_sessions"))
                ok = proc.returncode == 0 and not proc.stdout and not proc.stderr and built and not opened
                row.update(result="pass" if ok else "fail", exit=proc.returncode, output_bytes=len(proc.stdout) + len(proc.stderr),
                           view_rebuilt=built, open_requested=opened, display_verified=False, seconds=round(time.perf_counter() - started, 2))
                if not ok:
                    logs = [Path(paths.error_log), Path(paths.out, START_LOG)]
                    last = [line for f in logs if f.is_file() for line in f.read_bytes().decode("utf-8", "replace").splitlines() if line.strip()]
                    row["reason"] = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip()[:300] or (last[-1] if last else "기록 없음")
                results.append(row)
    failed = [r for r in results if r["result"] == "fail"]
    print(json.dumps({"harness": str(harness), "results": results, "ok": not failed,
                      "note": "임시 사본·합성 export로 실행했습니다. 실제 화면·상태·브라우저·모델은 쓰지 않았습니다."}, ensure_ascii=False, indent=1))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="하네스 시각자료 뷰어 설치·해제·열기")
    sub = ap.add_subparsers(dest="command", required=True)
    for name, text in (("install", "훅 등록과 뷰어 파일 복사"), ("uninstall", "이 뷰어의 훅만 해제")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--claude", action="store_true", help=".claude/settings.local.json")
        p.add_argument("--codex", action="store_true", help=".codex/hooks.json")
        p.add_argument("--both", action="store_true", help="둘 다")
        p.add_argument("harness", nargs="?", help="하네스 폴더 (설치된 하네스 안의 viewer.py라면 생략 가능)")
    p = sub.add_parser("open", help="최근 export로 화면을 다시 만들고 연다")
    p.add_argument("--latest", action="store_true", help="가장 최근 export (기본 동작)")
    p.add_argument("--export", help="특정 export 파일")
    p.add_argument("--insights", help="insights 파일 (기본: runtime-data/visual-viewer에서 session_id·turn_id로 고름)")
    p.add_argument("--focus", help="처음 보여줄 화면 id (기본: 상태로 선택)")
    p.add_argument("--no-browser", action="store_true", help="브라우저를 열지 않고 화면만 만든다")
    p.add_argument("harness", nargs="?", help="하네스 폴더 (설치된 하네스 안의 viewer.py라면 생략 가능)")
    p = sub.add_parser("status", help="설치·갱신 상태")
    p.add_argument("harness", nargs="?", help="하네스 폴더 (설치된 하네스 안의 viewer.py라면 생략 가능)")
    p = sub.add_parser("selftest", help="등록된 훅 명령을 각 셸에서 임시 사본으로 실행해 본다(CLI 업데이트 뒤)")
    p.add_argument("--claude", action="store_true", help="Claude Code 훅만")
    p.add_argument("--codex", action="store_true", help="Codex 훅만")
    p.add_argument("--both", action="store_true", help="둘 다(기본: 등록된 것 모두)")
    p.add_argument("harness", nargs="?", help="하네스 폴더 (설치된 하네스 안의 viewer.py라면 생략 가능)")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    commands = {"install": cmd_install, "uninstall": cmd_uninstall, "open": cmd_open, "status": cmd_status, "selftest": cmd_selftest}
    try:
        return commands[args.command](args)
    except ViewerError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
