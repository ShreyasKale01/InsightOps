"""
Data loading layer.

Responsible for getting tabular data (CSV file or SQL database) into a
pandas DataFrame safely, with size guards and clear error messages.
This module has zero AI/LLM dependency so it can be fully unit tested
in isolation.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Raised when a dataset cannot be loaded or fails validation."""


def load_csv(path: str | Path, max_rows: int = 200_000) -> pd.DataFrame:
    """Load a CSV file into a DataFrame with basic validation.

    Args:
        path: Path to the CSV file.
        max_rows: Safety guard - refuse to load absurdly large files
            into memory unbounded. Raise instead of silently truncating,
            so the caller can decide how to proceed (chunking, sampling).

    Raises:
        DataLoadError: if the file is missing, empty, unparsable, or
            exceeds max_rows.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise DataLoadError(f"CSV file not found: {file_path}")
    if file_path.suffix.lower() != ".csv":
        logger.warning("File %s does not have a .csv extension; attempting to parse anyway.", file_path)

    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError as exc:
        raise DataLoadError(f"CSV file is empty: {file_path}") from exc
    except pd.errors.ParserError as exc:
        raise DataLoadError(f"Could not parse CSV file {file_path}: {exc}") from exc

    if df.empty:
        raise DataLoadError(f"CSV file loaded but contains zero rows: {file_path}")

    if len(df) > max_rows:
        raise DataLoadError(
            f"Dataset has {len(df)} rows, exceeding the configured MAX_ROWS={max_rows}. "
            "Increase MAX_ROWS if this is expected, or pre-aggregate the data."
        )

    logger.info("Loaded CSV %s -> shape=%s", file_path, df.shape)
    return df


def load_sql(query: str, database_url: str, max_rows: int = 200_000) -> pd.DataFrame:
    """Load the result of a SQL query into a DataFrame.

    Args:
        query: A read-only SELECT query. Callers are responsible for
            ensuring this is not built from untrusted user input without
            parameterization (this function does not sanitize SQL).
        database_url: SQLAlchemy-compatible connection string.
        max_rows: Same safety guard as load_csv.

    Raises:
        DataLoadError: on connection failure, query failure, or if the
            result exceeds max_rows.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    stripped = query.strip().lower()
    if not stripped.startswith("select") and not stripped.startswith("with"):
        raise DataLoadError(
            "Only read-only SELECT/WITH queries are permitted through this loader."
        )

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
    except SQLAlchemyError as exc:
        raise DataLoadError(f"Database query failed: {exc}") from exc

    if len(df) > max_rows:
        raise DataLoadError(
            f"Query returned {len(df)} rows, exceeding MAX_ROWS={max_rows}. "
            "Add a LIMIT clause or aggregate in SQL first."
        )

    logger.info("Loaded SQL query -> shape=%s", df.shape)
    return df


def dataframe_schema(df: pd.DataFrame) -> dict:
    """Return a JSON-serializable schema summary of a DataFrame."""
    return {
        "n_rows": len(df),
        "n_columns": int(df.shape[1]),
        "columns": [
            {
                "name": col,
                "dtype": str(df[col].dtype),
                "n_missing": int(df[col].isna().sum()),
                "n_unique": int(df[col].nunique(dropna=True)),
            }
            for col in df.columns
        ],
    }
