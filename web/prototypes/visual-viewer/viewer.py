"""시각자료 뷰어 설치·해제·열기 (Claude Code·Codex CLI 공용, 표준 라이브러리만 사용).

    uv run python web/prototypes/visual-viewer/viewer.py install --claude <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py install --codex <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py uninstall --claude|--codex|--both <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py open --latest [<하네스 폴더>]
    uv run python web/prototypes/visual-viewer/viewer.py status [<하네스 폴더>]

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
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_view  # noqa: E402
import hook  # noqa: E402

APP_REL = ("web", "prototypes", "visual-viewer")
APP_FILES = ("index.html", "build_view.py", "hook.py", "viewer.py", "README.md")
# uv: 작업 폴더의 .python-version·uv.toml·pyproject를 따르지 않고 3.12를 쓰며 Python을 내려받지 않는다.
UV_PREFIX = "uv run --no-project --no-config --python 3.12 --no-python-downloads --quiet python -I -B -c"
# Python 코드 부분은 Git Bash·PowerShell·cmd 어디서나 같게 해석되도록 $ % ! ` \ ^ & | < > 를 쓰지 않는다.
# hook.py의 SHA-256이 맞을 때만 읽은 바이트 그대로 실행한다. 없거나 다르면 실행하지 않고 로그에 한 줄 남긴다.
_BASE = {"claude": "os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()", "codex": "os.getcwd()"}
_CODE = ("import hashlib,os,time;d={base};p=os.path.join(d,'web','prototypes','visual-viewer','hook.py');"
         "l=os.path.join(d,'runtime-data','visual-viewer','hook-error.log');"
         "b=open(p,'rb').read() if os.path.isfile(p) else b'';"
         "exec(compile(b,p,'exec'),{{'__name__':'__main__','__file__':p}}) if hashlib.sha256(b).hexdigest()=='{digest}' "
         "else os.path.isdir(os.path.dirname(l)) and open(l,'a').write("
         "time.ctime()+' hook.py is missing or differs from the installed fingerprint. Run viewer.py install again.'+chr(10))")
LOG_POSIX = "runtime-data/visual-viewer"
LOG_WINDOWS = r"runtime-data\visual-viewer"
START_LOG = "hook-start-error.log"  # Codex 셸이 쓰는 uv·Python 시작 오류(마지막 실행분만)
TARGETS = {
    "claude": {"file": (".claude", "settings.local.json"), "event": "PostToolUse", "matcher": "Bash|PowerShell",
               "name": "Claude Code", "async": True, "timeout": 60, "keep_positions": False},
    # codex-cli 0.146은 SessionEnd 외의 async 훅을 "async hooks are not supported yet"로 건너뛴다. 동기로 둔다.
    # 신뢰 키가 `이벤트:묶음 번호:처리기 번호` 위치라서 다른 훅의 위치를 지킨다.
    "codex": {"file": (".codex", "hooks.json"), "event": "PostToolUse", "matcher": "Bash",
              "name": "Codex CLI", "async": False, "timeout": 30, "keep_positions": True},
}
PLACEHOLDER = {"type": "command", "command": ""}  # Codex는 빈 명령을 건너뛰지만 그 자리 번호는 센다
HEX64 = re.compile(r"[0-9a-f]{64}")


class ViewerError(Exception):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def app_digests(app: Path) -> dict:
    return {"hook": digest(app / "hook.py"), "build_view": digest(app / "build_view.py"), "index": digest(app / "index.html")}


def hook_code(source: str, digests: dict) -> str:
    return _CODE.format(base=_BASE[source], digest=digests["hook"])


def hook_command(source: str, digests: dict) -> str:
    """셸에 상관없는 핵심 명령. Claude는 이것을 그대로 쓴다(Git Bash·PowerShell은 작업 폴더의 실행 파일을 찾지 않는다)."""
    return f'{UV_PREFIX} "{hook_code(source, digests)}" {source} {digests["build_view"]} {digests["index"]}'


def codex_commands(digests: dict) -> dict:
    """Codex는 동기 훅이라 uv·Python이 시작조차 못 해도 exit 0·무출력이어야 한다(exit 2면 셸 결과를 바꿔 버린다).

    셸의 stderr(uv·Python 시작 오류)는 hook-error.log가 아닌 hook-start-error.log에 매번 덮어쓴다. Windows cmd의
    리다이렉트는 파일을 쓰기 공유 없이 열어 두므로, 같은 파일이면 hook.py의 로그 쓰기가 막힌다.
    - command(macOS·Linux, sh -c): 출력은 버리고 시작 오류만 남긴 뒤 exit 0.
    - commandWindows(COMSPEC /C, 작업 폴더 = 하네스): cmd는 작업 폴더의 uv.cmd·uv.bat을 PATH보다 먼저 찾으므로
      NoDefaultCurrentDirectoryInExePath를 켜서 막는다. 출력은 버리고 시작 오류만 남긴 뒤 exit /b 0.
    """
    core = hook_command("codex", digests)
    return {
        "command": f"mkdir -p {LOG_POSIX} 2>/dev/null; {core} >/dev/null 2>{LOG_POSIX}/{START_LOG}; exit 0",
        "commandWindows": (f"set NoDefaultCurrentDirectoryInExePath=1&& (if not exist {LOG_WINDOWS}\\ md {LOG_WINDOWS}) & "
                           f"{core} 1>nul 2>{LOG_WINDOWS}\\{START_LOG} & exit /b 0"),
    }


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
    return "visual-viewer" in text and "hook.py" in text


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
        notes.append(f"다른 이벤트·matcher에 있던 이 뷰어 항목 {len(positions)}개를 {target['event']}({target['matcher']})로 옮겼습니다.")
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
    groups.append({"matcher": target["matcher"], "hooks": [new]})
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
        hexes = HEX64.findall(item.get(key) or "")
        if hexes:
            digests.append(dict(zip(("hook", "build_view", "index"), hexes)) if len(hexes) == 3 else None)
    return {"registered": bool(placed), "misplaced": len(found) - len(placed), "event": event, "matcher": matcher,
            "async": bool(item.get("async")), "timeout": item.get("timeout"), "digests": digests}


# ---------------------------------------------------------------- harness

def is_dev_repo(path: Path) -> bool:
    """개발 레포(Git checkout·ZIP 내려받기·git archive 모두). 제품 하네스에는 dev-harness 폴더가 없다."""
    return (path / "dev-harness").is_dir()


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
        how, notes = place_ours(config, path, source, handler(source, digests))
        save_config(path, config)
        rel = "/".join(target["file"])
        print(f"[{target['name']}] {rel}에 PostToolUse({target['matcher']}) 훅을 {how}했습니다. "
              f"다른 훅 {count_others(config)}개는 내용과 위치를 그대로 둡니다.")
        for note in notes:
            print(f"  {note}")
        if source == "claude":
            print("  다음: 이 하네스 폴더에서 Claude Code를 새로 열고 질문하세요. export가 저장되면 브라우저가 한 번 열립니다.")
        else:
            print("  다음: 이 하네스 폴더에서 `codex --search`를 열고 `/hooks`에서 이 훅을 검토·신뢰(trust)하세요.")
            print("        신뢰하기 전에는 실행되지 않습니다. 뷰어 파일을 갱신하면 명령의 지문이 바뀌어 다시 신뢰해야 합니다.")
            print("        Codex에서는 동기 훅이라 셸 명령마다 약 0.65초가 더 걸립니다. 신뢰 우회 옵션은 쓰지 마세요.")
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
            if all(d == digests for d in info.get("digests") or [None]):
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
                      "insights_file": summary.get("insights_file"), "warnings": summary["warnings"]})
        latest = hook.newest_export(paths)
        if in_exports and latest is not None and hook.export_key(latest) == key:
            state.update({"last_key": key, "last_export": export.name})
            state.pop("failed_key", None)
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


def cmd_status(args) -> int:
    harness = resolve_harness(args.harness)
    paths = hook.Paths(str(harness))
    app = harness.joinpath(*APP_REL)
    report = {"harness": str(harness), "app_files": {n: (app / n).is_file() for n in APP_FILES}}
    current = app_digests(app) if all((app / n).is_file() for n in ("hook.py", "build_view.py", "index.html")) else None
    for source, target in TARGETS.items():
        path = harness.joinpath(*target["file"])
        try:
            info = registered(load_config(path), source)
        except ViewerError as exc:
            info = {"registered": False, "error": str(exc)}
        info["file"] = "/".join(target["file"])
        if "digests" in info:
            info["files_match_command"] = bool(current) and bool(info["digests"]) and all(d == current for d in info["digests"])
            del info["digests"]
        report[source] = info
    layers = codex_feature_layers(harness)
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
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


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
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    commands = {"install": cmd_install, "uninstall": cmd_uninstall, "open": cmd_open, "status": cmd_status}
    try:
        return commands[args.command](args)
    except ViewerError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
