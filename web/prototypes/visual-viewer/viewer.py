"""시각자료 뷰어 설치·해제·열기 (Claude Code·Codex CLI 공용, 표준 라이브러리만 사용).

    uv run python web/prototypes/visual-viewer/viewer.py install --claude <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py install --codex <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py uninstall --claude|--codex|--both <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py open --latest [<하네스 폴더>]
    uv run python web/prototypes/visual-viewer/viewer.py status [<하네스 폴더>]

- install: 뷰어 파일을 `<하네스>/web/prototypes/visual-viewer/`에 복사하고(이미 그 자리면 생략), 훅을
  `.claude/settings.local.json` 또는 `.codex/hooks.json`에 합친다. 기존 설정·다른 훅은 지우거나 옮기지 않는다.
  훅 명령에는 사용자별 절대 경로가 없고, 설치한 hook.py·build_view.py·index.html의 SHA-256이 들어간다.
  그래서 파일이 바뀌면 훅이 실행하지 않고, Codex에서는 명령이 바뀌어 다시 신뢰해야 한다.
- uninstall: 이 뷰어의 훅 항목만 지운다. 뷰어 파일과 runtime-data의 화면·insights는 남긴다.
- open --latest: 가장 최근 export로 화면을 다시 만들고 브라우저로 연다(훅이 없거나 놓쳤을 때).
- 업무·모델·Tool을 실행하지 않는다. 개발 레포에는 설치하지 않는다.
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
# 훅 명령은 Git Bash·PowerShell·cmd 어디서나 같게 해석되도록 $ % ! ` \ ^ & | < > 를 쓰지 않는다.
# hook.py의 SHA-256이 맞을 때만 읽은 바이트 그대로 실행하고, 없거나 다르면 조용히 끝난다.
_BASE = {"claude": "os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()", "codex": "os.getcwd()"}
_CODE = ("import hashlib,os;p=os.path.join({base},'web','prototypes','visual-viewer','hook.py');"
         "b=open(p,'rb').read() if os.path.isfile(p) else b'';"
         "hashlib.sha256(b).hexdigest()=='{digest}' and exec(compile(b,p,'exec'),{{'__name__':'__main__','__file__':p}})")
TARGETS = {
    "claude": {"file": (".claude", "settings.local.json"), "event": "PostToolUse", "matcher": "Bash|PowerShell",
               "name": "Claude Code", "async": True, "timeout": 60},
    # codex-cli 0.146은 SessionEnd 외의 async 훅을 "async hooks are not supported yet"로 건너뛴다. 동기로 둔다.
    "codex": {"file": (".codex", "hooks.json"), "event": "PostToolUse", "matcher": "Bash",
              "name": "Codex CLI", "async": False, "timeout": 30},
}
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
    return f'{UV_PREFIX} "{hook_code(source, digests)}" {source} {digests["build_view"]} {digests["index"]}'


def handler(source: str, digests: dict) -> dict:
    target = TARGETS[source]
    value = {"type": "command", "command": hook_command(source, digests), "timeout": target["timeout"]}
    if target["async"]:
        value["async"] = True
    return value


def is_ours(item) -> bool:
    command = item.get("command") if isinstance(item, dict) else None
    return isinstance(command, str) and "visual-viewer" in command and "hook.py" in command


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


def place_ours(config: dict, path: Path, source: str, new: dict) -> str:
    """이 뷰어 항목을 넣는다. Codex 신뢰 키는 `이벤트:묶음 번호:처리기 번호` 위치라 다른 훅의 위치를 바꾸지 않는다.

    1) 기존 항목이 있으면 그 자리에서 바꾼다. 2) 해제 때 남긴 빈 묶음(같은 matcher)이 있으면 그 자리를 다시 쓴다.
    3) 둘 다 없으면 이벤트 목록 맨 끝에 붙인다.
    """
    target = TARGETS[source]
    table = config.setdefault("hooks", {})
    hooks_table(config, path)
    positions = our_positions(config)
    if positions:
        event, gi, hi = positions[0]
        table[event][gi]["hooks"][hi] = new
        for event2, gi2, hi2 in reversed(positions[1:]):  # 중복 항목은 지운다(같은 묶음 안 뒤쪽부터)
            del table[event2][gi2]["hooks"][hi2]
        return "갱신"
    groups = table.setdefault(target["event"], [])
    for group in groups:
        if isinstance(group, dict) and group.get("matcher") == target["matcher"] and group.get("hooks") == []:
            group["hooks"] = [new]
            return "추가(이전 자리)"
    groups.append({"matcher": target["matcher"], "hooks": [new]})
    return "추가"


def remove_ours(config: dict, path: Path) -> int:
    """이 뷰어의 처리기만 지운다. 뒤에 다른 묶음이 있으면 빈 묶음을 자리표시로 남겨 그 훅들의 위치(신뢰 키)를 지킨다."""
    if "hooks" not in config:
        return 0
    table = hooks_table(config, path)
    removed = 0
    for event in list(table):
        groups = table[event]
        for gi in range(len(groups) - 1, -1, -1):
            group = groups[gi]
            items = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(items, list) or not any(is_ours(h) for h in items):
                continue
            kept = [h for h in items if not is_ours(h)]
            removed += len(items) - len(kept)
            if kept:
                group["hooks"] = kept
            elif gi == len(groups) - 1:
                del groups[gi]
            else:
                group["hooks"] = []
        if not groups:
            del table[event]
    if not table:
        del config["hooks"]
    return removed


def count_others(config: dict) -> int:
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    return sum(1 for groups in table.values() if isinstance(groups, list) for g in groups if isinstance(g, dict)
               for h in (g.get("hooks") if isinstance(g.get("hooks"), list) else []) if not is_ours(h))


def registered(config: dict, source: str) -> dict:
    """등록된 이 뷰어 명령과 그 명령에 든 파일 지문."""
    target = TARGETS[source]
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    for group in table.get(target["event"]) or []:
        for item in (group.get("hooks") or []) if isinstance(group, dict) else []:
            if is_ours(item):
                found = HEX64.findall(item.get("command") or "")
                return {"registered": True, "async": bool(item.get("async")), "timeout": item.get("timeout"),
                        "digests": dict(zip(("hook", "build_view", "index"), found)) if len(found) == 3 else None}
    return {"registered": False}


# ---------------------------------------------------------------- harness

def is_dev_repo(path: Path) -> bool:
    return (path / "dev-harness").is_dir() and (path / ".git").exists()


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


def set_baseline(paths: hook.Paths) -> str | None:
    """설치 순간의 최신 export를 이미 본 것으로 둔다. 다시 설치할 때도(남은 상태가 있어도) 매번 한다.

    화면을 만든 것(built_key)과는 따로 기록하므로 status가 그리지 않은 화면을 최신이라고 하지 않는다.
    """
    latest = hook.newest_export(paths)
    if latest is None:
        return None
    state = hook.read_state(paths)
    key = hook.export_key(latest)
    if state.get("last_key") == key:
        return None
    state.update({"last_key": key, "last_export": latest.name, "baseline": True})
    state.pop("failed_key", None)
    hook.write_state(paths, state)
    return latest.name


def codex_feature_layers(harness: Path) -> list[dict]:
    """Codex의 [features] hooks(옛 이름 codex_hooks) 설정을 하네스·사용자 config.toml에서 읽는다.

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
                features = tomllib.loads(path.read_text(encoding="utf-8-sig")).get("features") or {}
                value = features.get("hooks", features.get("codex_hooks"))
                entry["hooks"] = value if isinstance(value, bool) else None
            except (OSError, ValueError, UnicodeDecodeError) as exc:
                entry["error"] = str(exc)[:200]
        layers.append(entry)
    return layers


