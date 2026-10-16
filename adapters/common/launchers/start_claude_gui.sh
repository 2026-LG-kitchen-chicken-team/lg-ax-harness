#!/usr/bin/env bash
# LG AX - Claude Desktop 원클릭 시작 (macOS): ./start_claude_gui.sh  또는  bash start_claude_gui.sh
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
uv run --no-project --python 3.12 python judge.py prepare --engine claude --ui gui
uv run --no-project --python 3.12 python judge.py desktop --engine claude
echo "첫 질문을 보내면 실행 대시보드가 브라우저에 자동으로 열립니다."
