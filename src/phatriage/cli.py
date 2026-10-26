import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

import torch

from . import __version__
from .assets import resolve_assets, validate_assets
from .markers import annotate_fasta
from .predict import predict_fasta
from .workflow import run_pipeline


def build_parser():
    parser = argparse.ArgumentParser(
        prog="phatriage",
        description="Phage Tri-class Lifestyle Assignment with Genomic Evidence",
    )
    parser.add_argument("--version", action="version", version=f"PhaTriAGE {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run lifestyle prediction and marker annotation")
    run.add_argument("--input", required=True, type=Path, help="Input nucleotide FASTA or FASTA.gz")
    run.add_argument("--output", required=True, type=Path, help="Output directory")
    run.add_argument("--assets", type=Path, help="Asset root; defaults to PHATRIAGE_ASSETS")
    run.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    run.add_argument("--batch-size", type=int)
    run.add_argument("--threads", type=int, default=4)
    run.add_argument("--keep-intermediates", action="store_true")

    predict = subparsers.add_parser("predict", help="Run only three-class lifestyle prediction")
    predict.add_argument("--input", required=True, type=Path)
    predict.add_argument("--output", required=True, type=Path)
    predict.add_argument("--assets", type=Path)
    predict.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    predict.add_argument("--batch-size", type=int)

    annotate = subparsers.add_parser("annotate", help="Run only ORF/HMM marker annotation")
    annotate.add_argument("--input", required=True, type=Path)
    annotate.add_argument("--output", required=True, type=Path)
    annotate.add_argument("--assets", type=Path)
    annotate.add_argument("--threads", type=int, default=4)
    annotate.add_argument("--keep-intermediates", action="store_true")

    doctor = subparsers.add_parser("doctor", help="Validate runtime and installed assets")
    doctor.add_argument("--assets", type=Path)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        assets = resolve_assets(args.assets, require_markers=True)
        manifest = validate_assets(assets)
        report = {
            "phatriage": __version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_runtime": torch.version.cuda,
            "pyrodigal_gv": shutil.which("pyrodigal-gv"),
            "hmmsearch": shutil.which("hmmsearch"),
            "asset_root": str(assets.root),
            "asset_manifest": manifest,
        }
        if not report["pyrodigal_gv"] or not report["hmmsearch"]:
            raise RuntimeError("pyrodigal-gv and hmmsearch must both be on PATH")
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "predict":
        assets = resolve_assets(args.assets, require_markers=False)
        frame, _ = predict_fasta(
            args.input, args.output, assets, device=args.device, batch_size=args.batch_size
        )
        print(f"Predicted {len(frame)} contigs: {args.output}")
        return 0
    if args.command == "annotate":
        assets = resolve_assets(args.assets, require_markers=True)
        frame, hits, _ = annotate_fasta(
            args.input,
            args.output,
            assets,
            threads=args.threads,
            keep_intermediates=args.keep_intermediates,
        )
        print(f"Annotated {len(frame)} contigs with {len(hits)} retained HMM hits: {args.output}")
        return 0
    frame, _ = run_pipeline(
        args.input,
        args.output,
        asset_root=args.assets,
        device=args.device,
        batch_size=args.batch_size,
        threads=args.threads,
        keep_intermediates=args.keep_intermediates,
    )
    print(f"Completed PhaTriAGE for {len(frame)} contigs: {args.output / 'phatriage_results.tsv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
