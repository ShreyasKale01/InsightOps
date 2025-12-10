import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.tools import (
    ToolError,
    aggregate_data,
    create_chart,
    describe_data,
    filter_data,
    get_schema,
)


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["US", "US", "EU", "EU", "APAC"],
            "product": ["A", "B", "A", "B", "A"],
            "revenue": [100.0, 150.0, 200.0, 50.0, 300.0],
        }
    )


def test_get_schema(df):
    schema = get_schema(df)
    assert schema["n_rows"] == 5
    assert schema["n_columns"] == 3
    names = [c["name"] for c in schema["columns"]]
    assert set(names) == {"region", "product", "revenue"}


def test_describe_data(df):
    result = describe_data(df)
    assert "revenue" in result
    assert result["revenue"]["count"] == 5


def test_filter_data_valid_expression(df):
    result = filter_data(df, "revenue > 100")
    assert result["matched_rows"] == 3
    assert result["total_rows"] == 5


def test_filter_data_rejects_dangerous_input(df):
    with pytest.raises(ToolError):
        filter_data(df, "os.system('rm -rf /')")


def test_filter_data_rejects_semicolon(df):
    with pytest.raises(ToolError):
        filter_data(df, "revenue > 100; print('hi')")


def test_filter_data_invalid_column(df):
    with pytest.raises(ToolError):
        filter_data(df, "nonexistent_column > 5")


def test_aggregate_data_sum(df):
    result = aggregate_data(df, group_by=["region"], metric_column="revenue", agg_func="sum")
    assert result["n_groups"] == 3
    us_row = next(r for r in result["rows"] if r["region"] == "US")
    assert us_row["revenue"] == 250.0


def test_aggregate_data_count(df):
    result = aggregate_data(df, group_by=["region"], metric_column="revenue", agg_func="count")
    assert result["n_groups"] == 3


def test_aggregate_data_unknown_group_column(df):
    with pytest.raises(ToolError):
        aggregate_data(df, group_by=["nope"], metric_column="revenue", agg_func="sum")


def test_aggregate_data_top_n(df):
    result = aggregate_data(df, group_by=["region"], metric_column="revenue", agg_func="sum", top_n=1)
    assert result["n_groups"] == 1


def test_create_chart_bar(df, tmp_path):
    result = create_chart(
        df,
        chart_type="bar",
        x="region",
        y="revenue",
        title="Revenue by region",
        output_dir=tmp_path,
        group_by=["region"],
        agg_func="sum",
    )
    assert Path(result["chart_path"]).exists()
    assert result["chart_path"].endswith(".png")


def test_create_chart_missing_required_args(df, tmp_path):
    with pytest.raises(ToolError):
        create_chart(df, chart_type="bar", x=None, y=None, title="Bad chart", output_dir=tmp_path)
