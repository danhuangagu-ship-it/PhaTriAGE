import json
from dataclasses import dataclass
from pathlib import Path

from .constants import MARKER_DB_VERSION, MODEL_BUNDLE_VERSION, default_asset_root
from .io import sha256


@dataclass(frozen=True)
class Assets:
    root: Path
    model_base: Path
    checkpoint: Path
    training_config: Path
    marker_db: Path
    manifest: Path


def resolve_assets(root=None, require_markers=True) -> Assets:
    root = Path(root).expanduser().resolve() if root else default_asset_root()
    manifest = root / "manifest.json"
    model_root = root / "model" / MODEL_BUNDLE_VERSION
    marker_db = root / "markers" / MARKER_DB_VERSION
    assets = Assets(
        root=root,
        model_base=model_root / "base_model",
        checkpoint=model_root / "final_state.pt",
        training_config=model_root / "training_config.json",
        marker_db=marker_db,
        manifest=manifest,
    )
    required = [assets.manifest, assets.model_base / "config.json", assets.checkpoint, assets.training_config]
    if require_markers:
        required.extend(
            [
                marker_db / "COMPLETE.json",
                marker_db / "combined_temperate_marker_profiles.hmm",
                marker_db / "profile_metadata.tsv",
            ]
        )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "PhaTriage assets are incomplete. Missing:\n  "
            + "\n  ".join(missing)
            + "\nDownload and unpack the release assets, then set PHATRIAGE_ASSETS."
        )
    return assets


def validate_assets(assets: Assets, require_markers=True) -> dict:
    manifest = json.loads(assets.manifest.read_text())
    failures = []
    for relative, expected in manifest.get("sha256", {}).items():
        if not require_markers and relative.startswith("markers/"):
            continue
        path = assets.root / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
        else:
            observed = sha256(path)
            if observed != expected:
                failures.append(f"checksum mismatch: {relative}")
    if failures:
        raise ValueError("Asset validation failed:\n  " + "\n  ".join(failures))
    return manifest
