#!/usr/bin/env bash
set -euo pipefail
repo='2026-LG-kitchen-chicken-team/lg-ax-agent'
installer_tag='installer-v0.1.1'
core_sha='54a0e30d2b1ced99894782b083e7745421f8a717c1223b89a8ae5e39dda85dd7'
engine=codex
version=product-v0.16.2
transport=gh
target=''
download_only=no
while (($#)); do
  case "$1" in
    --engine) engine="${2:?Missing engine}"; shift 2 ;;
    --version) version="${2:?Missing version}"; shift 2 ;;
    --target) target="${2:?Missing target}"; shift 2 ;;
    --transport) transport="${2:?Missing transport}"; shift 2 ;;
    --download-only) download_only=yes; shift ;;
    -h|--help) printf '%s\n' 'LG AX installer: --engine codex|claude --version product-v0.16.2 --target NEW_FOLDER --transport gh|public --download-only'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$engine" in codex|claude) ;; *) echo 'Invalid engine' >&2; exit 2 ;; esac
case "$transport" in gh|public) ;; *) echo 'Invalid transport' >&2; exit 2 ;; esac
work="$(mktemp -d "${TMPDIR:-/tmp}/lgax-installer.XXXXXXXX")"
trap 'rm -f "$work/install.py"; rmdir "$work"' EXIT
if [[ "$transport" == gh ]]; then
  command -v gh >/dev/null || { echo 'Install GitHub CLI and run gh auth login with repository read access.' >&2; exit 1; }
  gh release download "$installer_tag" --repo "$repo" --pattern install.py --output "$work/install.py"
else
  curl --proto '=https' --tlsv1.2 -fsSL "https://github.com/$repo/releases/download/$installer_tag/install.py" -o "$work/install.py"
fi
if command -v sha256sum >/dev/null; then
  actual="$(sha256sum "$work/install.py")"; actual="${actual%% *}"
else
  actual="$(shasum -a 256 "$work/install.py")"; actual="${actual%% *}"
fi
[[ "$actual" == "$core_sha" ]] || { echo 'Installer checksum mismatch.' >&2; exit 1; }
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  echo 'uv prepares Python 3.12. Official installer: https://astral.sh/uv/install.sh'
  printf 'Install uv now? [y/N] '
  answer=''; read -r answer </dev/tty || true
  case "$answer" in y|Y|yes) curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh | sh ;;
    *) echo 'Stopped. Install uv and run this command again.' >&2; exit 1 ;; esac
fi
args=(--repo "$repo" --version "$version" --engine "$engine" --transport "$transport")
[[ -z "$target" ]] || args+=(--target "$target")
[[ "$download_only" != yes ]] || args+=(--download-only)
uv run --no-project --python 3.12 python "$work/install.py" "${args[@]}"
