"""
Tool implementations exposed to the LLM via tool-calling (function calling).

Design decision: no free-form Python/SQL execution is exposed to the
model. Every tool is a narrow, structured operation (filter, group,
aggregate, sort, plot). This is a deliberate security boundary — it
prevents prompt-injection or a misbehaving model from executing
arbitrary code, reading the filesystem, or exfiltrating data, while
still covering the vast majority of real exploratory data analysis.

Each tool function:
  * takes a DataFrame + structured, JSON-schema-validated arguments
  * returns a small, JSON-serializable result (never the full raw data)
  * raises ToolError with a clear message on invalid input, which is
    fed back to the model so it can self-correct
"""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")  # headless rendering, no GUI backend required
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)

_SAFE_QUERY_PATTERN = re.compile(
    r"^[^;`]*$"
)  # reject semicolons / backticks outright as a first defense layer
_BANNED_TOKENS = ("__", "import", "os.", "sys.", "eval(", "exec(", "open(", "subprocess", "globals", "locals")


class ToolError(Exception):
    """Raised when a tool cannot complete due to invalid input or state."""


def _validate_filter_expression(expr: str) -> None:
    if not _SAFE_QUERY_PATTERN.match(expr):
        raise ToolError("Filter expression contains disallowed characters (';' or '`').")
    lowered = expr.lower()
    for token in _BANNED_TOKENS:
        if token in lowered:
            raise ToolError(f"Filter expression contains a disallowed token: {token!r}")
    if len(expr) > 300:
        raise ToolError("Filter expression is too long (max 300 characters).")


def get_schema(df: pd.DataFrame) -> dict:
    """Return column names, dtypes, null counts, and basic cardinality."""
    return {
        "n_rows": len(df),
        "n_columns": int(df.shape[1]),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "n_missing": int(df[col].isna().sum()),
                "n_unique": int(df[col].nunique(dropna=True)),
                "sample_values": [str(v) for v in df[col].dropna().unique()[:5].tolist()],
            }
            for col in df.columns
        ],
    }


def describe_data(df: pd.DataFrame, columns: list[str] | None = None) -> dict:
    """Return summary statistics (count, mean, std, min, quartiles, max) for numeric columns."""
    subset = df[columns] if columns else df
    numeric = subset.select_dtypes(include="number")
    if numeric.empty:
        return {"message": "No numeric columns found in the requested subset.", "columns_checked": list(subset.columns)}
    desc = numeric.describe().to_dict()
    return {col: {stat: round(float(val), 4) for stat, val in stats.items()} for col, stats in desc.items()}


def filter_data(df: pd.DataFrame, expression: str) -> dict:
    """Filter rows using a pandas boolean query expression, e.g. "revenue > 1000 and region == 'US'".

    Returns row count and a small preview (first 10 rows), never the
    full filtered dataset, to keep tool results compact and avoid
    dumping potentially sensitive bulk data back into the model context.
    """
    _validate_filter_expression(expression)
    try:
        filtered = df.query(expression, engine="python")
    except Exception as exc:
        raise ToolError(f"Invalid filter expression: {exc}") from exc

    preview = filtered.head(10)
    return {
        "matched_rows": len(filtered),
        "total_rows": len(df),
        "preview": preview.to_dict(orient="records"),
    }


def aggregate_data(
    df: pd.DataFrame,
    group_by: list[str],
    metric_column: str,
    agg_func: Literal["sum", "mean", "median", "count", "min", "max", "std"],
    top_n: int | None = None,
) -> dict:
    """Group by one or more columns and aggregate a numeric metric column."""
    for col in group_by:
        if col not in df.columns:
            raise ToolError(f"group_by column not found: {col!r}")
    if metric_column not in df.columns and agg_func != "count":
        raise ToolError(f"metric_column not found: {metric_column!r}")

    try:
        if agg_func == "count":
            result = df.groupby(group_by).size().reset_index(name="count")
            result = result.sort_values("count", ascending=False)
        else:
            result = (
                df.groupby(group_by)[metric_column]
                .agg(agg_func)
                .reset_index()
                .sort_values(metric_column, ascending=False)
            )
    except Exception as exc:
        raise ToolError(f"Aggregation failed: {exc}") from exc

    if top_n:
        result = result.head(top_n)

    return {"rows": result.to_dict(orient="records"), "n_groups": len(result)}


def create_chart(
    df: pd.DataFrame,
    chart_type: Literal["bar", "line", "scatter", "hist", "pie"],
    x: str | None,
    y: str | None,
    title: str,
    output_dir: Path,
    group_by: list[str] | None = None,
    agg_func: str = "sum",
) -> dict:
    """Render a chart to a PNG file and return its path.

    If group_by is provided, the data is aggregated first (mirrors
    aggregate_data) so the model doesn't need a separate round trip
    for the common "chart of grouped metric" case.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_df = df

    if group_by:
        if y is None:
            raise ToolError("y (metric column) is required when group_by is set.")
        plot_df = df.groupby(group_by)[y].agg(agg_func).reset_index()
        x = group_by[0] if x is None else x

    fig, ax = plt.subplots(figsize=(8, 5))
    try:
        if chart_type == "bar":
            if x is None or y is None:
                raise ToolError("bar chart requires both x and y.")
            plot_df.plot(kind="bar", x=x, y=y, ax=ax, legend=False)
        elif chart_type == "line":
            if x is None or y is None:
                raise ToolError("line chart requires both x and y.")
            plot_df.sort_values(x).plot(kind="line", x=x, y=y, ax=ax, legend=False, marker="o")
        elif chart_type == "scatter":
            if x is None or y is None:
                raise ToolError("scatter chart requires both x and y.")
            plot_df.plot(kind="scatter", x=x, y=y, ax=ax)
        elif chart_type == "hist":
            if y is None:
                raise ToolError("hist chart requires y (the numeric column).")
            plot_df[y].plot(kind="hist", ax=ax, bins=30)
        elif chart_type == "pie":
            if x is None or y is None:
                raise ToolError("pie chart requires both x (labels) and y (values).")
            plot_df.set_index(x)[y].plot(kind="pie", ax=ax, autopct="%1.1f%%")
    except ToolError:
        plt.close(fig)
        raise
    except Exception as exc:
        plt.close(fig)
        raise ToolError(f"Chart rendering failed: {exc}") from exc

    ax.set_title(title)
    fig.tight_layout()

    filename = f"chart_{uuid.uuid4().hex[:8]}.png"
    filepath = output_dir / filename
    fig.savefig(filepath, dpi=150)
    plt.close(fig)

    logger.info("Chart saved: %s", filepath)
    return {"chart_path": str(filepath), "chart_type": chart_type, "title": title}


TOOL_REGISTRY: dict[str, Any] = {
    "get_schema": get_schema,
    "describe_data": describe_data,
    "filter_data": filter_data,
    "aggregate_data": aggregate_data,
    "create_chart": create_chart,
}
