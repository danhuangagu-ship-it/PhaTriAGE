import json
import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

import pandas as pd

from .constants import STRONG_MARKER_TYPES, SUPPORTING_RECOMBINATION_TYPES
from .io import iter_fasta, sha256


HIT_COLUMNS = [
    "contig_id",
    "orf_id",
    "method",
    "marker_type",
    "marker_family",
    "evidence_tier",
    "profile_source",
    "profile_annotation",
    "i_evalue",
    "bitscore",
    "protein_coverage",
    "hmm_coverage",
]


def evidence_tier(marker_type):
    if marker_type in STRONG_MARKER_TYPES:
        return "strong_temperate"
    if marker_type in SUPPORTING_RECOMBINATION_TYPES:
        return "supporting_recombination"
    return "other_auxiliary"


def protein_to_contig(protein_id):
    match = re.match(r"^(.*)_([0-9]+)$", protein_id)
    if not match:
        raise ValueError(f"Unexpected pyrodigal protein identifier: {protein_id}")
    return match.group(1)


def parse_domtblout(path, metadata, max_i_evalue=1e-5, min_hmm_coverage=0.35):
    rows = []
    with Path(path).open() as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 22:
                continue
            target = fields[0]
            target_length = int(fields[2])
            profile_id = fields[3]
            profile_length = int(fields[5])
            i_evalue = float(fields[12])
            bitscore = float(fields[13])
            hmm_from, hmm_to = int(fields[15]), int(fields[16])
            ali_from, ali_to = int(fields[17]), int(fields[18])
            hmm_coverage = (hmm_to - hmm_from + 1) / profile_length
            protein_coverage = (ali_to - ali_from + 1) / target_length
            if i_evalue > max_i_evalue or hmm_coverage < min_hmm_coverage:
                continue
            if profile_id not in metadata:
                raise ValueError(f"Profile missing from metadata: {profile_id}")
            profile = metadata[profile_id]
            marker_type = profile["marker_type"]
            rows.append(
                {
                    "contig_id": protein_to_contig(target),
                    "orf_id": target,
                    "method": "HMMER3",
                    "marker_type": marker_type,
                    "marker_family": profile_id,
                    "evidence_tier": evidence_tier(marker_type),
                    "profile_source": profile["source"],
                    "profile_annotation": profile["annotation"],
                    "i_evalue": i_evalue,
                    "bitscore": bitscore,
                    "protein_coverage": protein_coverage,
                    "hmm_coverage": hmm_coverage,
                }
            )
    return rows


def _require_executable(name):
    executable = shutil.which(name)
    if not executable:
        raise FileNotFoundError(f"Required executable is not on PATH: {name}")
    return executable


def _write_normalized_fasta(input_fasta, output_fasta):
    identifiers = []
    with Path(output_fasta).open("w") as output:
        for record_id, sequence in iter_fasta(input_fasta):
            identifiers.append(record_id)
            output.write(f">{record_id}\n{sequence}\n")
    return identifiers


def annotate_fasta(input_fasta, output_dir, assets, threads=4, keep_intermediates=False):
    input_fasta = Path(input_fasta).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pyrodigal_gv = _require_executable("pyrodigal-gv")
    hmmsearch = _require_executable("hmmsearch")
    hmm_path = assets.marker_db / "combined_temperate_marker_profiles.hmm"
    metadata_path = assets.marker_db / "profile_metadata.tsv"
    db_complete = assets.marker_db / "COMPLETE.json"
    for path in (hmm_path, metadata_path, db_complete):
        if not path.is_file():
            raise FileNotFoundError(path)

    profile_table = pd.read_csv(metadata_path, sep="\t", dtype=str).fillna("")
    if profile_table.profile_id.duplicated().any():
        raise ValueError("Duplicate profile IDs in marker metadata")
    metadata = profile_table.set_index("profile_id").to_dict("index")

    normalized = output_dir / "input.normalized.fna"
    proteins = output_dir / "orfs.faa"
    genes = output_dir / "orfs.fna"
    gff = output_dir / "orfs.gff"
    domtbl = output_dir / "temperate_markers.domtblout"
    identifiers = _write_normalized_fasta(input_fasta, normalized)
    subprocess.run(
        [
            pyrodigal_gv,
            "-i",
            str(normalized),
            "-a",
            str(proteins),
            "-d",
            str(genes),
            "-o",
            str(gff),
            "-f",
            "gff",
            "-p",
            "meta",
            "-g",
            "11",
            "-m",
            "-j",
            str(int(threads)),
        ],
        check=True,
    )
    subprocess.run(
        [
            hmmsearch,
            "--cpu",
            str(int(threads)),
            "--noali",
            "--domtblout",
            str(domtbl),
            "-E",
            "1e-3",
            "--domE",
            "1e-3",
            str(hmm_path),
            str(proteins),
        ],
        check=True,
    )
    hits = parse_domtblout(domtbl, metadata)
    hit_frame = pd.DataFrame(hits, columns=HIT_COLUMNS)
    hit_path = output_dir / "temperate_marker_hits.tsv"
    hit_frame.to_csv(hit_path, sep="\t", index=False)

    strong = defaultdict(set)
    supporting = defaultdict(set)
    for hit in hits:
        label = f'{hit["marker_type"]}:{hit["marker_family"]}'
        if hit["evidence_tier"] == "strong_temperate":
            strong[hit["contig_id"]].add(label)
        elif hit["evidence_tier"] == "supporting_recombination":
            supporting[hit["contig_id"]].add(label)
    summary = pd.DataFrame(
        {
            "contig_id": identifiers,
            "temperate_marker_detected": [bool(strong[item]) for item in identifiers],
            "temperate_marker_types": [
                ";".join(
                    [f"strong|{value}" for value in sorted(strong[item])]
                    + [f"supporting|{value}" for value in sorted(supporting[item])]
                )
                for item in identifiers
            ],
        }
    )
    summary_path = output_dir / "temperate_marker_summary.tsv"
    summary.to_csv(summary_path, sep="\t", index=False)
    provenance = {
        "input_fasta_sha256": sha256(input_fasta),
        "database_manifest_sha256": sha256(db_complete),
        "orf_caller": "pyrodigal-gv meta mode; translation table 11",
        "search_method": "HMMER3 hmmsearch",
        "hit_threshold": "independent E-value <=1e-5 and HMM coverage >=0.35",
        "strong_marker_types": sorted(STRONG_MARKER_TYPES),
        "supporting_recombination_types": sorted(SUPPORTING_RECOMBINATION_TYPES),
        "n_contigs": len(summary),
        "n_strong_positive": int(summary.temperate_marker_detected.sum()),
        "n_marker_hits": len(hit_frame),
        "hits_sha256": sha256(hit_path),
        "summary_sha256": sha256(summary_path),
    }
    marker = output_dir / "ANNOTATION_COMPLETE.json"
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(provenance, indent=2) + "\n")
    os.replace(temporary, marker)
    if not keep_intermediates:
        for path in (normalized, proteins, genes, gff, domtbl):
            path.unlink(missing_ok=True)
    return summary, hit_frame, provenance

