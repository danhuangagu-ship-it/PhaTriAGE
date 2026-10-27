#!/usr/bin/env bash
set -euo pipefail

MODE=${1:-cpu}
case "$MODE" in
  cpu)
    ENV_NAME=${PHATRIAGE_ENV_NAME:-phatriage-cpu}
    ENV_FILE=environments/cpu.yml
    ;;
  gpu)
    ENV_NAME=${PHATRIAGE_ENV_NAME:-phatriage-gpu}
    ENV_FILE=environments/gpu.yml
    ;;
  *)
    echo "Usage: $0 [cpu|gpu]" >&2
    exit 2
    ;;
esac

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

if command -v mamba >/dev/null 2>&1; then
  SOLVER=mamba
elif command -v conda >/dev/null 2>&1; then
  SOLVER=conda
else
  echo "Install Miniforge/Conda or Mamba first, then rerun this command." >&2
  exit 1
fi

if "$SOLVER" run -n "$ENV_NAME" python -V >/dev/null 2>&1; then
  echo "Updating existing environment: $ENV_NAME"
  "$SOLVER" env update -n "$ENV_NAME" -f "$ENV_FILE" --prune
else
  echo "Creating environment: $ENV_NAME"
  "$SOLVER" env create -n "$ENV_NAME" -f "$ENV_FILE"
fi

"$SOLVER" run -n "$ENV_NAME" python -m pip install --no-deps .
bash scripts/install_assets.sh
"$SOLVER" run -n "$ENV_NAME" phatriage doctor

echo
echo "PhaTriAGE installation is complete."
echo "Activate it with: conda activate $ENV_NAME"
echo "Then run: phatriage run --input genomes.fasta --output results --device $MODE"
