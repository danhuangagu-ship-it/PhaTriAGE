#!/bin/bash
#SBATCH --job-name=phatriage_env_fix
#SBATCH --partition=ieg
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/env_fix_%j.out
#SBATCH --error=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/env_fix_%j.err
set -euo pipefail
ROOT=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026
ENV="$ROOT/environment/phatriage"
"$ENV/bin/pip" install \
  torch==2.13.0 \
  transformers==4.57.6 \
  pandas==2.3.3 \
  numpy==2.2.6 \
  safetensors==0.8.0 \
  huggingface-hub==0.36.2
"$ENV/bin/pip" install --no-deps -e "$ROOT/repo"
"$ENV/bin/phatriage" --version
"$ENV/bin/python" -m pytest -q "$ROOT/repo/tests"

