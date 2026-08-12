import json
import sys
from pathlib import Path

import duckdb


NUMERIC_TYPES = (
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "FLOAT",
    "DOUBLE",
    "DECIMAL",
)

TEMPORAL_TYPES = (
    "DATE",
    "TIME",
    "TIMESTAMP",
)


def progress(message: str) -> None:
    print(f"PROGRESS\t{message}", flush=True)


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


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
        raise ValueError(
            f"Unsupported format for profiling: {extension}"
        )

    progress("Detecting structure")

    column_names = relation.columns
    column_types = [str(data_type) for data_type in relation.types]

    relation.create_view(
        "rawsight_source",
        replace=True,
    )

    progress("Counting rows")

    row_count = connection.execute(
        "SELECT COUNT(*) FROM rawsight_source"
    ).fetchone()[0]

    progress("Checking exact duplicates")

    distinct_row_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT *
            FROM rawsight_source
        )
        """
    ).fetchone()[0]

    duplicate_rows = row_count - distinct_row_count

    duplicate_percent = (
        duplicate_rows / row_count * 100
        if row_count > 0
        else 0.0
    )

    progress("Profiling columns")

    expressions = []

    for index, (name, data_type) in enumerate(
        zip(column_names, column_types)
    ):
        column = quote_identifier(name)

        expressions.append(
            f"""
            COUNT(*) FILTER (
                WHERE {column} IS NULL
            ) AS c{index}_nulls
            """
        )

        expressions.append(
            f"""
            COUNT(DISTINCT {column})
            AS c{index}_distinct
            """
        )

        type_upper = data_type.upper()

        if (
            type_upper.startswith(NUMERIC_TYPES)
            or type_upper.startswith(TEMPORAL_TYPES)
        ):
            expressions.append(
                f"MIN({column}) AS c{index}_min"
            )
            expressions.append(
                f"MAX({column}) AS c{index}_max"
            )
        else:
            expressions.append(
                f"NULL AS c{index}_min"
            )
            expressions.append(
                f"NULL AS c{index}_max"
            )

    aggregate_sql = (
        "SELECT "
        + ", ".join(expressions)
        + " FROM rawsight_source"
    )

    aggregate_row = connection.execute(
        aggregate_sql
    ).fetchone()

    columns = []
    total_missing = 0

    position = 0

    for name, data_type in zip(
        column_names,
        column_types,
    ):
        null_count = aggregate_row[position]
        distinct_count = aggregate_row[position + 1]
        minimum = aggregate_row[position + 2]
        maximum = aggregate_row[position + 3]

        position += 4

        total_missing += null_count

        non_null_count = row_count - null_count

        null_percent = (
            null_count / row_count * 100
            if row_count > 0
            else 0.0
        )

        unique_percent = (
            distinct_count / non_null_count * 100
            if non_null_count > 0
            else 0.0
        )

        columns.append(
            {
                "name": name,
                "type": data_type,
                "null_count": null_count,
                "null_percent": round(null_percent, 4),
                "distinct_count": distinct_count,
                "unique_percent": round(unique_percent, 4),
                "min": json_safe(minimum),
                "max": json_safe(maximum),
            }
        )

    total_cells = row_count * len(columns)

    missing_percent = (
        total_missing / total_cells * 100
        if total_cells > 0
        else 0.0
    )

    progress("Preparing overview")

    return {
        "file": path.name,
        "rows": row_count,
        "column_count": len(columns),
        "duplicate_rows": duplicate_rows,
        "duplicate_percent": round(
            duplicate_percent,
            4,
        ),
        "missing_values": total_missing,
        "missing_percent": round(
            missing_percent,
            4,
        ),
        "columns": columns,
    }


if __name__ == "__main__":
    try:
        result = profile_dataset(sys.argv[1])

        print(
            "RESULT\t"
            + json.dumps(
                result,
                ensure_ascii=False,
            ),
            flush=True,
        )

    except Exception as error:
        print(
            f"ERROR\t{error}",
            flush=True,
        )
        sys.exit(1)