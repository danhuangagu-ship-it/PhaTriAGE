import json
from contextlib import nullcontext

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer


class PhaTriageClassifier(nn.Module):
    """Exact Mini-long mean-pooling linear-head architecture used for the final fit."""

    def __init__(self, base_model, dropout=0.1):
        super().__init__()
        self.backbone = base_model
        hidden_size = int(base_model.config.hidden_size)
        self.head = nn.Sequential(nn.Dropout(float(dropout)), nn.Linear(hidden_size, 3))

    def forward(self, input_ids, attention_mask, **kwargs):
        output = self.backbone(input_ids=input_ids, attention_mask=attention_mask, **kwargs)
        hidden = output.last_hidden_state if hasattr(output, "last_hidden_state") else output[0]
        mask = attention_mask.unsqueeze(-1)
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp_min(1)
        return self.head(pooled)


def choose_device(requested: str) -> torch.device:
    requested = requested.lower()
    if requested == "auto":
        requested = "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA mode was requested, but torch.cuda.is_available() is false")
    if requested not in {"cpu", "cuda"}:
        raise ValueError("device must be auto, cpu, or cuda")
    return torch.device(requested)


def load_classifier(assets, device: torch.device):
    training = json.loads(assets.training_config.read_text())
    if training.get("model") != "prokbert_mini_long" or training.get("mode") != "full":
        raise ValueError("Unexpected packaged model configuration")
    if training.get("pooling") != "mean" or training.get("head") != "linear":
        raise ValueError("Packaged model must use mean pooling and a linear head")
    tokenizer = AutoTokenizer.from_pretrained(
        assets.model_base, trust_remote_code=True, local_files_only=True
    )
    backbone = AutoModel.from_pretrained(
        assets.model_base, trust_remote_code=True, local_files_only=True
    )
    model = PhaTriageClassifier(backbone, training.get("dropout", 0.1))
    state = torch.load(assets.checkpoint, map_location="cpu", weights_only=False)
    if state.get("format") != "trainable_parameters_only":
        raise ValueError("Unexpected final checkpoint format")
    model.load_state_dict(state["model"], strict=True)
    model.eval().to(device)
    return model, tokenizer, training


def autocast_context(device: torch.device):
    if device.type == "cuda":
        return torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=True)
    return nullcontext()

