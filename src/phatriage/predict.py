import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from .assets import validate_assets
from .constants import CHUNK_BP, LABELS
from .io import iter_fasta, reverse_complement, sha256
from .model import autocast_context, choose_device, load_classifier


class ChunkDataset(Dataset):
    def __init__(self, chunks, reverse_complement_eval=True):
        self.chunks = chunks
        self.rc = bool(reverse_complement_eval)

    def __len__(self):
        return len(self.chunks) * (2 if self.rc else 1)

    def __getitem__(self, index):
        n = len(self.chunks)
        is_reverse = self.rc and index >= n
        chunk_index = index - n if is_reverse else index
        sequence = self.chunks[chunk_index]
        if is_reverse:
            sequence = reverse_complement(sequence)
        return sequence, chunk_index


class Collator:
    def __init__(self, tokenizer, token_limit):
        self.tokenizer = tokenizer
        self.token_limit = int(token_limit)

    def __call__(self, batch):
        sequences, indices = zip(*batch)
        encoded = self.tokenizer(
            list(sequences), padding=True, truncation=False, return_tensors="pt"
        )
        if encoded["input_ids"].shape[1] > self.token_limit:
            raise ValueError("A 512-bp chunk exceeded the packaged model token limit")
        encoded["chunk_indices"] = torch.tensor(indices, dtype=torch.long)
        return encoded


def predict_fasta(input_fasta, output_dir, assets, device="auto", batch_size=None):
    input_fasta = Path(input_fasta).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = validate_assets(assets, require_markers=False)
    torch_device = choose_device(device)
    model, tokenizer, training = load_classifier(assets, torch_device)
    batch_size = int(batch_size or (64 if torch_device.type == "cuda" else 4))

    contig_ids, lengths, owners, chunks = [], [], [], []
    for owner, (record_id, sequence) in enumerate(iter_fasta(input_fasta)):
        if not sequence:
            raise ValueError(f"Empty sequence: {record_id}")
        contig_ids.append(record_id)
        lengths.append(len(sequence))
        for start in range(0, len(sequence), CHUNK_BP):
            chunks.append(sequence[start : start + CHUNK_BP])
            owners.append(owner)
    if not contig_ids:
        raise ValueError("No FASTA records")

    dataset = ChunkDataset(chunks, reverse_complement_eval=bool(training["rc_eval"]))
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=torch_device.type == "cuda",
        collate_fn=Collator(tokenizer, int(training.get("token_limit", 2048))),
    )
    sums = np.zeros((len(chunks), 3), dtype=np.float64)
    seen = np.zeros(len(chunks), dtype=np.int16)
    with torch.inference_mode():
        for batch in loader:
            indices = batch.pop("chunk_indices").numpy()
            tensors = {key: value.to(torch_device, non_blocking=True) for key, value in batch.items()}
            with autocast_context(torch_device):
                logits = model(**tensors)
            probabilities = torch.softmax(logits.float(), dim=1).cpu().numpy()
            np.add.at(sums, indices, probabilities)
            np.add.at(seen, indices, 1)
    expected = 2 if training["rc_eval"] else 1
    if not np.all(seen == expected):
        raise RuntimeError("Unexpected forward/reverse-complement prediction count")

    chunk_probabilities = sums / seen[:, None]
    owners = np.asarray(owners, dtype=np.int64)
    genome_probabilities = np.zeros((len(contig_ids), 3), dtype=np.float64)
    np.add.at(genome_probabilities, owners, chunk_probabilities)
    chunk_counts = np.bincount(owners, minlength=len(contig_ids))
    genome_probabilities /= chunk_counts[:, None]
    predicted = genome_probabilities.argmax(1)
    frame = pd.DataFrame(
        {
            "contig_id": contig_ids,
            "sequence_length": lengths,
            "predicted_lifestyle": [LABELS[int(index)] for index in predicted],
            "predicted_score": genome_probabilities.max(1),
            "P_Virulent": genome_probabilities[:, 0],
            "P_Temperate": genome_probabilities[:, 1],
            "P_Chronic": genome_probabilities[:, 2],
            "n_512bp_chunks": chunk_counts,
        }
    )
    output_path = output_dir / "raw_predictions.tsv"
    frame.to_csv(output_path, sep="\t", index=False)
    provenance = {
        "tool": "PhaTriage",
        "model_bundle": manifest.get("model_bundle"),
        "input_fasta_sha256": sha256(input_fasta),
        "device": str(torch_device),
        "batch_size": batch_size,
        "chunk_bp": CHUNK_BP,
        "reverse_complement_eval": bool(training["rc_eval"]),
        "aggregation": "mean forward/reverse-complement probability per chunk, then mean chunk probabilities per contig",
        "output_sha256": sha256(output_path),
    }
    marker = output_dir / "PREDICTION_COMPLETE.json"
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(json.dumps(provenance, indent=2) + "\n")
    os.replace(temporary, marker)
    return frame, provenance
