#!/bin/bash
#SBATCH --job-name=phatriage_cpu
#SBATCH --partition=ieg
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/smoke_cpu_%j.out
#SBATCH --error=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026/logs/smoke_cpu_%j.err
set -euo pipefail
ROOT=/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-9.phatriage-toolkit-20261026
export PHATRIAGE_ASSETS="$ROOT/release_assets/staging"
export TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4
"$ROOT/environment/phatriage/bin/python" "$ROOT/repo/deployment/smoke_release.py" \
  --device cpu \
  --source-fasta /ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-8.manuscript-final-analysis-20261026/06_temperate_gene_annotation/results/internal_test_395/input/internal_test_full_395.fasta.gz \
  --reference /ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/0-8.manuscript-final-analysis-20261026/06_temperate_gene_annotation/results/internal_test_395/final_output/raw_three_class_probabilities.tsv \
  --assets "$PHATRIAGE_ASSETS" \
  --output "$ROOT/smoke/cpu"

