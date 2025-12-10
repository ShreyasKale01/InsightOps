"""Command-line interface for the AI Data Analyst Agent."""
from __future__ import annotations

import argparse
import logging
import sys

from .config import configure_logging, get_settings
from .core import DataAnalystAgent
from .data_loader import DataLoadError, load_csv, load_sql
from .report import save_report

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyst-agent",
        description="Ask natural-language questions about a CSV or database table and get an AI-generated analysis with charts.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="Path to a CSV file.")
    source.add_argument("--sql", help="A read-only SELECT query (requires DATABASE_URL in the environment).")

    parser.add_argument("--question", required=True, help="Natural-language question to ask about the data.")
    parser.add_argument("--report", action="store_true", help="Also write a markdown report to OUTPUT_DIR.")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    settings = get_settings()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.file:
            df = load_csv(args.file, max_rows=settings.max_rows)
            dataset_name = args.file
        else:
            if not settings.database_url:
                print("DATABASE_URL is not set. Add it to your .env file.", file=sys.stderr)
                return 2
            df = load_sql(args.sql, settings.database_url, max_rows=settings.max_rows)
            dataset_name = "SQL query result"
    except DataLoadError as exc:
        print(f"Failed to load data: {exc}", file=sys.stderr)
        return 1

    try:
        agent = DataAnalystAgent(df, settings=settings)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    result = agent.analyze(args.question)

    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print(result.answer)

    if result.chart_paths:
        print("\nCharts generated:")
        for path in result.chart_paths:
            print(f"  - {path}")

    if args.report:
        report_path = save_report(args.question, result, dataset_name, settings.output_dir)
        print(f"\nFull report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
