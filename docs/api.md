# Tool API Reference

This project doesn't expose an HTTP API (it's a CLI/library). The "API" that matters here is the tool contract between the Claude agent and the pandas layer — this is what an interviewer or code reviewer should read to understand exactly what the model can and cannot do.

## get_schema

- **Purpose**: Return column names, dtypes, null counts, cardinality, sample values.
- **Input**: none.
- **Output**:
```json
{
  "n_rows": 400,
  "n_columns": 7,
  "columns": [
    {"name": "region", "dtype": "object", "n_missing": 0, "n_unique": 4, "sample_values": ["North America", "Europe"]}
  ]
}
```

## describe_data

- **Purpose**: Summary statistics for numeric columns.
- **Input**: `{"columns": ["revenue"]}` (optional; omit for all numeric columns).
- **Output**: per-column `count/mean/std/min/25%/50%/75%/max`.

## filter_data

- **Purpose**: Row-level filtering.
- **Input**: `{"expression": "revenue > 1000 and region == 'US'"}`
- **Output**: `{"matched_rows": N, "total_rows": M, "preview": [...up to 10 rows...]}`
- **Errors**: `ToolError` if the expression contains `;`, `` ` ``, or a banned token (`import`, `os.`, `eval(`, `exec(`, `__`, `subprocess`, `globals`, `locals`), references an unknown column, or exceeds 300 characters.

## aggregate_data

- **Purpose**: Group-by + aggregate.
- **Input**: `{"group_by": ["region"], "metric_column": "revenue", "agg_func": "sum", "top_n": 5}`
- **agg_func**: one of `sum, mean, median, count, min, max, std`.
- **Output**: `{"rows": [{"region": "US", "revenue": 12500.0}, ...], "n_groups": N}`, sorted descending by the aggregated value.

## create_chart

- **Purpose**: Render a PNG chart, optionally aggregating first.
- **Input**: `{"chart_type": "bar", "x": "region", "y": "revenue", "title": "Revenue by Region", "group_by": ["region"], "agg_func": "sum"}`
- **chart_type**: one of `bar, line, scatter, hist, pie`.
- **Output**: `{"chart_path": "outputs/chart_ab12cd34.png", "chart_type": "bar", "title": "Revenue by Region"}`

## Error format

Every tool returns `{"error": "<message>"}` on failure instead of raising an uncaught exception up to the model. This lets Claude read the error and self-correct (e.g., fix a column name) within the same bounded loop instead of the whole request failing.
