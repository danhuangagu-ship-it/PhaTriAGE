# PhaTriAGE method and evidence rules

## Classification

PhaTriAGE uses the selected ProkBERT Mini-long model fully fine-tuned on the conflict-resolved `+462` three-class dataset. Eight genomes with conflicting empirical and bioinformatic labels were excluded before clustering and data splitting. The model retains its original end-to-end linear classification head.

Each input contig is divided into consecutive non-overlapping 512-bp chunks. The final short tail is retained. Forward and reverse-complement probabilities are averaged for each chunk, and the chunk probabilities are then averaged per contig. The maximum of the three unmodified probabilities determines the Virulent, Temperate, or Chronic assignment and `predicted_score`.

CPU and GPU modes load the same weights and use the same tokenizer, chunk membership, reverse-complement handling, and aggregation. CUDA inference uses bfloat16 autocasting, matching the original final-model evaluation; CPU inference uses float32.

## Temperate-marker annotation

ORFs are called with pyrodigal-gv in metagenomic mode using translation table 11. HMMER3 searches a versioned database containing the official BACPHLIP 206 lysogeny-associated profiles plus 177 PHROGs v4 profiles rebuilt with `hmmbuild` from official multiple-sequence alignments.

Domains are retained when their independent E-value is at most `1e-5` and HMM coverage is at least `0.35`.

Evidence is reported in two tiers:

- `strong_temperate`: integrase, excisionase/RDF, and immunity-repressor profiles. At least one such hit makes `temperate_marker_detected=true`.
- `supporting_recombination`: transposase and recombinase/resolvase profiles. These hits are retained in `temperate_marker_types` but do not make the Boolean field positive by themselves.

All remaining auxiliary families remain available in the detailed HMM-hit table. Marker evidence is generated after classification and never changes predicted probabilities or labels.

