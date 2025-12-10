"""
Entry point.

Usage:
    python main.py --file data/sample_sales.csv --question "Which region had the highest total revenue?" --report
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agent.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
