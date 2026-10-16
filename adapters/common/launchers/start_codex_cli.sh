#!/usr/bin/env bash
# LG AX - Codex CLI 원클릭 시작 (macOS/Linux): ./start_codex_cli.sh  또는  bash start_codex_cli.sh
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
uv run --no-project --python 3.12 python judge.py prepare --engine codex --ui cli
python="$(uv python find 3.12)"
mkdir -p codex/runtime-data/agent-office
"$python" judge.py observe --engine codex --keep-following --open > codex/runtime-data/agent-office/observer.log 2>&1 &
observer=$!
trap 'kill "$observer" 2>/dev/null || true; wait "$observer" 2>/dev/null || true' EXIT
echo "실행 관찰을 켰습니다(기록: codex/runtime-data/agent-office/observer.log). 첫 질문을 보내면 실행 대시보드가 브라우저에 열립니다."
cd codex
codex --search --sandbox workspace-write --ask-for-approval on-request --model gpt-6.1-sol --config model_reasoning_effort=medium
