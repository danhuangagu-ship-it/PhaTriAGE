#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from phatriage.assets import resolve_assets
from phatriage.io import iter_fasta
from phatriage.predict import predict_fasta
from phatriage.workflow import run_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--source-fasta", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--records", type=int, default=2)
    parser.add_argument("--full-pipeline", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sample = args.output / "smoke_input.fasta"
    records = []
    for record in iter_fasta(args.source_fasta):
        records.append(record)
        if len(records) == args.records:
            break
    if len(records) != args.records:
        raise ValueError("Source FASTA has too few records")
    with sample.open("w") as handle:
        for record_id, sequence in records:
            handle.write(f">{record_id}\n{sequence}\n")

    if args.full_pipeline:
        observed, provenance = run_pipeline(
            sample,
            args.output / "result",
            asset_root=args.assets,
            device=args.device,
            batch_size=16 if args.device == "cuda" else 2,
            threads=4,
        )
        probabilities = pd.read_csv(
            args.output / "result" / "raw_three_class_probabilities.tsv", sep="\t"
        )
        if list(observed.columns) != [
            "contig_id",
            "predicted_lifestyle",
            "predicted_score",
            "temperate_marker_detected",
            "temperate_marker_types",
        ]:
            raise ValueError("Unexpected primary result columns")
    else:
        assets = resolve_assets(args.assets, require_markers=False)
        probabilities, provenance = predict_fasta(
            sample,
            args.output / "prediction",
            assets,
            device=args.device,
            batch_size=2,
        )

    expected = pd.read_csv(args.reference, sep="\t", dtype={"contig_id": str})
    expected = expected.set_index("contig_id").loc[probabilities.contig_id].reset_index()
    if list(probabilities.predicted_lifestyle) != list(expected.predicted_lifestyle):
        raise AssertionError("Predicted labels differ from the frozen reference output")
    probability_columns = ["P_Virulent", "P_Temperate", "P_Chronic"]
    maximum_difference = float(
        np.abs(
            probabilities[probability_columns].to_numpy()
            - expected[probability_columns].to_numpy()
        ).max()
    )
    tolerance = 1e-5 if args.device == "cuda" else 2e-2
    if maximum_difference > tolerance:
        raise AssertionError(
            f"Maximum probability difference {maximum_difference} exceeds {tolerance}"
        )
    record = {
        "device": args.device,
        "full_pipeline": args.full_pipeline,
        "records": args.records,
        "labels_match": True,
        "maximum_probability_difference": maximum_difference,
        "tolerance": tolerance,
        "provenance": provenance,
    }
    (args.output / "SMOKE_COMPLETE.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

