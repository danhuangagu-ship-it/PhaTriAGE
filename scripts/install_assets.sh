#!/usr/bin/env bash
set -euo pipefail

RELEASE_TAG=${PHATRIAGE_RELEASE_TAG:-v0.1.0}
RELEASE_BASE=${PHATRIAGE_RELEASE_BASE:-"https://github.com/danhuangagu-ship-it/PhaTriAGE/releases/download/${RELEASE_TAG}"}
MODEL_NAME=phatriage-mini-long-full-add462-v1.tar.gz
MARKER_NAME=temperate_marker_db_hmmer3_v1.tar.gz
MODEL_SHA256=e4a66f541e6a956199bb0b9289a6c79f0b46158eee64dc508e125c2b8d9de466
MARKER_SHA256=8fe647cc4bd92f0a07cdc9cd38c3fe02e8cc5609ffb6cd4c759b2853e539e985
ASSET_ROOT=${1:-"${PHATRIAGE_ASSETS:-$HOME/.cache/phatriage/assets}"}

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [ASSET_ROOT]" >&2
  exit 2
fi

for command in curl tar; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command is unavailable: $command" >&2
    exit 1
  fi
done

checksum() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Neither sha256sum nor shasum is available" >&2
    exit 1
  fi
}

download_and_check() {
  local name=$1
  local expected=$2
  local target=$3
  echo "Downloading ${name}"
  curl --fail --location --retry 3 --continue-at - \
    "${RELEASE_BASE}/${name}" -o "$target"
  local observed
  observed=$(checksum "$target")
  if [[ "$observed" != "$expected" ]]; then
    echo "Checksum mismatch for ${name}" >&2
    echo "Expected: ${expected}" >&2
    echo "Observed: ${observed}" >&2
    exit 1
  fi
}

mkdir -p "$ASSET_ROOT"
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

download_and_check "$MODEL_NAME" "$MODEL_SHA256" "$tmpdir/$MODEL_NAME"
download_and_check "$MARKER_NAME" "$MARKER_SHA256" "$tmpdir/$MARKER_NAME"
tar -xzf "$tmpdir/$MODEL_NAME" -C "$ASSET_ROOT"
tar -xzf "$tmpdir/$MARKER_NAME" -C "$ASSET_ROOT"

echo "Assets installed and verified under: $ASSET_ROOT"
echo "Run: phatriage doctor"
