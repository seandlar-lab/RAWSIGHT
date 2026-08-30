from pathlib import Path

import duckdb

from rawsight.datasets import open_dataset


def inspect_structure(file_path: str) -> dict:
    path = Path(file_path)

    connection = duckdb.connect(database=":memory:")

    try:
        relation = open_dataset(connection, file_path)

        columns = [
            {
                "name": column_name,
                "technical_type": str(column_type),
            }
            for column_name, column_type in zip(
                relation.columns,
                relation.types,
            )
        ]

        return {
            "file_name": path.name,
            "extension": path.suffix.lower().lstrip("."),
            "column_count": len(columns),
            "columns": columns,
        }

    finally:
        connection.close()