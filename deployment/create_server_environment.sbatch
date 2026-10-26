#!/bin/bash
#SBATCH --job-name=phatriage_env
#SBATCH --partition=ieg
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/env_%j.out
#SBATCH --error=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/env_%j.err
set -euo pipefail
ROOT=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026
ENV="$ROOT/environment/phatriage"
if [[ -e "$ENV" ]]; then
  echo "Environment path already exists: $ENV" >&2
  exit 3
fi
/home/danhuang/miniconda3/bin/mamba create -y -p "$ENV" \
  --clone /home/danhuang/.mamba/envs/nucleotide_lm
/home/danhuang/miniconda3/bin/mamba install -y -p "$ENV" -c conda-forge \
  hmmer=3.4 pyrodigal-gv=0.3.2 pytest
"$ENV/bin/pip" install --no-deps -e "$ROOT/repo"
"$ENV/bin/phatriage" --version
"$ENV/bin/python" -m pytest -q "$ROOT/repo/tests"

