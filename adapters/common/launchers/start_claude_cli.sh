#!/usr/bin/env bash
# LG AX - Claude Code CLI 원클릭 시작 (macOS/Linux): ./start_claude_cli.sh  또는  bash start_claude_cli.sh
set -euo pipefail
cd "$(dirname "$0")"
need_uv() {
  command -v uv >/dev/null 2>&1 && return 0
  PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 && return 0
  echo "uv가 없습니다. 공식 안내: https://docs.astral.sh/uv/getting-started/installation/"
  echo "공식 설치 명령: curl -LsSf https://astral.sh/uv/install.sh | sh"
  printf '지금 이 공식 설치 명령을 실행할까요? [y/N] '
  read -r answer || answer=
  case "$answer" in y|Y|yes) ;; *) return 1 ;; esac
  curl -LsSf https://astral.sh/uv/install.sh | sh
  command -v uv >/dev/null 2>&1
}
need_uv
uv run --no-project --python 3.12 python judge.py prepare --engine claude --ui cli
PATH="$HOME/.local/bin:$PATH"
cd claude
echo "Claude Code를 시작합니다 (Opus 5.5, 추론 중간). 끝내려면 /exit"
exec claude --model claude-opus-5-5 --effort medium
