import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.data_loader import DataLoadError, dataframe_schema, load_csv


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    p = tmp_path / "sample.csv"
    p.write_text("region,revenue\nUS,100\nEU,200\n", encoding="utf-8")
    return p


def test_load_csv_success(sample_csv: Path):
    df = load_csv(sample_csv)
    assert list(df.columns) == ["region", "revenue"]
    assert len(df) == 2


def test_load_csv_missing_file(tmp_path: Path):
    with pytest.raises(DataLoadError, match="not found"):
        load_csv(tmp_path / "does_not_exist.csv")


def test_load_csv_empty_file(tmp_path: Path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(DataLoadError):
        load_csv(p)


def test_load_csv_row_limit_enforced(sample_csv: Path):
    with pytest.raises(DataLoadError, match="MAX_ROWS"):
        load_csv(sample_csv, max_rows=1)


def test_dataframe_schema_shape():
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})
    schema = dataframe_schema(df)
    assert schema["n_rows"] == 3
    assert schema["n_columns"] == 2
    col_a = next(c for c in schema["columns"] if c["name"] == "a")
    assert col_a["n_missing"] == 1
