"""LG AX agent office - install, remove and check the passive observer hook; convert what it recorded.

    uv run python web/prototypes/agent-office/office.py install --claude C:/my-harness [--open-on-prompt [--page factory|office]]
    uv run python web/prototypes/agent-office/office.py status --claude C:/my-harness
    uv run python web/prototypes/agent-office/office.py uninstall --claude C:/my-harness
    uv run python web/prototypes/agent-office/office.py watch --claude C:/my-harness
    uv run python web/prototypes/agent-office/office.py open --claude C:/my-harness [--page factory|office]
    uv run python web/prototypes/agent-office/office.py codex --harness C:/my-harness --latest
    uv run python web/prototypes/agent-office/office.py codex --harness C:/my-harness --wait --open
    uv run python web/prototypes/agent-office/office.py codex-sessions --harness C:/my-harness
    uv run python web/prototypes/agent-office/office.py trace C:/my-harness --out trace.json
    uv run python web/prototypes/agent-office/office.py selftest

install copies observe.py, office.py, README.md and the two pages (the 3D office index.html built from app/, and the
run dashboard factory.html built from web/prototypes/control-room/factory-dashboard) to
`<harness>/web/prototypes/agent-office/`, puts a copy of each page next to the records in
`<harness>/runtime-data/agent-office/` (the pages read live.js beside them), and ADDS async command hooks to
`<harness>/.claude/settings.local.json`. Other settings and hooks (for example the visual viewer's) are kept
as they are. Settings that are not a UTF-8 JSON object stop the install without changes. The hook runs observe.py only
when its SHA-256 matches the installed fingerprint, refuses symlinked/junction folders, prints nothing and always ends
with exit 0, so it cannot block or change a tool call. Standard library only; no model or business tool is called.
`--open-on-prompt` also writes `runtime-data/agent-office/auto-open.json`: the hook then opens the run dashboard (the
factory page; `--page office` for the 3D office) in the default browser at the first question of each session (once per
session). Installing without it removes that file.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_REL = ("web", "prototypes", "agent-office")
APP_FILES = ("observe.py", "office.py", "codex_follow.py", "README.md")
PAGE = "index.html"  # the 3D office, one self-contained file built by app/ (npm run build)
FACTORY = "factory.html"  # the run dashboard, one file built by control-room/factory-dashboard (npm run build:office)
PAGES = {"factory": FACTORY, "office": PAGE}  # the names auto-open.json and `--page` accept; the default comes first
SETTINGS_REL = (".claude", "settings.local.json")
AUTO_OPEN = "auto-open.json"  # beside the records; observe.py reads it at UserPromptSubmit
MARKER = "LG_AX_AGENT_OFFICE_V1"
TOOL_EVENTS = ("PreToolUse", "PostToolUse", "PostToolUseFailure")
OTHER_EVENTS = ("UserPromptSubmit", "Stop", "SubagentStart", "SubagentStop", "SessionStart", "SessionEnd")
TESTED_CLAUDE = ("2.1.289",)

SKILL_KO = {"evidence-retrieval": "근거 조회", "web-evidence-collection": "웹 수집", "needs-structuring": "불편 구조화",
            "feature-comparison": "기능 대조", "concept-writing": "콘셉트 작성", "review-and-revise": "검토·수정"}
ROLE_KO = {"product_official_researcher": "공식 자료 조사", "product_review_researcher": "후기 조사·분석",
           "product_evidence_reviewer": "독립 근거 검토", "main": "메인", "other_subagent": "다른 하위 에이전트"}

# Python passed with -c: no $ % ! ` \ ^ & | < > so Git Bash, PowerShell and cmd read it the same way.
PY_CODE = ("import hashlib,os,sys;d=os.path.abspath(sys.argv.pop(2));h=sys.argv.pop(2);"
           "p=os.path.join(d,'web','prototypes','agent-office','observe.py');"
           "b=open(p,'rb').read() if os.path.isfile(p) else b'';"
           "exec(compile(b,p,'exec'),{'__name__':'__main__','__file__':p}) if hashlib.sha256(b).hexdigest()==h else None")
UV_ARGS = "run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c "
GUARD_DIRS = ("web", "web/prototypes", "web/prototypes/agent-office", "runtime-data", "runtime-data/agent-office")


class OfficeError(Exception):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def windows_runner(sha: str) -> str:
    """PowerShell script: refuse reparse points, pass stdin to the pinned observe.py through uv, drop all output."""
    guard = ("function G($r){try{foreach($x in @(" + ",".join("'" + d + "'" for d in GUARD_DIRS) + ")){"
             "$p=[IO.Path]::Combine($r,$x);try{$a=[IO.File]::GetAttributes($p)}catch [IO.FileNotFoundException]{continue}"
             "catch [IO.DirectoryNotFoundException]{continue};if($a -band 1024){return $false}};"
             "foreach($x in @('web/prototypes/agent-office','runtime-data/agent-office')){$p=[IO.Path]::Combine($r,$x);"
             "if([IO.Directory]::Exists($p)){foreach($e in (Get-ChildItem -LiteralPath $p -Force)){if($e.Attributes -band 1024){return $false}}}};"
             "return $true}catch{return $false}};")
    runner = ("function P($f,$a,$d,[byte[]]$b){$i=[Diagnostics.ProcessStartInfo]::new();$i.FileName=$f;$i.Arguments=$a;$i.WorkingDirectory=$d;"
              "$i.UseShellExecute=$false;$i.CreateNoWindow=$true;$i.RedirectStandardOutput=$true;$i.RedirectStandardError=$true;"
              "$i.StandardOutputEncoding=[Text.Encoding]::UTF8;$i.StandardErrorEncoding=[Text.Encoding]::UTF8;$i.RedirectStandardInput=$true;"
              "$p=[Diagnostics.Process]::Start($i);$p.StandardInput.BaseStream.Write($b,0,$b.Length);$p.StandardInput.Close();"
              "$o=$p.StandardOutput.ReadToEnd();$e=$p.StandardError.ReadToEnd();$p.WaitForExit();return ,@($p.ExitCode,$o,$e)};")
    execution = ("$a='" + UV_ARGS + "'+[char]34+'" + PY_CODE.replace("'", "''") + "'+[char]34+' claude '+[char]34+$r+'/.'+[char]34+' " + sha + "';"
                 "$v=P 'uv' $a $r $b;if($v[2]){[IO.File]::WriteAllText($l,$v[2],$u)};")
    return ("# " + MARKER + "\n$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';" + guard + runner +
            "try{$r=$env:CLAUDE_PROJECT_DIR;if(-not $r){$r=(Get-Location).Path};if(-not (G $r)){exit 0};"
            "$o=[IO.Path]::Combine($r,'runtime-data/agent-office');[void][IO.Directory]::CreateDirectory($o);"
            "$l=[IO.Path]::Combine($o,'observe-start-error.log');$u=[Text.UTF8Encoding]::new($false);"
            "$m=[IO.MemoryStream]::new();[Console]::OpenStandardInput().CopyTo($m);$b=$m.ToArray();" + execution +
            "}catch{};exit 0")


def hook_command(sha: str, windows: bool | None = None) -> str:
    windows = os.name == "nt" if windows is None else windows
    if windows:
        encoded = base64.b64encode(windows_runner(sha).encode("utf-16le")).decode("ascii")
        return "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + encoded
    checks = " ".join('"$H/' + d + '"' for d in GUARD_DIRS)
    script = (": " + MARKER + "; H=\"${CLAUDE_PROJECT_DIR:-$(pwd)}\"; for Q in " + checks + "; do [ -L \"$Q\" ] && exit 0; done; "
              "cd \"$H\" || exit 0; uv " + UV_ARGS + "\"" + PY_CODE + "\" claude \"$H/.\" " + sha + " >/dev/null 2>&1; exit 0")
    return "sh -c " + shlex.quote(script)


def is_ours(command) -> bool:
    if not isinstance(command, str):
        return False
    if MARKER in command:
        return True
    token = "-EncodedCommand "
    if token in command:
        try:
            return MARKER in base64.b64decode(command.split(token, 1)[1].strip()).decode("utf-16le", errors="ignore")
        except ValueError:
            return False
    return False


def command_sha(command: str) -> str | None:
    """The observe.py fingerprint inside one of our commands (for status)."""
    text = command
    if "-EncodedCommand " in command:
        text = base64.b64decode(command.split("-EncodedCommand ", 1)[1].strip()).decode("utf-16le", errors="ignore")
    for word in reversed(text.replace("'", " ").replace(";", " ").split()):
        if len(word) == 64 and all(c in "0123456789abcdef" for c in word):
            return word
    return None


# --- settings -------------------------------------------------------------------------------------------------------
def read_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OfficeError(f"{path}는 UTF-8이 아닙니다. 바꾸지 않고 멈춥니다.") from exc
    text = text.lstrip("\ufeff")
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError as exc:
        raise OfficeError(f"{path}가 올바른 JSON이 아닙니다. 바꾸지 않고 멈춥니다.") from exc
    if not isinstance(data, dict):
        raise OfficeError(f"{path}의 최상위가 객체가 아닙니다. 바꾸지 않고 멈춥니다.")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict) or any(not isinstance(v, list) for v in hooks.values()):
        raise OfficeError(f"{path}의 hooks 형식을 알 수 없습니다. 바꾸지 않고 멈춥니다.")
    return data


def write_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def without_ours(groups: list) -> list:
    kept = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            kept.append(group)
            continue
        handlers = [h for h in group["hooks"] if not (isinstance(h, dict) and is_ours(h.get("command")))]
        if handlers or not group["hooks"]:
            kept.append({**group, "hooks": handlers})
    return kept


def merged(data: dict, command: str | None) -> dict:
    """Settings with our handlers removed and, when command is given, added once per event."""
    data = json.loads(json.dumps(data))
    hooks = data.setdefault("hooks", {})
    for event in TOOL_EVENTS + OTHER_EVENTS:
        groups = without_ours(hooks.get(event, []))
        if command:
            handler = {"type": "command", "command": command, "async": True, "timeout": 30}
            groups.append({"matcher": "*", "hooks": [handler]} if event in TOOL_EVENTS else {"hooks": [handler]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop("hooks")
    return data


def check_harness(harness: Path) -> Path:
    harness = harness.resolve()
    if not harness.is_dir():
        raise OfficeError(f"하네스 폴더가 없습니다: {harness}")
    if (harness / "dev-harness").is_dir():
        raise OfficeError("개발 레포에는 설치하지 않습니다. 설치된 하네스 폴더를 지정하세요.")
    if not (harness / "product-install.json").is_file() and not (harness / ".claude").is_dir():
        raise OfficeError(f"설치된 하네스 폴더로 보이지 않습니다(product-install.json 없음): {harness}")
    return harness


def set_auto_open(harness: Path, page: str | None):
    """page is a PAGES name (the hook opens only those files), or None to turn auto-open off."""
    path = harness / "runtime-data" / "agent-office" / AUTO_OPEN
    if page:
        write_atomic(path, json.dumps({"open_on_prompt": True, "page": page, "opened": []}) + "\n")
    elif path.is_file():
        path.unlink()


def default_page(harness: Path, page: str | None = None) -> str | None:
    """The requested page name, else the run dashboard when it is installed, else the office page."""
    if page is not None and page not in PAGES:
        raise OfficeError(f"알 수 없는 화면입니다: {page} (factory 또는 office)")
    out = harness / "runtime-data" / "agent-office"
    for name in ([page] if page else list(PAGES)):
        if (out / PAGES[name]).is_file():
            return name
    return None


def install(harness: Path, open_on_prompt: bool = False, page: str | None = None) -> str:
    harness = check_harness(harness)
    settings = harness.joinpath(*SETTINGS_REL)
    data = read_settings(settings)  # read and check first: nothing is copied when the settings cannot be merged
    if page is not None and page not in PAGES:
        raise OfficeError(f"알 수 없는 화면입니다: {page} (factory 또는 office)")
    app = copy_files(harness)
    pages = copy_page(harness)
    sha = digest(app / "observe.py")
    write_atomic(settings, json.dumps(merged(data, hook_command(sha)), ensure_ascii=False, indent=2) + "\n")
    target = default_page(harness, page) if open_on_prompt else None
    set_auto_open(harness, target)
    events = len(TOOL_EVENTS) + len(OTHER_EVENTS)
    out = harness / "runtime-data" / "agent-office"
    page_line = "".join(f"{label}: {out / PAGES[name]}\n" for name, label in (("factory", "실행 대시보드(공장 관제)"), ("office", "사무실 화면(3D)"))
                        if out.joinpath(PAGES[name]) in pages)
    page_line = page_line or "화면: index.html·factory.html이 없어 복사하지 않았습니다 (각 앱 폴더에서 빌드).\n"
    if target:
        page_line += f"  세션의 첫 질문 때 {PAGES[target]}을 기본 브라우저로 한 번 엽니다 (끄기: --open-on-prompt 없이 다시 install).\n"
    return (f"관찰 파일: {app}\n기록 위치: {harness / 'runtime-data' / 'agent-office'}\n{page_line}"
            f"[Claude Code] {settings.relative_to(harness)}에 관찰 훅 {events}개(백그라운드)를 추가했습니다. 다른 훅은 그대로 둡니다.\n"
            "  다음: 이 하네스 폴더에서 Claude Code를 새로 열고(처음이면 폴더 신뢰 허용) 질문하세요.\n"
            "  훅은 출력이 없고 항상 정상 종료하므로 도구 호출을 막거나 바꾸지 않습니다. 끄기: office.py uninstall --claude <폴더>")


def copy_files(harness: Path) -> Path:
    app = harness.joinpath(*APP_REL)
    app.mkdir(parents=True, exist_ok=True)
    for name in APP_FILES:
        source = HERE / name
        if source.resolve() != (app / name).resolve():
            tmp = app / f"{name}.{os.getpid()}.tmp"
            shutil.copyfile(source, tmp)
            os.replace(tmp, app / name)
    return app


def codex(harness: Path, rollout=None, latest=False, once=False, until_complete=False, max_minutes=180.0, out=None, wait=False,
          open_page_once=False, opener=None, page=None) -> int:
    """Follow one Codex session into the office records (no hooks; Codex settings are not touched).
    open_page_once opens the run dashboard (or `page`) when the first records of the session are written (live view)."""
    harness = check_harness(harness)
    out = out or sys.stdout
    opened = []
    copy_files(harness)  # the pages and the follower live in the harness too (no Codex settings are changed)
    copy_page(harness)
    shown = harness / "runtime-data" / "agent-office" / PAGES[default_page(harness, page) or "office"]
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import codex_follow

    def announce(path, meta):
        print(f"Codex 세션 {meta['id']} ({meta.get('ts') or '시각 미확인'})\n기록 파일: {path}\n"
              f"실행 대시보드: {shown}" + ("" if once else "\n따라가는 중입니다. 멈추려면 Ctrl+C."), file=out)

    def printer(event):
        if open_page_once and not opened:
            opened.append(True)
            print(open_page(harness, opener=opener, page=page), file=out, flush=True)
        print(watch_line(event), file=out, flush=True)

    def waiting():
        print(f"새 Codex 세션을 기다립니다. 이제 {harness}에서 codex를 열고 질문하세요.\n"
              f"실행 대시보드: {shown}", file=out, flush=True)

    # One follower per harness: two (say, a second one-click start) would write the same session twice.
    (harness / "runtime-data" / "agent-office").mkdir(parents=True, exist_ok=True)
    lock = codex_follow.ob.Lock(harness / "runtime-data" / "agent-office" / ".codex-follow.lock", wait=0.0)
    try:
        lock.__enter__()
    except TimeoutError:
        raise OfficeError("이 하네스 폴더는 이미 다른 Codex 관찰이 따라가고 있습니다. 그 관찰 창을 쓰거나 닫은 뒤 다시 실행하세요.") from None
    try:
        result = codex_follow.follow(harness, Path(rollout) if rollout else None, latest=latest, once=once,
                                     until_complete=until_complete, max_seconds=max_minutes * 60, printer=printer, announce=announce,
                                     wait=wait, waiting=waiting)
    except codex_follow.FollowError as exc:
        raise OfficeError(str(exc)) from None
    finally:
        lock.__exit__(None, None, None)
    print(f"끝: 사건 {result['events_written']}개 기록 · 하위 에이전트 기록 {result['agent_threads']}개 · {result['stop_reason']}", file=out)
    return result["events_written"]


def codex_sessions(harness: Path, out=None) -> int:
    harness = check_harness(harness)
    out = out or sys.stdout
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import codex_follow
    sessions = codex_follow.list_sessions(harness)
    if not sessions:
        print("최근 3일 동안 이 하네스 폴더에서 연 Codex 세션 기록이 없습니다.", file=out)
    for i, s in enumerate(sessions, 1):
        print(f"{i}. {s.get('ts') or '시각 미확인'} · {s['id']} · 하위 에이전트 {s['agents']}개 · Codex {s.get('cli_version') or '버전 미확인'}\n   {s['path']}", file=out)
    return len(sessions)


def copy_page(harness: Path) -> list:
    """Each built page goes into the app folder and next to live.js (runtime-data/agent-office), where it reads the
    records. Returns the copies beside the records."""
    out = harness / "runtime-data" / "agent-office"
    out.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in (FACTORY, PAGE):
        source = HERE / name
        if not source.is_file():
            continue
        for folder in (harness.joinpath(*APP_REL), out):
            if source.resolve() != (folder / name).resolve():
                tmp = folder / f"{name}.{os.getpid()}.tmp"
                shutil.copyfile(source, tmp)
                os.replace(tmp, folder / name)
        copied.append(out / name)
    return copied


def page_path(harness: Path, page: str | None = None) -> Path:
    harness = check_harness(harness)
    name = default_page(harness, page)
    if not name:
        wanted = harness / "runtime-data" / "agent-office" / PAGES[page or "factory"]
        raise OfficeError(f"화면이 없습니다: {wanted}. 먼저 office.py install --claude <폴더>를 실행하세요.")
    return harness / "runtime-data" / "agent-office" / PAGES[name]


def open_page(harness: Path, launch=True, opener=None, page: str | None = None) -> str:
    path = page_path(harness, page)
    if launch:
        if opener is None:
            import webbrowser
            opener = webbrowser.open
        opener(path.as_uri())
    return f"{'실행 대시보드' if path.name == FACTORY else '사무실 화면'}: {path.as_uri()}"


def uninstall(harness: Path) -> str:
    harness = check_harness(harness)
    settings = harness.joinpath(*SETTINGS_REL)
    data = read_settings(settings)
    if not settings.exists():
        return "설정 파일이 없어 지울 훅이 없습니다."
    write_atomic(settings, json.dumps(merged(data, None), ensure_ascii=False, indent=2) + "\n")
    set_auto_open(harness, None)
    return f"{settings.relative_to(harness)}에서 관찰 훅만 지웠습니다. 기록·파일은 남겨 둡니다."


def status(harness: Path) -> dict:
    harness = check_harness(harness)
    settings = harness.joinpath(*SETTINGS_REL)
    data = read_settings(settings)
    app = harness.joinpath(*APP_REL)
    installed = digest(app / "observe.py") if (app / "observe.py").is_file() else None
    registered, shas = [], set()
    for event, groups in data.get("hooks", {}).items():
        for group in groups:
            for handler in (group.get("hooks") or []) if isinstance(group, dict) else []:
                if isinstance(handler, dict) and is_ours(handler.get("command")):
                    registered.append(event)
                    shas.add(command_sha(handler["command"]))
    out = harness / "runtime-data" / "agent-office"
    events = out / "events.jsonl"
    lines = events.read_text(encoding="utf-8").splitlines() if events.is_file() else []
    last = json.loads(lines[-1]) if lines else None
    errors = (out / "observe-error.log").read_text(encoding="utf-8").splitlines()[-5:] if (out / "observe-error.log").is_file() else []
    start = (out / "observe-start-error.log").read_text(encoding="utf-8").strip() if (out / "observe-start-error.log").is_file() else ""
    missing = [e for e in TOOL_EVENTS + OTHER_EVENTS if e not in registered]
    try:
        auto = json.loads((out / AUTO_OPEN).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        auto = {}
    return {"harness": str(harness), "registered": sorted(set(registered)), "missing_events": missing,
            "files_match_command": bool(installed) and shas == {installed}, "events_recorded": len(lines),
            "last_event": {k: last.get(k) for k in ("ts", "hook", "kind", "node", "op")} if last else None,
            "last_errors": errors, "start_error": start[:500] or None, "claude_version": claude_version(),
            "page": str(out / PAGE) if (out / PAGE).is_file() else None,
            "dashboard": str(out / FACTORY) if (out / FACTORY).is_file() else None,
            "open_on_prompt": isinstance(auto, dict) and auto.get("open_on_prompt") is True,
            "open_page": (auto.get("page", "office") if auto.get("page", "office") in PAGES else None)
            if isinstance(auto, dict) and auto.get("open_on_prompt") is True else None,
            "tested_claude_versions": list(TESTED_CLAUDE)}


def claude_version():
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace")
        return out.stdout.strip()[:60] or None
    except (OSError, subprocess.SubprocessError):
        return None


# --- trace (control-room TraceEvent shape) ----------------------------------------------------------------------------
def label_of(event: dict) -> str:
    kind, node, phase = event.get("kind"), event.get("node"), event.get("phase")
    who = ROLE_KO.get(node, SKILL_KO.get(node, node or ""))
    if kind == "skill_op":
        base = f"{SKILL_KO.get(node, node)} · {event.get('op')}"
        detail = event.get("detail") or {}
        if phase == "end" and isinstance(detail.get("accepted"), bool):
            verdict = "승인됨" if detail["accepted"] else "거절됨"
            extra = [x for x in (detail.get("reason"), detail.get("turn_status")) if x]
            return f"{base} {verdict}" + (f" ({', '.join(extra)})" if extra else "")
        return base + (" 실패" if phase == "fail" else " 끝" if phase == "end" else "")
    if kind == "delegate":
        if phase == "start":
            return f"{who}에 맡김"
        if phase == "end":
            return f"{who} 백그라운드로 시작" if (event.get("detail") or {}).get("background") else f"{who} 돌려받음"
        return f"{who} 실패"
    if kind == "subagent":
        if node == "other_subagent":
            kind_name = (event.get("detail") or {}).get("agent_type")
            return "Claude Code 보조 작업 " + ("시작" if phase == "start" else "끝") + (f" ({kind_name})" if kind_name else "")
        return f"{who} 시작" if phase == "start" else f"{who} 끝"
    if kind == "handback":
        return f"{who} 결과 돌려줌" + (" 완료" if phase == "end" else "")
    if kind == "handback_delivered":
        return "메인이 연구 결과 받음"
    if kind == "notification":
        return "작업 알림 받음"
    if kind == "skill_load":
        return f"{who} 지침 읽음"
    detail = event.get("detail") or {}
    if kind == "web":
        return f"웹 열람 · {detail['host']}" if detail.get("host") else "웹 검색"
    if kind == "shell":
        names = [PROGRAM_KO.get(p, p) for p in detail.get("programs") or [] if p != "other"]
        return "명령 실행" + (" · " + ", ".join(dict.fromkeys(names)) if names else "")
    if kind == "file":
        area = AREA_KO.get(detail.get("area"), "")
        if detail.get("skill"):
            area = f"{SKILL_KO.get(detail['skill'], detail['skill'])} 참고 문서"
        return f"{FILE_TOOL_KO.get(event.get('tool'), event.get('tool'))}" + (f" · {area}" if area else "")
    if kind == "tool":
        tool = event.get("tool") or ""
        name = tool.split("__")[-1] if tool.startswith("mcp__") else tool
        return TOOL_KO.get(name, f"{name or '도구'} 사용")
    return {"request": "새 질문", "turn_end": "답변 끝", "turn_cancelled": "turn 취소 관측 · 실행 결과 미확인", "session": "세션 " + ("시작" if phase == "start" else "끝")}.get(kind, kind or "")


# Tool names without a room of their own (Claude Code and Codex).
TOOL_KO = {"exec": "Codex 코드 실행 묶음", "wait": "실행 결과 기다림", "js": "JS 실행", "update_plan": "계획 갱신",
           "ToolSearch": "도구 찾기", "TodoWrite": "할 일 정리", "TaskCreate": "할 일 만들기", "TaskUpdate": "할 일 갱신"}


PROGRAM_KO = {
    "product_doctor": "설치 점검", "ls": "파일 목록 보기", "dir": "파일 목록 보기", "get-childitem": "파일 목록 보기",
    "cat": "파일 읽기", "type": "파일 읽기", "get-content": "파일 읽기", "head": "파일 앞부분 보기", "tail": "파일 끝부분 보기",
    "find": "파일 찾기", "grep": "내용 찾기", "rg": "내용 찾기", "select-string": "내용 찾기", "wc": "줄 수 세기",
    "measure-object": "개수 세기", "pwd": "위치 확인", "cd": "폴더 이동", "set-location": "폴더 이동", "echo": "글자 출력",
    "write-output": "글자 출력", "mkdir": "폴더 만들기", "new-item": "파일·폴더 만들기", "cp": "파일 복사", "copy-item": "파일 복사",
    "mv": "파일 옮기기", "move-item": "파일 옮기기", "rm": "파일 지우기", "remove-item": "파일 지우기", "python": "파이썬 실행",
    "python3": "파이썬 실행", "py": "파이썬 실행", "uv": "uv 실행", "git": "git", "sed": "글자 바꾸기", "awk": "글자 처리",
    "jq": "JSON 보기", "curl": "웹 받아오기", "wget": "웹 받아오기", "invoke-webrequest": "웹 받아오기", "sort": "정렬",
    "uniq": "중복 정리", "node": "node 실행", "npm": "npm 실행", "npx": "npm 실행", "test-path": "경로 확인",
    "get-item": "파일 정보 보기", "out-file": "파일 쓰기", "set-content": "파일 쓰기",
}
AREA_KO = {"exports": "결과 내보내기", "web_evidence": "웹 근거 보관", "catalogs": "근거 목록", "deliverables": "보고서",
           "runtime": "작업 기록", "skills": "Skill 폴더", "agents": "에이전트 설명", "docs": "문서", "data": "자료",
           "tools": "도구 코드", "web": "화면 파일", "harness": "하네스 폴더", "outside": "하네스 밖"}
FILE_TOOL_KO = {"Read": "파일 읽기", "Write": "파일 쓰기", "Edit": "파일 고치기", "NotebookEdit": "노트 고치기",
                "Grep": "내용 찾기", "Glob": "파일 찾기"}


def to_trace(events: list) -> dict:
    """Recorded hook events in the TraceEvent fields of the teammate control room, plus when and on what basis."""
    times = [datetime.fromisoformat(e["ts"].replace("Z", "+00:00")) for e in events if e.get("ts")]
    start = min(times) if times else None
    out = []
    for e in events:
        at = (datetime.fromisoformat(e["ts"].replace("Z", "+00:00")) - start).total_seconds() if start and e.get("ts") else 0
        actor, node, kind, phase = e.get("actor") or "main", e.get("node") or "main", e.get("kind"), e.get("phase")
        source, target = actor, node
        background = bool((e.get("detail") or {}).get("background"))
        if kind == "delegate" and phase == "end" and not background:
            source, target = node, actor
        if kind == "handback":
            source, target = actor, "main"
        status = {"start": "active", "end": "done", "fail": "error"}.get(phase, "done")
        if kind == "delegate" and background:
            status = "active"  # launched in the background; the return is the later handback / SubagentStop
        out.append({"id": e.get("id"), "at": round(at, 3), "kind": kind, "source": source, "target": target,
                    "label": label_of(e), "detail": (e.get("op") or "") if kind == "skill_op" else "", "status": status,
                    "ts": e.get("ts"), "basis": e.get("basis"), "call": e.get("call"), "session": e.get("session")})
    duration = max((x["at"] for x in out), default=0)
    sessions = sorted({e.get("session") for e in events if e.get("session")})
    return {"mode": "observed", "title": "관측 기록 · Claude Code 훅", "sessionId": sessions[-1] if sessions else None,
            "sessions": sessions, "duration": duration, "events": out,
            "warnings": ["훅이 받은 시각이며 모델 내부 시각이 아닙니다.",
                         "Skill 작업은 명령 경로로 알아낸 것(command_based_mapping)이고 실행 성공·의미 검토의 증거가 아닙니다."],
            "metrics": {"evidence": None, "tokens": None}}


def trace(harness: Path, out_path: Path) -> str:
    events_file = harness.resolve() / "runtime-data" / "agent-office" / "events.jsonl"
    events = []
    if events_file.is_file():
        for line in events_file.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    write_atomic(out_path, json.dumps(to_trace(events), ensure_ascii=False, indent=1) + "\n")
    return f"{len(events)}개 사건을 {out_path}에 썼습니다."


def watch_line(event: dict) -> str:
    """One recorded event as a short Korean line with local time, for `office.py watch`."""
    try:
        when = datetime.fromisoformat(event["ts"].replace("Z", "+00:00")).astimezone().strftime("%H:%M:%S")
    except (KeyError, ValueError):
        when = "--:--:--"
    actor = ROLE_KO.get(event.get("actor"), event.get("actor") or "")
    extra = (event.get("detail") or {}).get("duration_ms")
    basis = {"command_based_mapping": " (명령으로 추정)", "instruction_loaded": " (지침)"}.get(event.get("basis"), "")
    took = f" · {extra / 1000:.1f}초" if isinstance(extra, (int, float)) else ""
    return f"{when}  [{actor}] {label_of(event)}{basis}{took}"


def watch(harness: Path, once=False, interval=0.5, out=None) -> int:
    """Prints recorded events as they arrive (read only). Ctrl+C stops it; the session is not touched."""
    import time
    out = out or sys.stdout
    events_file = check_harness(harness) / "runtime-data" / "agent-office" / "events.jsonl"
    seen = 0
    if not once:
        print(f"기록을 지켜봅니다: {events_file} (멈추기: Ctrl+C)", file=out, flush=True)
    try:
        while True:
            lines = events_file.read_text(encoding="utf-8").splitlines() if events_file.is_file() else []
            if len(lines) < seen:  # rolled over to a new file
                seen = 0
            for line in lines[seen:]:
                try:
                    print(watch_line(json.loads(line)), file=out, flush=True)
                except ValueError:
                    continue
            seen = len(lines)
            if once:
                return seen
            time.sleep(interval)
    except KeyboardInterrupt:
        return seen


# --- selftest -------------------------------------------------------------------------------------------------------
SELFTEST_PAYLOADS = [
    {"hook_event_name": "SessionStart", "session_id": "selftest", "source": "startup"},
    {"hook_event_name": "UserPromptSubmit", "session_id": "selftest", "prompt": "SELFTEST-SECRET-PROMPT"},
    {"hook_event_name": "PreToolUse", "session_id": "selftest", "tool_name": "Bash", "tool_use_id": "toolu_1",
     "tool_input": {"command": "uv run python .claude/skills/evidence-retrieval/scripts/run.py retrieve_reviews --input SELFTEST-SECRET.json"}},
    {"hook_event_name": "PostToolUse", "session_id": "selftest", "tool_name": "Bash", "tool_use_id": "toolu_1",
     "tool_input": {"command": "uv run python .claude/skills/evidence-retrieval/scripts/run.py retrieve_reviews --input x.json"},
     "tool_response": {"stdout": "{\"ok\": true, \"data\": \"SELFTEST-SECRET-OUTPUT\"}"}},
    {"hook_event_name": "PreToolUse", "session_id": "selftest", "tool_name": "Agent", "tool_use_id": "toolu_2",
     "tool_input": {"subagent_type": "product-review-researcher", "prompt": "SELFTEST-SECRET-PROMPT"}},
    {"hook_event_name": "Stop", "session_id": "selftest"},
]


def selftest() -> dict:
    """Runs the real hook command (the same one install writes) against a temporary harness copy."""
    with tempfile.TemporaryDirectory(prefix="agent-office-selftest-") as tmp:
        harness = Path(tmp) / "harness"
        (harness / ".claude").mkdir(parents=True)
        (harness / "product-install.json").write_text("{}", encoding="utf-8")
        install(harness)
        data = read_settings(harness.joinpath(*SETTINGS_REL))
        command = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(harness))
        results = []
        for payload in SELFTEST_PAYLOADS:
            proc = subprocess.run(command, shell=True, input=json.dumps(payload).encode("utf-8"), capture_output=True,
                                  cwd=harness, env=env, timeout=120)
            results.append({"exit": proc.returncode, "stdout": len(proc.stdout), "stderr": len(proc.stderr)})
        events_file = harness / "runtime-data" / "agent-office" / "events.jsonl"
        text = events_file.read_text(encoding="utf-8") if events_file.is_file() else ""
        lines = [json.loads(line) for line in text.splitlines()]
        ok = (len(lines) == len(SELFTEST_PAYLOADS) and all(r["exit"] == 0 and r["stdout"] == 0 for r in results)
              and "SELFTEST-SECRET" not in text and (harness / "runtime-data" / "agent-office" / "live.js").is_file()
              and any(e["kind"] == "skill_op" and e["op"] == "retrieve_reviews" for e in lines)
              and any(e["kind"] == "delegate" and e["node"] == "product_review_researcher" for e in lines))
        return {"ok": ok, "events": [f"{e['hook']}:{e['kind']}:{e['node']}" for e in lines], "runs": results,
                "note": "임시 하네스 사본과 합성 훅 입력으로 실제 훅 명령을 실행했습니다. Claude Code·모델·업무 도구는 쓰지 않았습니다."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LG AX agent office: 관찰 훅 설치·제거·확인과 기록 변환")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "uninstall", "status"):
        p = sub.add_parser(name)
        p.add_argument("--claude", type=Path, required=True, metavar="HARNESS", help="설치된 하네스 폴더 (Claude Code)")
        if name == "install":
            p.add_argument("--open-on-prompt", action="store_true", help="세션의 첫 질문 때 실행 대시보드를 브라우저로 한 번 열기")
            p.add_argument("--page", choices=tuple(PAGES), help="자동으로 열 화면 (기본: factory = 공장 관제, 없으면 office)")
    p = sub.add_parser("open", help="실행 대시보드(공장 관제, 없으면 3D 사무실)를 기본 브라우저로 열기")
    p.add_argument("--claude", type=Path, required=True, metavar="HARNESS")
    p.add_argument("--page", choices=tuple(PAGES), help="factory = 공장 관제, office = 3D 사무실")
    p.add_argument("--print", action="store_true", help="열지 않고 주소만 출력")
    p = sub.add_parser("codex", help="Codex 세션 기록(rollout)을 따라가며 사무실 기록으로 옮기기")
    p.add_argument("--harness", type=Path, required=True)
    pick = p.add_mutually_exclusive_group(required=True)
    pick.add_argument("--rollout", type=Path, help="메인 세션의 rollout-*.jsonl 파일")
    pick.add_argument("--latest", action="store_true", help="이 하네스 폴더에서 연 가장 최근 Codex 세션")
    pick.add_argument("--wait", action="store_true", help="이 명령 뒤에 시작되는 새 Codex 세션을 기다렸다가 따라가기")
    p.add_argument("--once", action="store_true", help="지금까지의 기록만 옮기고 끝내기 (지난 세션 재생용)")
    p.add_argument("--until-complete", action="store_true", help="답변이 끝나면 멈추기")
    p.add_argument("--open", action="store_true", help="세션의 첫 기록이 들어오면 실행 대시보드를 브라우저로 한 번 열기")
    p.add_argument("--page", choices=tuple(PAGES), help="--open이 열 화면 (기본: factory, 없으면 office)")
    p.add_argument("--max-minutes", type=float, default=180.0)
    p = sub.add_parser("codex-sessions", help="이 하네스 폴더에서 연 최근 Codex 세션 목록")
    p.add_argument("--harness", type=Path, required=True)
    p = sub.add_parser("watch")
    p.add_argument("--claude", type=Path, required=True, metavar="HARNESS")
    p.add_argument("--once", action="store_true", help="지금까지의 기록만 출력하고 끝내기")
    p = sub.add_parser("trace")
    p.add_argument("harness", type=Path)
    p.add_argument("--out", type=Path, required=True)
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if args.command == "install":
            print(install(args.claude, open_on_prompt=args.open_on_prompt, page=args.page))
        elif args.command == "uninstall":
            print(uninstall(args.claude))
        elif args.command == "status":
            print(json.dumps(status(args.claude), ensure_ascii=False, indent=1))
        elif args.command == "codex":
            codex(args.harness, rollout=args.rollout, latest=args.latest, once=args.once,
                  until_complete=args.until_complete, max_minutes=args.max_minutes, wait=args.wait, open_page_once=args.open,
                  page=args.page)
        elif args.command == "codex-sessions":
            codex_sessions(args.harness)
        elif args.command == "open":
            print(open_page(args.claude, launch=not args.print, page=args.page))
        elif args.command == "watch":
            watch(args.claude, once=args.once)
        elif args.command == "trace":
            print(trace(args.harness, args.out))
        else:
            result = selftest()
            print(json.dumps(result, ensure_ascii=False, indent=1))
            return 0 if result["ok"] else 1
    except OfficeError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
