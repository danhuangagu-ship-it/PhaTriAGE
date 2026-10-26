from pathlib import Path

import pandas as pd

from phatriage.io import iter_fasta, reverse_complement
from phatriage.markers import evidence_tier
from phatriage.workflow import merge_results


def test_fasta_and_reverse_complement(tmp_path):
    fasta = tmp_path / "input.fa"
    fasta.write_text(">a description\nACGTN\n>b\nTTAA\n")
    assert list(iter_fasta(fasta)) == [("a", "ACGTN"), ("b", "TTAA")]
    assert reverse_complement("ACGTN") == "NACGT"


def test_marker_tiers():
    assert evidence_tier("integrase") == "strong_temperate"
    assert evidence_tier("immunity_repressor") == "strong_temperate"
    assert evidence_tier("transposase") == "supporting_recombination"
    assert evidence_tier("recombinase_resolvase") == "supporting_recombination"
    assert evidence_tier("partition_maintenance") == "other_auxiliary"


def test_primary_output_columns(tmp_path):
    predictions = pd.DataFrame(
        {
            "contig_id": ["a"],
            "predicted_lifestyle": ["Chronic"],
            "predicted_score": [0.9],
            "P_Virulent": [0.02],
            "P_Temperate": [0.08],
            "P_Chronic": [0.9],
        }
    )
    markers = pd.DataFrame(
        {
            "contig_id": ["a"],
            "temperate_marker_detected": [False],
            "temperate_marker_types": ["supporting|transposase:phrog_x"],
        }
    )
    output = tmp_path / "result.tsv"
    merged = merge_results(predictions, markers, output)
    assert list(merged.columns) == [
        "contig_id",
        "predicted_lifestyle",
        "predicted_score",
        "temperate_marker_detected",
        "temperate_marker_types",
    ]

