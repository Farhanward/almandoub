from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from pathlib import Path

from .agent import decide
from .model import IntentModel


def _p(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))]


def evaluate(input_path: str | Path, model_path: str | Path, *, repeat: int = 1) -> dict:
    model = IntentModel.load(model_path)
    rows = [json.loads(line) for line in Path(input_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    correct = errors = escalations = 0
    latencies = []
    started = time.perf_counter()
    tracemalloc.start()
    for _ in range(repeat):
        for row in rows:
            t0 = time.perf_counter()
            try:
                result = decide(str(row.get("instruction") or ""), model)
                if result["intent"] == row.get("intent"):
                    correct += 1
                if result["action"] == "ESCALATE":
                    escalations += 1
            except Exception:
                errors += 1
            latencies.append((time.perf_counter() - t0) * 1000)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    processed = len(rows) * repeat
    return {
        "input": str(Path(input_path).resolve()),
        "records": len(rows),
        "repeat": repeat,
        "processed": processed,
        "accuracy": correct / processed if processed else 0.0,
        "correct": correct,
        "escalations": escalations,
        "errors": errors,
        "latency_ms": {"mean": statistics.fmean(latencies) if latencies else 0.0, "p99": _p(latencies, 99), "max": max(latencies) if latencies else 0.0},
        "memory_mb": {"current": current / 1_000_000, "peak": peak / 1_000_000},
        "elapsed_seconds": time.perf_counter() - started,
        "collapse_check": {"passed": errors == 0, "criteria": "errors == 0"},
    }

