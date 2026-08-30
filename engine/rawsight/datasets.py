from pathlib import Path

import duckdb


def open_dataset(
    connection: duckdb.DuckDBPyConnection,
    file_path: str,
) -> duckdb.DuckDBPyRelation:
    """
    Open a dataset as a DuckDB relation.

    Dataset access belongs here so analysis modules do not need
    their own CSV/Parquet opening logic.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        return connection.read_csv(str(path))

    if extension == ".parquet":
        return connection.read_parquet(str(path))

    raise ValueError(
        f"Unsupported dataset format: {extension or 'unknown'}"
    )