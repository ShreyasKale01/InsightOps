"""Compile an AgentResult into a shareable markdown report."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from .core import AgentResult


def build_markdown_report(question: str, result: AgentResult, dataset_name: str) -> str:
    lines = [
        "# Data Analysis Report",
        "",
        f"- **Dataset:** {dataset_name}",
        f"- **Question:** {question}",
        f"- **Generated:** {_dt.datetime.now(_dt.timezone.utc).isoformat(timespec='seconds')}",
        f"- **Analysis steps used:** {result.turns_used}",
        "",
        "## Findings",
        "",
        result.answer,
        "",
    ]

    if result.chart_paths:
        lines.append("## Charts")
        lines.append("")
        for path in result.chart_paths:
            lines.append(f"![chart]({path})")
        lines.append("")

    if result.tool_calls:
        lines.append("## Analysis Trace (tool calls)")
        lines.append("")
        for i, call in enumerate(result.tool_calls, start=1):
            lines.append(f"{i}. `{call['tool']}({call['input']})`")
        lines.append("")

    return "\n".join(lines)


def save_report(question: str, result: AgentResult, dataset_name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_md = build_markdown_report(question, result, dataset_name)
    filename = f"report_{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    filepath = output_dir / filename
    filepath.write_text(report_md, encoding="utf-8")
    return filepath
