"""Execute the documented DuckDB analysis against the validated panel."""

from pathlib import Path

import duckdb
import pandas as pd


def run_sql_analysis(sql_path: Path, project_root: Path) -> pd.DataFrame:
    """Run the SQL script and return its final result set."""
    connection = duckdb.connect(database=":memory:")
    try:
        connection.execute(f"SET home_directory='{project_root.as_posix()}';")
        return connection.execute(sql_path.read_text(encoding="utf-8")).fetchdf()
    finally:
        connection.close()

