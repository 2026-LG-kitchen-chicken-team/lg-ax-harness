"""시각자료 뷰어 설치·해제·열기 (Claude Code·Codex CLI 공용, 표준 라이브러리만 사용).

    uv run python web/prototypes/visual-viewer/viewer.py install --claude <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py install --codex <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py uninstall --claude|--codex|--both <하네스 폴더>
    uv run python web/prototypes/visual-viewer/viewer.py open --latest [<하네스 폴더>]
    uv run python web/prototypes/visual-viewer/viewer.py status [<하네스 폴더>]

- install: 뷰어 파일을 `<하네스>/web/prototypes/visual-viewer/`에 복사하고(이미 그 자리면 생략), 훅을
  `.claude/settings.local.json` 또는 `.codex/hooks.json`에 합친다. 기존 설정·다른 훅은 지우지 않는다.
  훅 명령에는 사용자별 절대 경로를 넣지 않고 하네스 기준 상대 경로만 쓴다.
- uninstall: 이 뷰어의 훅 항목만 지운다. 뷰어 파일과 runtime-data의 화면·insights는 남긴다.
- open --latest: 가장 최근 export로 화면을 다시 만들고 브라우저로 연다(훅이 없거나 놓쳤을 때).
- 업무·모델·Tool을 실행하지 않는다. 하네스 폴더를 주지 않으면 이 파일이 들어 있는 하네스를 쓴다.
"""

from __future__ import annotations

import argparse
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
HOOK_TIMEOUT = 60
# 훅 명령은 Git Bash·PowerShell·cmd 어디서나 같게 해석되도록 $ % ! ` \ ^ & | < > 를 쓰지 않는다.
# 스크립트가 없으면(뷰어를 지운 경우) 조용히 끝난다. Claude는 CLAUDE_PROJECT_DIR, Codex는 세션 cwd(하네스 폴더) 기준이다.
_FIND = "os.path.join({base},'web','prototypes','visual-viewer','hook.py')"
_RUN = "import os,runpy;p=" + _FIND + ";os.path.isfile(p) and runpy.run_path(p,run_name='__main__')"
HOOK_CODE = {
    "claude": _RUN.format(base="os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()"),
    "codex": _RUN.format(base="os.getcwd()"),
}
TARGETS = {
    "claude": {"file": (".claude", "settings.local.json"), "event": "PostToolUse", "matcher": "Bash|PowerShell", "name": "Claude Code"},
    "codex": {"file": (".codex", "hooks.json"), "event": "PostToolUse", "matcher": "Bash", "name": "Codex CLI"},
}


class ViewerError(Exception):
    pass


def hook_command(source: str) -> str:
    return f'uv run --no-project --quiet python -I -B -c "{HOOK_CODE[source]}" {source}'


def handler(source: str) -> dict:
    return {"type": "command", "command": hook_command(source), "timeout": HOOK_TIMEOUT, "async": True}


def is_ours(item) -> bool:
    command = item.get("command") if isinstance(item, dict) else None
    return isinstance(command, str) and "visual-viewer" in command and "hook.py" in command


# ---------------------------------------------------------------- settings files

def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
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


def remove_ours(config: dict, path: Path) -> int:
    """이 뷰어의 훅 처리기만 지우고, 비게 된 묶음·이벤트·hooks 키를 정리한다. 지운 개수를 돌려준다."""
    if "hooks" not in config:
        return 0
    table = hooks_table(config, path)
    removed = 0
    for event in list(table):
        groups = []
        for group in table[event]:
            items = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(items, list):
                groups.append(group)
                continue
            kept = [h for h in items if not is_ours(h)]
            removed += len(items) - len(kept)
            if kept:
                groups.append({**group, "hooks": kept})
            elif len(items) == len(kept):
                groups.append(group)  # 원래 비어 있던 묶음은 그대로 둔다
        if groups:
            table[event] = groups
        else:
            del table[event]
    if not table:
        del config["hooks"]
    return removed


