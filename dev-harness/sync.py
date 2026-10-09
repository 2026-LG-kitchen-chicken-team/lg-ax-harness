"""Regular-file Claude adapter generation. Does not mutate global configuration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from checks import safe_path, write_json


def expected_files(root: Path) -> dict[str, bytes]:
    result = {}
    source = safe_path(root, ".agents/skills", must_exist=True)
    for file in sorted(source.rglob("*")):
        if not file.is_file() or "__pycache__" in file.parts or file.suffix == ".pyc":
            continue
        safe_path(root, file.relative_to(root).as_posix(), must_exist=True)
        relative = file.relative_to(source).as_posix()
        # Codex upstream scripts/references are vendor-preserved, not Claude runtime instructions.
        if relative.startswith("harness/"):
            if relative != "harness/SKILL.md":
                continue
            text = """---
name: harness
description: "Claude Code에서 개발 작업을 분해하고 네이티브 위임·검사·독립 리뷰·인수인계를 연결한다."
---

# Claude 개발 오케스트레이션

CLAUDE.md, 요구·결정·개발 작업 원본, git status/diff를 읽는다. 필요한 .claude/agents 역할과 Skill만 선택하고 자신의 네이티브 Agent 도구로 위임한다. Codex 도구를 호출하지 않는다.

부모가 목표·의존성·원본 지문·소유 파일·완료 명령·시간/호출 상한·중단 조건을 배정한다. 한 checkout의 작성자는 한 명이며 병렬 쓰기는 독립 worktree로 한다. 읽기 전용 역할은 결과만 반환하고 부모가 파일과 기록을 작성한다.

실제 native ID와 결과만 기록한다. 장부·검사 helper는 python dev-harness/cli.py로 실행하며 Agent나 메시지를 대신 실행하지 않는다. Codex run registry의 lifecycle을 Claude 세션 상태라고 가정하지 않는다. Claude에서 사용할 상태 매핑은 팀원 환경에서 검증한 범위만 기록한다.

완료 검사는 실제 command/exit code/receipt, 통합 diff와 독립 리뷰로 판단한다. 미측정 토큰은 unknown, 미실행 검사는 not_run이다. 기술별 지침은 배정된 나머지 Skill만 읽는다. 실제 Claude 발견·위임·인수인계 검증 상태는 docs/validation/development-harness.md를 따른다.
"""
            result[relative] = text.encode("utf-8")
        else:
            result[relative] = file.read_bytes().replace(b".agents/skills/", b".claude/skills/")
    return result


def sync_skills(root: Path, *, check: bool = False) -> list[str]:
    root = root.resolve(strict=True)
    expected = expected_files(root)
    target = safe_path(root, ".claude/skills")
    actual = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    errors = ["Unexpected Claude copy: " + p for p in sorted(actual - expected.keys())]
    for relative, content in expected.items():
        path = safe_path(root, ".claude/skills/" + relative)
        if check:
            if not path.is_file() or path.read_bytes() != content:
                errors.append("Claude skill drift: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    manifest = {"source": ".agents/skills", "target": ".claude/skills", "transforms": [
        "harness: Claude-native entrypoint; no upstream Codex runtime references",
        "other Skills: project skill path adapted"], "files": {
            p: hashlib.sha256(raw).hexdigest() for p, raw in expected.items()}}
    path = safe_path(root, "dev-harness/claude-sync-manifest.json")
    if check:
        if not path.is_file() or json.loads(path.read_text(encoding="utf-8")) != manifest:
            errors.append("Claude sync manifest drift")
    else:
        write_json(path, manifest)
    return errors
