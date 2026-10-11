"""Claude Code·Codex CLI 공용 훅: 하네스가 새 export를 저장하면 시각자료 뷰어 화면을 다시 만든다.

`viewer.py install`이 하네스의 `.claude/settings.local.json`(PostToolUse, Bash|PowerShell)이나
`.codex/hooks.json`(PostToolUse, Bash)에 등록한다. 두 CLI 모두 훅 입력 JSON을 stdin으로 준다.
이 파일은 `<하네스>/web/prototypes/visual-viewer/`에 있고 하네스 위치는 자기 위치로 정한다.

- 표준 라이브러리만 쓴다. 항상 exit 0이며 stdout·stderr에 쓰지 않는다(모델 문맥에 아무것도 넣지 않음).
  오류는 `runtime-data/visual-viewer/hook-error.log`에만 남긴다.
- 업무·모델·Tool을 실행하지 않는다. `runtime-data/exports`에 아직 그리지 않은 export가 있을 때만
  build_view.generate를 부른다. 같은 session_id의 `insights-*.json`이 출력 폴더에 있으면 함께 쓴다.
- CLI 세션(claude·codex + session_id)마다 처음 화면을 만들 때만 기본 브라우저를 연다.
  열린 화면은 그 뒤로 2초 안에 새 데이터로 바뀐다. `LGAX_VIEWER_NO_OPEN=1`이면 열지 않는다(시험용).
"""

from __future__ import annotations

# 새 export가 없을 때 빨리 끝나도록 무거운 모듈(build_view 등)은 필요할 때만 불러온다.
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SOURCES = ("claude", "codex")
KEEP_SESSIONS = 50
LOCK_STALE_SECONDS = 120
LOCK_WAIT_SECONDS = 10
LOG_LIMIT = 256 * 1024


class Paths:
    def __init__(self, harness: str = HARNESS):
        self.harness = harness
        self.exports = os.path.join(harness, "runtime-data", "exports")
        self.out = os.path.join(harness, "runtime-data", "visual-viewer")
        self.state = os.path.join(self.out, ".hook-state.json")
        self.lock = os.path.join(self.out, ".hook.lock")
        self.error_log = os.path.join(self.out, "hook-error.log")


