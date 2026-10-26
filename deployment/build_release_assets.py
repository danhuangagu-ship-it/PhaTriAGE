#!/usr/bin/env python3
"""Assemble reproducible PhaTriage runtime bundles from exact server artifacts."""
import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path


MODEL_VERSION = "phatriage-mini-long-full-add462-v1"
MARKER_VERSION = "temperate_marker_db_hmmer3_v1"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy(source, target):
    source = Path(source)
    target = Path(target)
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    staging = output_root / "staging"
    releases = output_root / "bundles"
    if staging.exists() or releases.exists():
        raise FileExistsError("Release staging or bundle directory already exists")
    staging.mkdir(parents=True)
    releases.mkdir(parents=True)

    base = Path("/ourdisk/hpc/ieg/dont_archive/danhuang/software-data/nucleotide_LMs/prokbert-mini-long")
    final = Path(
        "/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/"
        "0-7.roux2019-augmentation-20261021/runs/"
        "c8r462_mini_long_full_mean_linear_512_s42_v1/seed_42/final_fit"
    )
    remote_code = Path(
        "/home/danhuang/.cache/huggingface/modules/transformers_modules/neuralbioinfo/"
        "nbrg_hyphen_transformers/366d9336b6b89d7c1feddf56d9b01be8065ccc43"
    )
    marker_source = Path(
        "/ourdisk/hpc/ieg/dont_archive/danhuang/projects/chronic_virus/"
        "0-8.manuscript-final-analysis-20261026/06_temperate_gene_annotation/"
        "databases/temperate_marker_db_hmmer3_v1"
    )
    model_out = staging / "model" / MODEL_VERSION
    base_out = model_out / "base_model"
    marker_out = staging / "markers" / MARKER_VERSION

    base_files = [
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "README.md",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.txt",
    ]
    for name in base_files:
        copy(base / name, base_out / name)
    copy(remote_code / "models.py", base_out / "models.py")
    copy(remote_code / "tokenizer.py", base_out / "tokenizer.py")
    (base_out / "__init__.py").write_text("")

    config_path = base_out / "config.json"
    config = json.loads(config_path.read_text())
    config["auto_map"] = {
        key: value.split("--", 1)[-1] for key, value in config["auto_map"].items()
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    tokenizer_path = base_out / "tokenizer_config.json"
    tokenizer = json.loads(tokenizer_path.read_text())
    tokenizer["auto_map"]["AutoTokenizer"][0] = tokenizer["auto_map"]["AutoTokenizer"][0].split("--", 1)[-1]
    tokenizer_path.write_text(json.dumps(tokenizer, indent=2) + "\n")

    copy(final / "final_state.pt", model_out / "final_state.pt")
    training = json.loads((final / "config.json").read_text())
    training["model_path"] = "base_model"
    training["token_limit"] = 2048
    training["selected_release_model"] = True
    training["source_checkpoint_sha256"] = sha256(final / "final_state.pt")
    (model_out / "training_config.json").write_text(json.dumps(training, indent=2) + "\n")
    copy(final / "_COMPLETE.json", model_out / "training_complete.json")
    copy(final / "model_info.json", model_out / "model_info.json")

    marker_files = [
        "COMPLETE.json",
        "combined_temperate_marker_profiles.hmm",
        "combined_temperate_marker_profiles.hmm.h3f",
        "combined_temperate_marker_profiles.hmm.h3i",
        "combined_temperate_marker_profiles.hmm.h3m",
        "combined_temperate_marker_profiles.hmm.h3p",
        "profile_metadata.tsv",
        "phrogs_v4_temperate_marker_profiles.tsv",
    ]
    for name in marker_files:
        copy(marker_source / name, marker_out / name)

    hash_paths = [
        Path("model") / MODEL_VERSION / "base_model" / name for name in base_files
    ] + [
        Path("model") / MODEL_VERSION / "base_model" / "models.py",
        Path("model") / MODEL_VERSION / "base_model" / "tokenizer.py",
        Path("model") / MODEL_VERSION / "final_state.pt",
        Path("model") / MODEL_VERSION / "training_config.json",
    ] + [Path("markers") / MARKER_VERSION / name for name in marker_files]
    manifest = {
        "schema_version": 1,
        "model_bundle": MODEL_VERSION,
        "marker_database": MARKER_VERSION,
        "classification": {
            "labels": ["Virulent", "Temperate", "Chronic"],
            "chunk_bp": 512,
            "reverse_complement_eval": True,
            "aggregation": "mean orientations per chunk; mean chunks per contig",
        },
        "marker_evidence": {
            "strong": ["excisionase_rdf", "immunity_repressor", "integrase"],
            "supporting_recombination": ["recombinase_resolvase", "transposase"],
        },
        "sha256": {str(path): sha256(staging / path) for path in hash_paths},
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    model_tar = releases / f"{MODEL_VERSION}.tar.gz"
    with tarfile.open(model_tar, "w:gz") as archive:
        archive.add(model_out, arcname=str(Path("model") / MODEL_VERSION))
        archive.add(staging / "manifest.json", arcname="manifest.json")
    marker_tar = releases / f"{MARKER_VERSION}.tar.gz"
    with tarfile.open(marker_tar, "w:gz") as archive:
        archive.add(marker_out, arcname=str(Path("markers") / MARKER_VERSION))
        archive.add(staging / "manifest.json", arcname="manifest.json")
    checksums = {
        model_tar.name: sha256(model_tar),
        marker_tar.name: sha256(marker_tar),
    }
    (releases / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2) + "\n")
    print(json.dumps({"manifest": manifest, "bundle_sha256": checksums}, indent=2))


if __name__ == "__main__":
    main()

