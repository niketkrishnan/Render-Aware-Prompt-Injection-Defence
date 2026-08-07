"""
Layer 3 — Semantic Injection Classifier (DistilBERT).

Loads a DistilBERT model fine-tuned on HackAPrompt and scores free text for
prompt-injection intent, independent of how that text was rendered/hidden.

Fine-tuning code (the training loop used to produce ./saved_model) lives in
notebooks/ — this module only covers inference, which is what the fusion
pipeline needs at request time.
"""

from __future__ import annotations

import torch
from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

DEFAULT_MODEL_DIR = "./saved_model"
MAX_TOKEN_LENGTH = 128


class SemanticClassifier:
    def __init__(self, model_dir: str = DEFAULT_MODEL_DIR, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = DistilBertTokenizerFast.from_pretrained(model_dir)
        self.model = DistilBertForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def score(self, text: str) -> float:
        """Return P(injection) for a single string, rounded to 4 decimals."""
        inputs = self.tokenizer(
            [text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_TOKEN_LENGTH,
        ).to(self.device)
        outputs = self.model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)
        return round(probs[:, 1].item(), 4)

    @torch.no_grad()
    def score_batch(self, texts: list[str], batch_size: int = 32) -> list[float]:
        """Batched scoring for dataset construction / bulk evaluation."""
        scores: list[float] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=MAX_TOKEN_LENGTH,
            ).to(self.device)
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            scores.extend(probs[:, 1].cpu().tolist())
        return scores
