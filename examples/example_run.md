# Example Run

This shows what a typical session looks like (illustrative — exact numbers depend on the live model response, since `data/sample_sales.csv` is randomly generated).

```bash
$ python main.py --file data/sample_sales.csv \
    --question "Which region generated the most total revenue, and how does it break down by product?" \
    --report

======================================================================
ANALYSIS
======================================================================
North America generated the highest total revenue at $48,213.50 across
the dataset.

- Top product in North America: Aurora Desk ($15,204.00)
- Second: Zenith Lamp ($11,890.50)
- Europe was the second-highest region overall at $41,662.75.

Charts generated:
  - outputs/chart_9f3a1b2c.png

Full report saved to: outputs/report_20260807_143022.md
```

The generated `report_*.md` includes the same analysis, an embedded chart image reference, and a numbered trace of every tool call the agent made (e.g., `aggregate_data(group_by=['region'], metric_column='revenue', agg_func='sum')`) so the answer is fully auditable.
