from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import decide
from .batch import evaluate
from .datasets import fetch_bitext
from .model import IntentModel, train
from .reports import markdown


def _write_json(path: str | Path, data: dict) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="almandoub", description="المندوب: موظف محادثات محلي.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    dl = sub.add_parser("download")
    dl.add_argument("--out", default="data/external/bitext_customer_support_12000.jsonl")
    dl.add_argument("--limit", type=int, default=12000)
    tr = sub.add_parser("train")
    tr.add_argument("--input", default="data/external/bitext_customer_support_12000.jsonl")
    tr.add_argument("--out", default="models/almandoub_intent_model.json")
    handle = sub.add_parser("handle")
    handle.add_argument("--model", default="models/almandoub_intent_model.json")
    handle.add_argument("--message", required=True)
    batch = sub.add_parser("batch")
    batch.add_argument("--input", default="data/external/bitext_customer_support_12000.jsonl")
    batch.add_argument("--model", default="models/almandoub_intent_model.json")
    batch.add_argument("--json-out", default="reports/almandoub_benchmark.json")
    batch.add_argument("--report", default="reports/almandoub_benchmark.md")
    stress = sub.add_parser("stress")
    stress.add_argument("--input", default="data/external/bitext_customer_support_12000.jsonl")
    stress.add_argument("--model", default="models/almandoub_intent_model.json")
    stress.add_argument("--repeat", type=int, default=3)
    stress.add_argument("--json-out", default="reports/almandoub_stress.json")
    stress.add_argument("--report", default="reports/almandoub_stress.md")
    serve = sub.add_parser("serve")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    sub.add_parser("version")
    args = parser.parse_args(argv)
    if args.cmd == "serve":
        from .service import run_server

        run_server(host=args.host, port=args.port)
        return 0
    if args.cmd == "version":
        from .version import __version__

        print(json.dumps({"service": "almandoub", "version": __version__}, ensure_ascii=False))
        return 0
    if args.cmd == "download":
        print(json.dumps(fetch_bitext(args.out, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "train":
        print(json.dumps(train(args.input, args.out), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "handle":
        model = IntentModel.load(args.model)
        print(json.dumps(decide(args.message, model), ensure_ascii=False, indent=2))
        return 0
    if args.cmd in {"batch", "stress"}:
        summary = evaluate(args.input, args.model, repeat=getattr(args, "repeat", 1))
        _write_json(args.json_out, summary)
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(markdown(summary, "تقرير ضغط المندوب" if args.cmd == "stress" else "تقرير المندوب"), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["collapse_check"]["passed"] else 2
    raise ValueError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())

