from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DATASET = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
ROWS_URL = "https://datasets-server.huggingface.co/rows"


def _get(url: str, retries: int = 6) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "almandoub-local-benchmark/0.1"})
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code != 429 or attempt == retries - 1:
                raise
            time.sleep(min(60.0, 5.0 * (attempt + 1)))
    raise RuntimeError("unreachable retry state")


def fetch_bitext(out_path: str | Path, *, limit: int = 12000, page_size: int = 100) -> dict[str, Any]:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    intents: dict[str, int] = {}
    with out.open("w", encoding="utf-8") as handle:
        for offset in range(0, limit, page_size):
            length = min(page_size, limit - offset)
            url = f"{ROWS_URL}?{urlencode({'dataset': DATASET, 'config': 'default', 'split': 'train', 'offset': offset, 'length': length})}"
            page = _get(url)
            for item in page.get("rows", []):
                row = dict(item.get("row") or {})
                record = {
                    "instruction": row.get("instruction") or row.get("utterance") or row.get("text") or "",
                    "response": row.get("response") or "",
                    "category": row.get("category") or "",
                    "intent": row.get("intent") or "",
                    "row_idx": item.get("row_idx"),
                    "dataset": DATASET,
                }
                if not record["instruction"] or not record["intent"]:
                    continue
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                intents[record["intent"]] = intents.get(record["intent"], 0) + 1
                rows += 1
    return {"dataset": DATASET, "out": str(out.resolve()), "rows": rows, "intents": len(intents)}

