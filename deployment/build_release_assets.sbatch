#!/bin/bash
#SBATCH --job-name=phatriage_assets
#SBATCH --partition=ieg
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/assets_%j.out
#SBATCH --error=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/assets_%j.err
set -euo pipefail
ROOT=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026
~/.mamba/envs/nucleotide_lm/bin/python "$ROOT/repo/deployment/build_release_assets.py" \
  --output-root "$ROOT/release_assets"