def count_entries(config: dict) -> int:
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    return sum(len(g.get("hooks") or []) for groups in table.values() if isinstance(groups, list)
               for g in groups if isinstance(g, dict) and isinstance(g.get("hooks"), list))


def registered(config: dict, source: str) -> bool:
    target = TARGETS[source]
    table = config.get("hooks") if isinstance(config.get("hooks"), dict) else {}
    for group in table.get(target["event"]) or []:
        if isinstance(group, dict) and any(isinstance(h, dict) and h.get("command") == hook_command(source) for h in group.get("hooks") or []):
            return True
    return False


# ---------------------------------------------------------------- harness

def resolve_harness(value: str | None) -> Path:
    harness = Path(value).expanduser().resolve() if value else HERE.parents[2]
    if not harness.is_dir():
        raise ViewerError(f"하네스 폴더가 없습니다: {harness}")
    if not (harness / "AGENTS.md").is_file() or not ((harness / "product-tools").is_dir() or (harness / "skills").is_dir()):
        raise ViewerError(f"하네스 폴더가 아닙니다(AGENTS.md와 product-tools 또는 skills가 필요): {harness}")
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
    """설치 전부터 있던 export로는 브라우저를 띄우지 않도록 현재 최신 export를 이미 본 것으로 둔다."""
    state = hook.read_state(paths)
    latest = hook.newest_export(paths)
    if latest is None or state.get("last_key"):
        return None
    state.update({"last_key": hook.export_key(latest), "last_export": latest.name, "baseline": True})
    hook.write_state(paths, state)
    return latest.name


def codex_hooks_disabled(harness: Path) -> bool:
    config = harness / ".codex" / "config.toml"
    try:
        text = config.read_text(encoding="utf-8-sig")
    except OSError:
        return False
    return bool(re.search(r"^\s*(codex_)?hooks\s*=\s*false\b", text, re.M))


# ---------------------------------------------------------------- commands

def selected(args) -> list[str]:
    sources = [s for s in ("claude", "codex") if getattr(args, s) or args.both]
    if not sources:
        raise ViewerError("--claude, --codex, --both 중 하나를 주세요.")
    return sources


def cmd_install(args) -> int:
    harness = resolve_harness(args.harness)
    sources = selected(args)
    configs = {}
    for source in sources:  # 모두 읽을 수 있을 때만 바꾼다
        path = harness.joinpath(*TARGETS[source]["file"])
        configs[source] = (path, load_config(path))
        if "hooks" in configs[source][1]:
            hooks_table(configs[source][1], path)
    app, changed = copy_app(harness)
    paths = hook.Paths(str(harness))
    os.makedirs(paths.out, exist_ok=True)
    page = Path(paths.out, "index.html")
    if not page.is_file():  # 첫 export 전에도 열 수 있는 빈 화면
        shutil.copyfile(HERE / "index.html", page)
    baseline = set_baseline(paths)
    print(f"뷰어 파일: {app} ({'갱신 ' + ', '.join(changed) if changed else '변경 없음'})")
    print(f"화면 위치: {Path(paths.out, 'index.html')}")
    if baseline:
        print(f"설치 전 export({baseline})는 자동으로 띄우지 않습니다. 보려면 open --latest를 쓰세요.")
    for source in sources:
        path, config = configs[source]
        target = TARGETS[source]
        replaced = remove_ours(config, path)
        others = count_entries(config)
        table = config.setdefault("hooks", {})
        table.setdefault(target["event"], []).append({"matcher": target["matcher"], "hooks": [handler(source)]})
        save_config(path, config)
        rel = "/".join(target["file"])
        print(f"[{target['name']}] {rel}에 PostToolUse({target['matcher']}) 훅을 "
              f"{'갱신' if replaced else '추가'}했습니다. 다른 훅 {others}개는 그대로 둡니다.")
        if source == "claude":
            print("  다음: 이 하네스 폴더에서 Claude Code를 새로 열고 질문하세요. export가 저장되면 브라우저가 한 번 열립니다.")
        else:
            print("  다음: 이 하네스 폴더에서 `codex --search`를 열고, 처음 한 번 `/hooks`에서 이 훅을 검토·신뢰(trust)하세요.")
            print("        신뢰하기 전에는 실행되지 않습니다. 신뢰 우회 옵션은 쓰지 마세요.")
            if codex_hooks_disabled(harness):
                print("  주의: .codex/config.toml에서 hooks가 꺼져 있습니다(hooks = false). 켜야 실행됩니다.")
    if not shutil.which("uv"):
        print("주의: uv가 PATH에 없습니다. 훅 명령은 uv로 Python을 실행합니다.")
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
            print(f"[{target['name']}] 훅 {removed}개를 지웠습니다. 다른 설정은 그대로 둡니다.")
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
    if insights is None:
        with open(export, encoding="utf-8") as f:
            found = hook.find_insights(paths, json.load(f).get("session_id"))
        insights = Path(found) if found else None
    summary = build_view.generate(export, insights, args.focus or "auto", out_dir=Path(paths.out))
    if not args.export and Path(paths.exports) == export.parent:
        state = hook.read_state(paths)
        state.update({"last_key": hook.export_key(hook.newest_export(paths)), "last_export": export.name})
        state.pop("failed_key", None)
        hook.write_state(paths, state)
    index = Path(summary["outputs"]["index"]).resolve()
    if not args.no_browser:
        import webbrowser

        webbrowser.open(index.as_uri())
    print(json.dumps({"export": export.name, "insights": insights.name if insights else None, "focus": summary["focus"],
                      "pages": summary["pages"], "index": str(index), "warnings": summary["warnings"]}, ensure_ascii=False, indent=1))
    return 0


