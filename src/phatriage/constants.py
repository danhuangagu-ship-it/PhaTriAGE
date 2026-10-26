from pathlib import Path

LABELS = ("Virulent", "Temperate", "Chronic")
CHUNK_BP = 512
MODEL_BUNDLE_VERSION = "phatriage-mini-long-full-add462-v1"
MARKER_DB_VERSION = "temperate_marker_db_hmmer3_v1"
STRONG_MARKER_TYPES = frozenset({"integrase", "excisionase_rdf", "immunity_repressor"})
SUPPORTING_RECOMBINATION_TYPES = frozenset({"transposase", "recombinase_resolvase"})


def default_asset_root() -> Path:
    import os

    configured = os.environ.get("PHATRIAGE_ASSETS")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".cache" / "phatriage" / "assets"

