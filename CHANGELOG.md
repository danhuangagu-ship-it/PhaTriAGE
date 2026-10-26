# Changelog

## 0.1.0 — 2026-10-26

- Initial PhaTriAGE release.
- Three-class Virulent/Temperate/Chronic prediction with the selected conflict-resolved `+462` ProkBERT Mini-long full-fine-tuning model.
- Matched CPU and CUDA inference paths using identical chunking, reverse-complement evaluation, probability aggregation, and checkpoint.
- Independent pyrodigal-gv/HMMER3 annotation against 206 BACPHLIP profiles and a strict PHROGs v4 subset.
- Strong temperate evidence restricted to integrase, excisionase/RDF, and immunity repressor profiles.
- Transposase and recombinase/resolvase retained together as supporting recombination evidence.
- Primary five-column per-contig output plus raw probabilities, detailed HMM hits, hashes, and provenance.

