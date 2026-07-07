from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .text import sanitize, tokens


@dataclass
class IntentModel:
    labels: list[str]
    label_counts: dict[str, int]
    token_logprob: dict[str, dict[str, float]]
    unknown_logprob: dict[str, float]
    priors: dict[str, float]
    responses: dict[str, str]
    categories: dict[str, str]

    def predict(self, text: str) -> dict:
        clean, _ = sanitize(text)
        ts = tokens(clean)
        scores = {}
        for label in self.labels:
            score = self.priors[label]
            lookup = self.token_logprob[label]
            unknown = self.unknown_logprob[label]
            for token in ts:
                score += lookup.get(token, unknown)
            scores[label] = score
        best = max(scores, key=scores.get)
        ordered = sorted(scores.values(), reverse=True)
        margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
        confidence = 1 / (1 + math.exp(-min(20.0, margin)))
        return {"intent": best, "category": self.categories.get(best, ""), "confidence": confidence, "response": self.responses.get(best, "")}

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "IntentModel":
        return cls(
            labels=list(data["labels"]),
            label_counts={str(k): int(v) for k, v in data["label_counts"].items()},
            token_logprob={label: {k: float(v) for k, v in values.items()} for label, values in data["token_logprob"].items()},
            unknown_logprob={str(k): float(v) for k, v in data["unknown_logprob"].items()},
            priors={str(k): float(v) for k, v in data["priors"].items()},
            responses={str(k): str(v) for k, v in data["responses"].items()},
            categories={str(k): str(v) for k, v in data["categories"].items()},
        )

    def save(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "IntentModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _row_text(row: dict) -> str:
    return str(row.get("instruction") or row.get("question") or row.get("text") or "")


def train(input_path: str | Path, out_path: str | Path, *, alpha: float = 0.3) -> dict:
    rows = [json.loads(line) for line in Path(input_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("training data is empty")
    counts: dict[str, Counter] = defaultdict(Counter)
    label_counts: Counter[str] = Counter()
    response_counts: dict[str, Counter] = defaultdict(Counter)
    categories: dict[str, str] = {}
    vocab = Counter()
    for row in rows:
        label = str(row.get("intent") or row.get("label") or row.get("category") or "unknown")
        category = str(row.get("category") or "")
        clean, _ = sanitize(_row_text(row))
        ts = tokens(clean)
        if not ts:
            continue
        counts[label].update(ts)
        vocab.update(ts)
        label_counts[label] += 1
        response = str(row.get("response") or row.get("answer") or "")
        if response:
            response_counts[label][response] += 1
        if category:
            categories[label] = category
    labels = sorted(label_counts)
    if len(labels) < 2:
        raise ValueError("training data must contain at least two intents")
    total_docs = sum(label_counts.values())
    vocab_size = max(1, len(vocab))
    token_logprob = {}
    unknown_logprob = {}
    priors = {}
    for label in labels:
        total = sum(counts[label].values())
        token_logprob[label] = {token: math.log((counts[label].get(token, 0) + alpha) / (total + alpha * vocab_size)) for token in vocab}
        unknown_logprob[label] = math.log(alpha / (total + alpha * vocab_size))
        priors[label] = math.log((label_counts[label] + alpha) / (total_docs + alpha * len(labels)))
    responses = {label: (response_counts[label].most_common(1)[0][0] if response_counts[label] else "سأراجع طلبك وأعود لك بالتفاصيل.") for label in labels}
    model = IntentModel(labels, dict(label_counts), token_logprob, unknown_logprob, priors, responses, categories)
    model.save(out_path)
    return {"rows": len(rows), "intents": len(labels), "features": len(vocab), "out": str(Path(out_path).resolve())}

