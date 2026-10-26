# PhaTriAGE

**PhaTriAGE — Phage Tri-class Lifestyle Assignment with Genomic Evidence** predicts bacteriophage lifestyle as **Virulent**, **Temperate**, or **Chronic** from nucleotide FASTA files. It then adds an independent ORF/HMMER annotation layer for conserved temperate-associated markers.

PhaTriAGE uses the final conflict-resolved `+462` ProkBERT Mini-long model with full fine-tuning and the original linear classification head. Classification and marker annotation are independent: marker hits never alter the predicted class or probability.

## Output

The primary `phatriage_results.tsv` contains:

| Field | Meaning |
|---|---|
| `contig_id` | FASTA record identifier |
| `predicted_lifestyle` | Virulent, Temperate, or Chronic |
| `predicted_score` | Original three-class probability of the selected class |
| `temperate_marker_detected` | `true` only when a strong temperate marker is detected |
| `temperate_marker_types` | Strong and supporting marker families with evidence prefixes |

Strong evidence is restricted to integrase, excisionase/RDF, and immunity-repressor profiles. Transposase and recombinase/resolvase profiles are retained together as `supporting_recombination` evidence and do not make `temperate_marker_detected` positive by themselves.

The output directory also contains all three class probabilities, detailed HMM hits, checksums, and provenance.

## Installation

Clone this repository, then create one of the isolated environments:

```bash
mamba env create -f environments/cpu.yml
conda activate phatriage-cpu
```

or, on a CUDA system:

```bash
mamba env create -f environments/gpu.yml
conda activate phatriage-gpu
```

Download the two release assets and install them:

```bash
bash scripts/install_assets.sh \
  https://github.com/danhuangagu-ship-it/PhaTriAGE/releases/download/v0.1.0/phatriage-mini-long-full-add462-v1.tar.gz \
  https://github.com/danhuangagu-ship-it/PhaTriAGE/releases/download/v0.1.0/temperate_marker_db_hmmer3_v1.tar.gz
phatriage doctor
```

Release asset SHA-256 checksums:

| Asset | SHA-256 |
|---|---|
| `phatriage-mini-long-full-add462-v1.tar.gz` | `e4a66f541e6a956199bb0b9289a6c79f0b46158eee64dc508e125c2b8d9de466` |
| `temperate_marker_db_hmmer3_v1.tar.gz` | `8fe647cc4bd92f0a07cdc9cd38c3fe02e8cc5609ffb6cd4c759b2853e539e985` |

The asset directory defaults to `~/.cache/phatriage/assets`. Set `PHATRIAGE_ASSETS` or pass `--assets` to use another location.

## Usage

GPU mode:

```bash
phatriage run \
  --input genomes.fasta \
  --output results \
  --device cuda \
  --threads 8
```

CPU mode:

```bash
phatriage run \
  --input genomes.fasta \
  --output results \
  --device cpu \
  --batch-size 4 \
  --threads 8
```

`--device auto` uses a CUDA GPU when available and otherwise uses CPU. GPU mode changes execution speed only; sequence chunking, reverse-complement evaluation, aggregation, checkpoint, and marker thresholds remain identical. CPU prediction can be slow for large datasets.

The two stages can also run separately:

```bash
phatriage predict --input genomes.fasta --output prediction --device cuda
phatriage annotate --input genomes.fasta --output annotation --threads 8
```

## Method summary

- Input contigs are divided into consecutive 512-bp chunks, including the final short tail.
- Every chunk is evaluated in forward and reverse-complement orientation.
- Orientation probabilities are averaged per chunk, then chunk probabilities are averaged per contig.
- The selected model is the conflict-resolved `+462` Mini-long full-fine-tuning model.
- ORFs are called with pyrodigal-gv in metagenomic mode using translation table 11.
- HMMER3 searches 206 BACPHLIP profiles plus a strict PHROGs v4 subset rebuilt from official alignments.
- Retained HMM domains require independent E-value `<=1e-5` and HMM coverage `>=0.35`.

## Licensing

PhaTriAGE source code is MIT licensed. The fine-tuned model inherits the ProkBERT base model's **CC BY-NC 4.0** terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing assets or considering commercial use.
