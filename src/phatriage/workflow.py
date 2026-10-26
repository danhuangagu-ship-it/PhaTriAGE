import json
import os
from pathlib import Path

import pandas as pd

from .assets import resolve_assets, validate_assets
from .io import sha256
from .markers import annotate_fasta
from .predict import predict_fasta


def merge_results(predictions, markers, output_path):
    if predictions.contig_id.duplicated().any() or markers.contig_id.duplicated().any():
        raise ValueError("Duplicate contig IDs in prediction or annotation table")
    if set(predictions.contig_id) != set(markers.contig_id):
        raise ValueError("Prediction and annotation contig membership differ")
    merged = predictions.merge(markers, on="contig_id", validate="one_to_one", sort=False)
    primary = merged[
        [
            "contig_id",
            "predicted_lifestyle",
            "predicted_score",
            "temperate_marker_detected",
            "temperate_marker_types",
        ]
    ]
    primary.to_csv(output_path, sep="\t", index=False)
    return primary


def run_pipeline(
    input_fasta,
    output_dir,
    asset_root=None,
    device="auto",
    batch_size=None,
    threads=4,
    keep_intermediates=False,
):
    output_dir = Path(output_dir).resolve()
    prediction_dir = output_dir / "prediction"
    annotation_dir = output_dir / "annotation"
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = resolve_assets(asset_root, require_markers=True)
    manifest = validate_assets(assets)
    predictions, prediction_record = predict_fasta(
        input_fasta, prediction_dir, assets, device=device, batch_size=batch_size
    )
    markers, _, annotation_record = annotate_fasta(
        input_fasta,
        annotation_dir,
        assets,
        threads=threads,
        keep_intermediates=keep_intermediates,
    )
    final_path = output_dir / "phatriage_results.tsv"
    final = merge_results(predictions, markers, final_path)
    raw_path = output_dir / "raw_three_class_probabilities.tsv"
    predictions.to_csv(raw_path, sep="\t", index=False)
    record = {
        "tool": "PhaTriage",
        "asset_manifest": manifest,
        "prediction": prediction_record,
        "annotation": annotation_record,
        "outputs": {
            "phatriage_results.tsv": sha256(final_path),
            "raw_three_class_probabilities.tsv": sha256(raw_path),
            "temperate_marker_hits.tsv": sha256(annotation_dir / "temperate_marker_hits.tsv"),
        },
    }
    complete = output_dir / "PHATRIAGE_COMPLETE.json"
    temporary = complete.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    os.replace(temporary, complete)
    return final, record

