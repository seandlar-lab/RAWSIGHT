import json
import sys
from pathlib import Path

import duckdb


def inspect_structure(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    extension = path.suffix.lower()

    connection = duckdb.connect(database=":memory:")

    try:
        if extension == ".csv":
            relation = connection.read_csv(str(path))
        elif extension == ".parquet":
            relation = connection.read_parquet(str(path))
        else:
            raise ValueError(
                f"Unsupported dataset format for structure inspection: {extension}"
            )

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
            "extension": extension.lstrip("."),
            "column_count": len(columns),
            "columns": columns,
        }

    finally:
        connection.close()


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "ERROR\tUsage: inspect_structure.py <dataset_path>",
            flush=True,
        )
        sys.exit(1)

    try:
        result = inspect_structure(sys.argv[1])

        print(
            "RESULT\t" + json.dumps(result, ensure_ascii=False),
            flush=True,
        )

    except Exception as exc:
        print(
            f"ERROR\t{exc}",
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()