def codex_hooks_disabled(harness: Path) -> bool:
    return any(layer["hooks"] is False for layer in codex_feature_layers(harness))


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
    for source in sources:  # 모두 읽을 수 있을 때만 바꾼다
        path = harness.joinpath(*TARGETS[source]["file"])
        configs[source] = (path, load_config(path))
        if "hooks" in configs[source][1]:
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
        how = place_ours(config, path, source, handler(source, digests))
        save_config(path, config)
        rel = "/".join(target["file"])
        print(f"[{target['name']}] {rel}에 PostToolUse({target['matcher']}) 훅을 {how}했습니다. "
              f"다른 훅 {count_others(config)}개는 내용과 위치를 그대로 둡니다.")
        if source == "claude":
            print("  다음: 이 하네스 폴더에서 Claude Code를 새로 열고 질문하세요. export가 저장되면 브라우저가 한 번 열립니다.")
        else:
            print("  다음: 이 하네스 폴더에서 `codex --search`를 열고 `/hooks`에서 이 훅을 검토·신뢰(trust)하세요.")
            print("        신뢰하기 전에는 실행되지 않습니다. 뷰어 파일을 갱신하면 명령의 지문이 바뀌어 다시 신뢰해야 합니다.")
            print("        Codex에서는 동기 훅이라 셸 명령마다 약 0.5초가 더 걸립니다. 신뢰 우회 옵션은 쓰지 마세요.")
            off = [layer for layer in codex_feature_layers(harness) if layer["hooks"] is False]
            for layer in off:
                print(f"  주의: {layer['path']}의 [features] hooks = false라 Codex가 훅을 실행하지 않습니다.")
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
        removed = remove_ours(config, path)
        if not removed:
            print(f"[{target['name']}] 이 뷰어의 훅이 없습니다.")
            continue
        if source == "codex" and not config:
            path.unlink()  # 이 뷰어의 훅만 있던 파일
            print(f"[{target['name']}] 훅 {removed}개를 지우고 빈 {'/'.join(target['file'])}를 삭제했습니다.")
        else:
            save_config(path, config)
            print(f"[{target['name']}] 훅 {removed}개를 지웠습니다. 다른 훅의 내용과 위치(빈 자리표시 포함)는 그대로 둡니다.")
    print("뷰어 파일과 runtime-data/visual-viewer의 화면·insights는 남겨 둡니다(필요 없으면 직접 지우세요).")
    return 0


