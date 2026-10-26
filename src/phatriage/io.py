import gzip
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def open_text(path: Path):
    return gzip.open(path, "rt") if str(path).endswith(".gz") else Path(path).open("rt")


def iter_fasta(path: Path):
    name = None
    pieces = []
    seen = set()
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(pieces).upper()
                name = line[1:].split()[0]
                if not name:
                    raise ValueError(f"Empty FASTA identifier at line {line_number}")
                if name in seen:
                    raise ValueError(f"Duplicate FASTA identifier: {name}")
                seen.add(name)
                pieces = []
            else:
                if name is None:
                    raise ValueError(f"Sequence before first FASTA header at line {line_number}")
                pieces.append(line)
    if name is not None:
        yield name, "".join(pieces).upper()


_RC = str.maketrans("ACGTNacgtn", "TGCANtgcan")


def reverse_complement(sequence: str) -> str:
    return sequence.translate(_RC)[::-1]

