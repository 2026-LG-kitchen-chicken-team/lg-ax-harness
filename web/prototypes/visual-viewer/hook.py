"""Claude Code·Codex CLI 공용 훅: 하네스가 새 export를 저장하면 시각자료 뷰어 화면을 다시 만든다.

`viewer.py install`이 하네스의 `.claude/settings.local.json`(PostToolUse, Bash|PowerShell, async)이나
`.codex/hooks.json`(PostToolUse, Bash, 동기)에 등록한다. 두 CLI 모두 훅 입력 JSON을 stdin으로 준다.
이 파일은 `<하네스>/web/prototypes/visual-viewer/`에 있고 하네스 위치는 자기 위치로 정한다.

- 등록된 명령은 이 파일의 SHA-256이 설치 때와 같을 때만 이 파일을 실행하고, 인자로 받은 build_view.py·
  index.html의 SHA-256이 맞을 때만 그 파일을 쓴다. 파일이 바뀌면 아무것도 실행하지 않고 로그만 남긴다.
- 표준 라이브러리만 쓴다. 항상 exit 0이며 stdout·stderr에 쓰지 않는다(모델 문맥에 아무것도 넣지 않음).
  오류는 `runtime-data/visual-viewer/hook-error.log`에만 남긴다.
- 업무·모델·Tool을 실행하지 않는다. `runtime-data/exports`에 아직 그리지 않은 export가 있을 때만
  build_view.generate를 부른다. insights는 출력 폴더의 `insights-*.json`에서 session_id·turn_id로 고른다.
- CLI 세션(claude·codex + session_id)마다 처음 화면을 만들 때만 기본 브라우저를 연다. 세션 기록을 먼저 저장하고
  연다. 열린 화면은 그 뒤로 2초 안에 새 데이터로 바뀐다. `LGAX_VIEWER_NO_OPEN=1`이면 열지 않는다(시험용).
"""

from __future__ import annotations

# 새 export가 없을 때 빨리 끝나도록 무거운 모듈(build_view 등)은 필요할 때만 불러온다.
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SOURCES = ("claude", "codex")
SYNC_SOURCES = ("codex",)  # Codex 0.146은 async 훅을 건너뛰므로 동기로 등록한다
KEEP_SESSIONS = 50
LOCK_WAIT = {"async": 10.0, "sync": 2.0}
LOG_LIMIT = 256 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class Paths:
    def __init__(self, harness: str = HARNESS):
        self.harness = harness
        self.exports = os.path.join(harness, "runtime-data", "exports")
        self.out = os.path.join(harness, "runtime-data", "visual-viewer")
        self.state = os.path.join(self.out, ".hook-state.json")
        self.lock = os.path.join(self.out, ".hook.lock")
        self.error_log = os.path.join(self.out, "hook-error.log")


class IntegrityError(Exception):
    pass


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_state(paths: Paths) -> dict:
    for attempt in range(5):
        try:
            with open(paths.state, encoding="utf-8") as f:
                value = json.load(f)
            return value if isinstance(value, dict) else {}
        except PermissionError:  # Windows: 다른 훅이 바꾸는 중
            time.sleep(0.05 * (attempt + 1))
        except (OSError, ValueError):
            return {}
    return {}


def write_state(paths: Paths, state: dict) -> None:
    """원자적으로 바꾼다. Windows에서 다른 훅이 읽는 중이면 os.replace가 실패하므로 잠시 뒤 다시 한다."""
    os.makedirs(paths.out, exist_ok=True)
    tmp = f"{paths.state}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    for attempt in range(20):
        try:
            os.replace(tmp, paths.state)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise PermissionError(f"상태 파일을 바꾸지 못했습니다: {paths.state}")


def newest_export(paths: Paths):
    try:
        entries = [e for e in os.scandir(paths.exports) if e.name.endswith(".json") and e.is_file()]
    except OSError:
        return None
    return max(entries, key=lambda e: (e.stat().st_mtime_ns, e.name)) if entries else None


def export_key(entry) -> str:
    stat = entry.stat()
    return f"{entry.name}:{stat.st_mtime_ns}:{stat.st_size}"


def insights_signature(paths: Paths) -> str:
    """insights 파일이 바뀌면(고쳐지면) 실패했던 export를 다시 시도하도록 실패 기록에 함께 넣는다."""
    try:
        items = sorted((e.name, e.stat().st_mtime_ns, e.stat().st_size) for e in os.scandir(paths.out)
                       if e.name.startswith("insights-") and e.name.endswith(".json") and e.is_file())
    except OSError:
        items = []
    return sha256_bytes(json.dumps(items).encode("utf-8"))[:16]


def failure_key(paths: Paths, entry) -> str:
    return f"{export_key(entry)}|{insights_signature(paths)}"


# ---------------------------------------------------------------- lock (OS file lock: 프로세스가 죽으면 저절로 풀린다)

class Lock:
    def __init__(self, paths: Paths):
        self.path = paths.lock
        self.fd = None

    def acquire(self, wait: float) -> bool:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + wait
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.fd = fd
                return True
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    return False
                time.sleep(0.1)

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(self.fd)
        self.fd = None


# ---------------------------------------------------------------- build