def cmd_status(args) -> int:
    harness = resolve_harness(args.harness)
    paths = hook.Paths(str(harness))
    app = harness.joinpath(*APP_REL)
    report = {"harness": str(harness), "app_files": {n: (app / n).is_file() for n in APP_FILES}}
    for source, target in TARGETS.items():
        path = harness.joinpath(*target["file"])
        try:
            report[source] = {"file": "/".join(target["file"]), "registered": registered(load_config(path), source)}
        except ViewerError as exc:
            report[source] = {"file": "/".join(target["file"]), "error": str(exc)}
    report["codex_hooks_disabled"] = codex_hooks_disabled(harness)
    latest = hook.newest_export(paths)
    state = hook.read_state(paths)
    report["latest_export"] = latest.name if latest else None
    report["last_built"] = state.get("last_export")
    report["up_to_date"] = bool(latest) and state.get("last_key") == hook.export_key(latest)
    report["insights"] = state.get("insights")
    report["opened_sessions"] = len(state.get("opened_sessions") or [])
    try:
        lines = Path(paths.error_log).read_text(encoding="utf-8").strip().splitlines()
        report["last_error"] = next((line for line in reversed(lines) if line[:2].isdigit()), lines[-1] if lines else None)
    except OSError:
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
        p.add_argument("harness", nargs="?", help="하네스 폴더 (기본: 이 파일이 든 하네스)")
    p = sub.add_parser("open", help="최근 export로 화면을 다시 만들고 연다")
    p.add_argument("--latest", action="store_true", help="가장 최근 export (기본 동작)")
    p.add_argument("--export", help="특정 export 파일")
    p.add_argument("--insights", help="insights 파일 (기본: 같은 session_id를 runtime-data/visual-viewer에서 찾음)")
    p.add_argument("--focus", help="처음 보여줄 화면 id (기본: 상태로 선택)")
    p.add_argument("--no-browser", action="store_true", help="브라우저를 열지 않고 화면만 만든다")
    p.add_argument("harness", nargs="?", help="하네스 폴더 (기본: 이 파일이 든 하네스)")
    p = sub.add_parser("status", help="설치·갱신 상태")
    p.add_argument("harness", nargs="?", help="하네스 폴더 (기본: 이 파일이 든 하네스)")
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
