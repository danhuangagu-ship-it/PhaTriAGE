#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 MODEL_BUNDLE_URL MARKER_BUNDLE_URL [ASSET_ROOT]" >&2
  exit 2
fi

MODEL_URL=$1
MARKER_URL=$2
ASSET_ROOT=${3:-"${PHATRIAGE_ASSETS:-$HOME/.cache/phatriage/assets}"}
mkdir -p "$ASSET_ROOT"
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

curl --fail --location --retry 3 "$MODEL_URL" -o "$tmpdir/model.tar.gz"
curl --fail --location --retry 3 "$MARKER_URL" -o "$tmpdir/markers.tar.gz"
tar -xzf "$tmpdir/model.tar.gz" -C "$ASSET_ROOT"
tar -xzf "$tmpdir/markers.tar.gz" -C "$ASSET_ROOT"
echo "Assets installed under $ASSET_ROOT"
echo "Run: PHATRIAGE_ASSETS='$ASSET_ROOT' phatriage doctor"