def verified_read(path: str, expected: str | None) -> bytes:
    with open(path, "rb") as f:
        raw = f.read()
    if expected is not None and sha256_bytes(raw) != expected:
        raise IntegrityError(f"{os.path.basename(path)}가 설치 때와 다릅니다. viewer.py install로 다시 설치하세요.")
    return raw


def load_build_view(expected: str | None):
    """build_view.py를 SHA-256이 맞는 바이트로만 불러온다(검사한 바이트 그대로 실행)."""
    import types

    path = os.path.join(HERE, "build_view.py")
    raw = verified_read(path, expected)
    module = types.ModuleType("build_view")
    module.__file__ = path
    sys.modules["build_view"] = module
    exec(compile(raw, path, "exec"), module.__dict__)  # noqa: S102 - 검증한 설치 파일
    return module


def rebuild(paths: Paths, export_path: str, hashes: dict | None = None, focus: str | None = "auto") -> dict:
    """export 하나로 view-data.js를 만든다. insights는 출력 폴더에서 session_id·turn_id로 고른다."""
    from pathlib import Path

    hashes = hashes or {}
    build_view = load_build_view(hashes.get("build_view"))
    return build_view.generate(Path(export_path), None, focus, out_dir=Path(paths.out), insights_dir=Path(paths.out),
                               index_sha256=hashes.get("index"))


def open_browser(paths: Paths) -> None:
    if os.environ.get("LGAX_VIEWER_NO_OPEN"):
        return
    import webbrowser
    from pathlib import Path

    webbrowser.open(Path(paths.out, "index.html").resolve().as_uri())


def run(hook_input: dict, source: str, paths: Paths | None = None, hashes: dict | None = None) -> dict:
    paths = paths or Paths()
    latest = newest_export(paths)
    if latest is None:
        return {"changed": False, "reason": "export 없음"}
    state = read_state(paths)
    key = export_key(latest)
    if key == state.get("last_key") or failure_key(paths, latest) == state.get("failed_key"):
        return {"changed": False, "reason": "이미 처리한 export", "export": latest.name}
    lock = Lock(paths)
    if not lock.acquire(LOCK_WAIT["sync" if source in SYNC_SOURCES else "async"]):
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
            if key == state.get("last_key") or failure_key(paths, latest) == state.get("failed_key"):
                break
            try:
                summary = rebuild(paths, latest.path, hashes)
            except IntegrityError:
                raise
            except (Exception, SystemExit) as exc:  # noqa: BLE001
                # 쓰는 중인 export를 읽었을 수 있어 한 번 더 본다. 두 번 실패하면 export·insights가 바뀔 때까지 다시 하지 않는다.
                attempts[key] = attempts.get(key, 0) + 1
                if attempts[key] < 2:
                    time.sleep(0.5)
                    continue
                state["failed_key"] = failure_key(paths, latest)
                write_state(paths, state)
                log_error(paths, f"view 생성 실패 {latest.name}: {type(exc).__name__}: {exc}")
                continue
            state.pop("failed_key", None)
            state.pop("baseline", None)
            state.update({"last_key": key, "built_key": key, "last_export": latest.name,
                          "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "focus": summary["focus"],
                          "insights": summary["insights"], "insights_file": summary.get("insights_file"),
                          "warnings": summary["warnings"]})
            write_state(paths, state)
            built = latest.name
        opened = False
        if built:
            session = f"{source}:{hook_input.get('session_id') or 'no-session'}"
            state = read_state(paths)
            seen = [s for s in state.get("opened_sessions") or [] if isinstance(s, str)]
            if session not in seen:
                # 먼저 기록하고 연다: 기록에 실패하면 열지 않으므로 한 세션에서 두 번 열리지 않는다.
                seen.append(session)
                state["opened_sessions"] = seen[-KEEP_SESSIONS:]
                write_state(paths, state)
                open_browser(paths)
                opened = True
        return {"changed": bool(built), "export": built, "opened_browser": opened}
    finally:
        lock.release()


def parse_args(argv: list[str], hook_input: dict) -> tuple[str, dict]:
    """`<source> <build_view sha256> <index.html sha256>`. source가 없으면 입력으로 추정한다."""
    source = next((a for a in argv if a in SOURCES), None)
    if source is None:
        source = "codex" if "turn_id" in hook_input else ("claude" if os.environ.get("CLAUDE_PROJECT_DIR") else "cli")
    digests = [a for a in argv if HEX64.match(a)]
    hashes = {"build_view": digests[0], "index": digests[1]} if len(digests) >= 2 else {}
    return source, hashes


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
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        value = json.loads(raw) if raw.strip() else {}
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def main(argv: list[str] | None = None) -> int:
    paths = Paths()
    try:
        silence()
        hook_input = read_hook_input()
        source, hashes = parse_args(sys.argv[1:] if argv is None else argv, hook_input)
        if not hashes:
            # 지문 없이 불린 경우(옛 설치·직접 실행)는 검사하지 않은 파일을 실행하지 않는다.
            log_error(paths, "훅 명령에 파일 지문이 없습니다. viewer.py install로 다시 설치하세요.")
            return 0
        run(hook_input, source, paths, hashes)
    except BaseException:  # noqa: BLE001 - 훅 실패가 CLI 작업을 방해하지 않게 기록만 남긴다
        import traceback

        log_error(paths, traceback.format_exc())
    return 0


if __name__ == "__main__":
    sys.exit(main())
