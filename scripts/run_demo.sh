#!/usr/bin/env bash
# Quick smoke-test demo run against the bundled sample dataset.
# Requires ANTHROPIC_API_KEY to be set in .env.
set -euo pipefail

cd "$(dirname "$0")/.."

python main.py \
  --file data/sample_sales.csv \
  --question "Which region generated the most total revenue in 2025, and how does it break down by product?" \
  --report

echo ""
echo "Demo complete. Check the outputs/ directory for the generated report and chart."
