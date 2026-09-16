import json
import sys
from pathlib import Path

import duckdb
from rawsight.datasets import (
    inspect_source,
    open_dataset,
    select_analysis_strategy,
)

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

def detect_yyyymmdd_date(
    connection,
    column_name: str,
    data_type: str,
    row_count: int,
):
    integer_types = {
        "TINYINT",
        "SMALLINT",
        "INTEGER",
        "BIGINT",
        "HUGEINT",
        "UTINYINT",
        "USMALLINT",
        "UINTEGER",
        "UBIGINT",
    }

    if data_type.upper() not in integer_types:
        return None

    column = quote_identifier(column_name)

    result = connection.execute(
        f"""
        SELECT
            COUNT(*) FILTER (
                WHERE {column} = 0
            ) AS zero_count,

            COUNT(*) FILTER (
                WHERE {column} IS NOT NULL
                  AND {column} <> 0
            ) AS candidate_count,

            COUNT(*) FILTER (
                WHERE {column} IS NOT NULL
                  AND {column} <> 0
                  AND try_strptime(
                      CAST({column} AS VARCHAR),
                      '%Y%m%d'
                  ) IS NOT NULL
            ) AS valid_date_count

        FROM rawsight_source
        """
    ).fetchone()

    zero_count = result[0]
    candidate_count = result[1]
    valid_date_count = result[2]

    if candidate_count == 0:
        return None

    confidence = valid_date_count / candidate_count * 100

    # Vi kräver starkt stöd i själva värdena.
    if confidence < 95:
        return None

    return {
        "suggested_type": "DATE",
        "format": "YYYYMMDD",
        "confidence": round(confidence, 2),
        "valid_count": valid_date_count,
        "candidate_count": candidate_count,
        "zero_count": zero_count,
    }

def build_analysis_status(
    status: str,
    reason: str | None = None,
) -> dict:
    return {
        "status": status,
        "reason": reason,
    }

def profile_conservative_dataset(
    file_path: str,
    inspection: dict,
    analysis_strategy: dict,
) -> dict:
    """
    Produce a safe structural profile without running
    whole-row DISTINCT or mass column aggregates.
    """

    path = Path(file_path)

    progress("Opening dataset safely")

    connection = duckdb.connect()

    try:
        relation = open_dataset(
            connection,
            file_path,
        )

        column_names = relation.columns
        column_types = [
            str(data_type)
            for data_type in relation.types
        ]

        relation.create_view(
            "rawsight_source",
            replace=True,
        )

        progress("Counting rows")

        row_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM rawsight_source
            """
        ).fetchone()[0]

        columns = [
            {
                "name": name,
                "type": data_type,
                "null_count": None,
                "null_percent": None,
                "distinct_count": None,
                "unique_percent": None,
                "min": None,
                "max": None,
                "semantic_hint": None,
            }
            for name, data_type in zip(
                column_names,
                column_types,
            )
        ]

        return {
            "file": path.name,
            "rows": row_count,
            "column_count": len(columns),

            "duplicate_rows": None,
            "duplicate_percent": None,
            "missing_values": None,
            "missing_percent": None,

            "columns": columns,

            "analysis_strategy": analysis_strategy,
            "structural_model": inspection.get(
                "structural_model"
            ),
        }

    finally:
        connection.close()

def profile_dataset(file_path: str) -> dict:
    """
    Route dataset analysis according to detected structural
    characteristics.

    Unsafe generic profiling is bypassed when structural
    evidence indicates that a specialized or conservative
    strategy is required.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    progress("Inspecting source structure")

    inspection = inspect_source(
        file_path
    )

    structural_model = inspection.get(
        "structural_model",
        {},
    )

    analysis_strategy = select_analysis_strategy(
        structural_model
    )

    strategy = analysis_strategy[
        "strategy"
    ]

    progress(
        f"Analysis strategy: {strategy}"
    )

    if strategy == "wide_temporal":
        return profile_wide_temporal_safe(
            file_path=file_path,
            inspection=inspection,
            analysis_strategy=analysis_strategy,
        )

    if strategy == "long_temporal":
        return profile_conservative_dataset(
            file_path=file_path,
            inspection=inspection,
            analysis_strategy=analysis_strategy,
        )

    if strategy == "conservative_tabular":
        return profile_conservative_dataset(
            file_path=file_path,
            inspection=inspection,
            analysis_strategy=analysis_strategy,
        )

    return profile_conservative_dataset(
        file_path=file_path,
        inspection=inspection,
        analysis_strategy=analysis_strategy,
    )

def profile_wide_temporal_safe(
    file_path: str,
    inspection: dict,
    analysis_strategy: dict,
) -> dict:
    """
    Produce a safe profile for a wide temporal dataset.

    Temporal facts are derived from structural evidence already
    detected during source inspection. Expensive generic
    profiling remains bypassed.
    """

    profile = profile_conservative_dataset(
        file_path=file_path,
        inspection=inspection,
        analysis_strategy=analysis_strategy,
    )

    structural_model = inspection.get(
        "structural_model",
        {},
    )

    logical_structure = structural_model.get(
        "logical_structure",
        {},
    )

    temporal_axis = logical_structure.get(
        "temporal_axis"
    )

    if temporal_axis is None:
        return profile

    start_index = temporal_axis.get(
        "start_index"
    )

    end_index = temporal_axis.get(
        "end_index"
    )

    temporal_column_count = None

    if (
        isinstance(start_index, int)
        and isinstance(end_index, int)
        and end_index >= start_index
    ):
        temporal_column_count = (
            end_index - start_index + 1
        )

    non_temporal_column_count = None

    if temporal_column_count is not None:
        non_temporal_column_count = (
            profile["column_count"]
            - temporal_column_count
        )

    profile["wide_temporal"] = {
        "status": "candidate",
        "axis_orientation": temporal_axis.get(
            "orientation"
        ),
        "temporal_column_start_index": start_index,
        "temporal_column_end_index": end_index,
        "temporal_column_count": temporal_column_count,
        "non_temporal_column_count": (
            non_temporal_column_count
        ),
        "format": temporal_axis.get(
            "format"
        ),
        "range_start": temporal_axis.get(
            "range_start"
        ),
        "range_end": temporal_axis.get(
            "range_end"
        ),
        "order": temporal_axis.get(
            "order"
        ),
        "distinct_timestamp_count": (
            temporal_axis.get(
                "distinct_count"
            )
        ),
        "dominant_interval_seconds": (
            temporal_axis.get(
                "dominant_interval_seconds"
            )
        ),
        "cadence_consistency": (
            temporal_axis.get(
                "cadence_consistency"
            )
        ),
    }

    return profile

def profile_dataset_legacy(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    progress("Opening dataset")

    connection = duckdb.connect()

    relation = open_dataset(connection, file_path)

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
    progress("Detecting semantic patterns")

    for column in columns:
        column["semantic_hint"] = detect_yyyymmdd_date(
            connection,
            column["name"],
            column["type"],
            row_count,
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
