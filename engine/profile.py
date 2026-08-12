import json
import sys
from pathlib import Path

import duckdb


def progress(message: str) -> None:
    print(f"PROGRESS\t{message}", flush=True)


def profile_dataset(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    progress("Opening dataset")

    connection = duckdb.connect()

    if extension == ".csv":
        relation = connection.read_csv(str(path))
    elif extension == ".parquet":
        relation = connection.read_parquet(str(path))
    else:
        raise ValueError(f"Unsupported format for profiling: {extension}")

    progress("Detecting structure")

    columns = [
        {
            "name": name,
            "type": str(data_type),
        }
        for name, data_type in zip(relation.columns, relation.types)
    ]

    progress("Counting rows")

    row_count = relation.aggregate("count(*)").fetchone()[0]

    progress("Preparing overview")

    return {
        "file": path.name,
        "rows": row_count,
        "column_count": len(columns),
        "columns": columns,
    }


if __name__ == "__main__":
    try:
        result = profile_dataset(sys.argv[1])

        print(
            "RESULT\t" + json.dumps(result, ensure_ascii=False),
            flush=True,
        )

    except Exception as error:
        print(
            f"ERROR\t{error}",
            flush=True,
        )
        sys.exit(1)