from __future__ import annotations


def markdown(summary: dict, title: str = "تقرير المندوب") -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"- المدخل: `{summary.get('input')}`",
            f"- المعالجة: `{summary.get('processed', 0)}`",
            f"- الدقة: `{summary.get('accuracy', 0):.2%}`",
            f"- التصعيدات: `{summary.get('escalations', 0)}`",
            f"- الأخطاء: `{summary.get('errors', 0)}`",
            f"- p99: `{summary.get('latency_ms', {}).get('p99', 0):.3f}ms`",
            f"- peak memory: `{summary.get('memory_mb', {}).get('peak', 0):.2f}MB`",
            "",
        ]
    )

