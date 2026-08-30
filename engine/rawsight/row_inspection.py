import json
import sys
from pathlib import Path

import duckdb


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def inspect_rows(
    file_path: str,
    column_name: str,
    value: str,
    limit: int = 100,
) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    connection = duckdb.connect()

    if extension == ".csv":
        relation = connection.read_csv(str(path))
    elif extension == ".parquet":
        relation = connection.read_parquet(str(path))
    else:
        raise ValueError(
            f"Unsupported format for inspection: {extension}"
        )

    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    relation.create_view(
        "rawsight_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    # Vi jämför här via textrepresentation för att kunna använda
    # samma funktion för både numeriska och textbaserade värden.
    where_clause = f"CAST({column} AS VARCHAR) = ?"

    total_rows = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM rawsight_source
        WHERE {where_clause}
        """,
        [value],
    ).fetchone()[0]

    cursor = connection.execute(
        f"""
        SELECT *
        FROM rawsight_source
        WHERE {where_clause}
        LIMIT ?
        """,
        [value, limit],
    )

    column_names = [
        description[0]
        for description in cursor.description
    ]

    result_rows = cursor.fetchall()

    rows = [
        [json_safe(value) for value in row]
        for row in result_rows
    ]

    return {
        "filter": {
            "column": column_name,
            "value": value,
        },
        "total_rows": total_rows,
        "returned_rows": len(rows),
        "columns": column_names,
        "rows": rows,
    }
