import json
import sys
from pathlib import Path

import duckdb


def profile_dataset(file_path: str) -> dict:
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
        raise ValueError(f"Unsupported format for profiling: {extension}")

    columns = [
        {
            "name": name,
            "type": str(data_type),
        }
        for name, data_type in zip(relation.columns, relation.types)
    ]

    row_count = relation.aggregate("count(*)").fetchone()[0]

    return {
        "file": path.name,
        "rows": row_count,
        "column_count": len(columns),
        "columns": columns,
    }


if __name__ == "__main__":
    try:
        result = profile_dataset(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)