def cmd_open(args) -> int:
    harness = resolve_harness(args.harness)
    paths = hook.Paths(str(harness))
    latest = None
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
    except (OSError, ValueError, KeyError, TypeError, SystemExit) as exc:
        raise ViewerError(f"화면을 만들지 못했습니다({export.name}): {type(exc).__name__}: {exc}") from exc
    if latest is not None:
        state = hook.read_state(paths)
        key = hook.export_key(latest)
        state.update({"last_key": key, "built_key": key, "last_export": export.name, "insights": summary["insights"],
                      "insights_file": summary.get("insights_file"), "warnings": summary["warnings"]})
        state.pop("failed_key", None)
        state.pop("baseline", None)
        hook.write_state(paths, state)
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
        if info.get("registered"):
            info["files_match_command"] = bool(current) and info.get("digests") == current
            info.pop("digests", None)
        report[source] = info
    report["codex_features"] = codex_feature_layers(harness)
    report["codex_hooks_disabled"] = any(layer["hooks"] is False for layer in report["codex_features"])
    report["codex_features_note"] = "관리자 requirements.toml·managed 설정은 확인하지 않았습니다."
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
    try:
        lines = Path(paths.error_log).read_text(encoding="utf-8").strip().splitlines()
        report["last_error"] = next((line for line in reversed(lines) if line[:2].isdigit()), lines[-1] if lines else None)
    except (OSError, UnicodeDecodeError):
        report["last_error"] = None
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
    try:
        sys.stdout.reconfigure(encoding="utf-8")
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