def read_state(paths: Paths) -> dict:
    try:
        with open(paths.state, encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(paths: Paths, state: dict) -> None:
    os.makedirs(paths.out, exist_ok=True)
    tmp = f"{paths.state}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, paths.state)


def newest_export(paths: Paths):
    try:
        entries = [e for e in os.scandir(paths.exports) if e.name.endswith(".json") and e.is_file()]
    except OSError:
        return None
    return max(entries, key=lambda e: (e.stat().st_mtime_ns, e.name)) if entries else None


def export_key(entry) -> str:
    stat = entry.stat()
    return f"{entry.name}:{stat.st_mtime_ns}:{stat.st_size}"


def find_insights(paths: Paths, session_id: str | None) -> str | None:
    """출력 폴더의 insights-*.json 중 session_id가 같은 파일(이름순 첫 번째)."""
    if not session_id:
        return None
    try:
        names = sorted(n for n in os.listdir(paths.out) if n.startswith("insights-") and n.endswith(".json"))
    except OSError:
        return None
    for name in names:
        path = os.path.join(paths.out, name)
        try:
            with open(path, encoding="utf-8-sig") as f:
                if json.load(f).get("session_id") == session_id:
                    return path
        except (OSError, ValueError, AttributeError):
            continue
    return None


def rebuild(paths: Paths, export_path: str, focus: str | None = "auto") -> dict:
    """export 하나로 view-data.js를 만든다. insights는 같은 session_id만 쓴다."""
    from pathlib import Path

    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import build_view  # 같은 폴더의 생성 스크립트

    with open(export_path, encoding="utf-8") as f:
        session_id = json.load(f).get("session_id")
    insights = find_insights(paths, session_id)
    summary = build_view.generate(Path(export_path), Path(insights) if insights else None, focus, out_dir=Path(paths.out))
    summary["insights_file"] = os.path.basename(insights) if insights else None
    return summary


def acquire_lock(paths: Paths) -> bool:
    os.makedirs(paths.out, exist_ok=True)
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        try:
            fd = os.open(paths.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - os.stat(paths.lock).st_mtime > LOCK_STALE_SECONDS:
                    os.remove(paths.lock)  # 죽은 훅이 남긴 잠금
                    continue
            except OSError:
                continue
        if time.monotonic() > deadline:
            return False
        time.sleep(0.2)


def release_lock(paths: Paths) -> None:
    try:
        os.remove(paths.lock)
    except OSError:
        pass


def open_browser(paths: Paths) -> None:
    if os.environ.get("LGAX_VIEWER_NO_OPEN"):
        return
    import webbrowser
    from pathlib import Path

    webbrowser.open(Path(paths.out, "index.html").resolve().as_uri())


def run(hook_input: dict, source: str, paths: Paths | None = None) -> dict:
    paths = paths or Paths()
    latest = newest_export(paths)
    if latest is None:
        return {"changed": False, "reason": "export 없음"}
    state = read_state(paths)
    if export_key(latest) in (state.get("last_key"), state.get("failed_key")):
        return {"changed": False, "reason": "이미 처리한 export", "export": latest.name}
    if not acquire_lock(paths):
        return {"changed": False, "reason": "다른 훅이 갱신 중"}
    try:
        built = None
        attempts: dict[str, int] = {}
        # 잠금을 기다리거나 만드는 동안 더 새 export가 생길 수 있어, 최신이 바뀌지 않을 때까지 다시 본다.
        for _ in range(6):
            latest = newest_export(paths)
            state = read_state(paths)
            if latest is None:
                break
            key = export_key(latest)
            if key in (state.get("last_key"), state.get("failed_key")):
                break
            try:
                summary = rebuild(paths, latest.path)
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                # 쓰는 중인 export를 읽었을 수 있어 한 번 더 본다. 두 번 실패한 export는 다시 시도하지 않는다.
                attempts[key] = attempts.get(key, 0) + 1
                if attempts[key] < 2:
                    time.sleep(0.5)
                    continue
                state["failed_key"] = key
                write_state(paths, state)
                log_error(paths, f"view 생성 실패 {latest.name}: {type(exc).__name__}: {exc}")
                continue
            state.pop("failed_key", None)
            state.update({"last_key": key, "last_export": latest.name, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                          "focus": summary["focus"], "insights": summary["insights"], "insights_file": summary["insights_file"],
                          "warnings": summary["warnings"]})
            write_state(paths, state)
            built = latest.name
        opened = False
        if built:
            session = f"{source}:{hook_input.get('session_id') or 'no-session'}"
            state = read_state(paths)
            seen = [s for s in state.get("opened_sessions") or [] if isinstance(s, str)]
            if session not in seen:
                open_browser(paths)
                seen.append(session)
                state["opened_sessions"] = seen[-KEEP_SESSIONS:]
                write_state(paths, state)
                opened = True
        return {"changed": bool(built), "export": built, "opened_browser": opened}
    finally:
        release_lock(paths)


def detect_source(argv: list[str], hook_input: dict) -> str:
    for arg in argv:
        if arg in SOURCES:
            return arg
    if "turn_id" in hook_input:  # Codex 훅 입력에만 있는 필드
        return "codex"
    return "claude" if os.environ.get("CLAUDE_PROJECT_DIR") else "cli"


def log_error(paths: Paths, text: str) -> None:
    try:
        os.makedirs(paths.out, exist_ok=True)
        mode = "a"
        if os.path.exists(paths.error_log) and os.path.getsize(paths.error_log) > LOG_LIMIT:
            mode = "w"
        with open(paths.error_log, mode, encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text.rstrip() + "\n")
    except OSError:
        pass


def silence() -> None:
    """stdout·stderr(자식 프로세스 포함)를 버린다. 훅 출력이 CLI 모델 문맥에 들어가지 않게 한다."""
    try:
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
    except OSError:
        pass
    sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")


def read_hook_input() -> dict:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        value = json.loads(raw) if raw.strip() else {}
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    paths = Paths()
    try:
        silence()
        hook_input = read_hook_input()
        run(hook_input, detect_source(sys.argv[1:] if argv is None else argv, hook_input), paths)
    except BaseException:  # noqa: BLE001 - 훅 실패가 CLI 작업을 방해하지 않게 기록만 남긴다
        import traceback

        log_error(paths, traceback.format_exc())
    return 0


if __name__ == "__main__":
    sys.exit(main())
