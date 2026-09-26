import json
import sys
from pathlib import Path

import duckdb
from rawsight.datasets import (
    inspect_source,
    open_dataset,
    select_analysis_strategy,
)
from rawsight.source_context import (
    SourceExecutionContext,
)
from rawsight.wide_temporal_execution import (
    execute_wide_temporal_analysis,
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

def is_numeric_type(
    data_type: str,
) -> bool:
    type_upper = data_type.upper()

    return any(
        type_upper.startswith(prefix)
        for prefix in NUMERIC_TYPES
    )


def is_temporal_type(
    data_type: str,
) -> bool:
    type_upper = data_type.upper()

    return any(
        type_upper.startswith(prefix)
        for prefix in TEMPORAL_TYPES
    )

def profile_conservative_dataset(
    file_path: str,
    inspection: dict,
    analysis_strategy: dict,
    source_context: (
        SourceExecutionContext | None
    ) = None,
    count_rows: bool = True,
) -> dict:
    """
    Produce a safe structural profile without running
    whole-row DISTINCT or mass column aggregates.

    A supplied SourceExecutionContext is reused and remains owned by
    the caller. Without one, this function owns one source session.
    """

    path = Path(file_path)

    if source_context is None:
        progress(
            "Opening dataset safely"
        )

        with SourceExecutionContext(
            file_path
        ) as owned_context:
            return profile_conservative_dataset(
                file_path=file_path,
                inspection=inspection,
                analysis_strategy=analysis_strategy,
                source_context=owned_context,
                count_rows=count_rows,
            )

    source_context.assert_source(
        file_path
    )

    if not source_context.is_open:
        raise RuntimeError(
            "Supplied SourceExecutionContext "
            "must already be open"
        )

    connection = (
        source_context.require_connection()
    )
    column_names = (
        source_context.column_names
    )
    column_types = (
        source_context.column_types
    )

    row_count = None

    if count_rows:
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

def profile_long_temporal_safe(
    file_path: str,
    inspection: dict,
    analysis_strategy: dict,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict:
    """
    Produce a bounded profile for a long temporal dataset.

    The source is scanned through aggregate expressions only.
    No full-row DISTINCT, ordering, or source materialization
    is performed here.

    Numeric columns are also checked for evidence that their
    observed non-null values are confined to {0, 1}. This is
    structural/value evidence only; no domain meaning such as
    switch, flag, or state is inferred.
    """

    path = Path(file_path)

    if source_context is None:
        progress(
            "Opening long temporal dataset safely"
        )

        with SourceExecutionContext(
            file_path
        ) as owned_context:
            return profile_long_temporal_safe(
                file_path=file_path,
                inspection=inspection,
                analysis_strategy=analysis_strategy,
                source_context=owned_context,
            )

    source_context.assert_source(
        file_path
    )

    if not source_context.is_open:
        raise RuntimeError(
            "Supplied SourceExecutionContext "
            "must already be open"
        )

    connection = (
        source_context.require_connection()
    )

    column_names = (
        source_context.column_names
    )

    column_types = (
        source_context.column_types
    )

    progress(
        "Profiling long temporal columns"
    )

    expressions = [
        "COUNT(*) AS row_count"
    ]

    for index, (
        name,
        data_type,
    ) in enumerate(
        zip(
            column_names,
            column_types,
        )
    ):
        column = quote_identifier(
            name
        )

        expressions.append(
            f"""
            COUNT(*) FILTER (
                WHERE {column} IS NULL
            ) AS c{index}_nulls
            """
        )

        if (
            is_numeric_type(data_type)
            or is_temporal_type(data_type)
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

        if is_numeric_type(
            data_type
        ):
            expressions.append(
                f"""
                COUNT(*) FILTER (
                    WHERE {column} = 0
                ) AS c{index}_zero
                """
            )

            expressions.append(
                f"""
                COUNT(*) FILTER (
                    WHERE {column} = 1
                ) AS c{index}_one
                """
            )

            expressions.append(
                f"""
                COUNT(*) FILTER (
                    WHERE {column} IS NOT NULL
                      AND {column} NOT IN (0, 1)
                ) AS c{index}_other
                """
            )

    aggregate_sql = (
        "SELECT "
        + ", ".join(expressions)
        + " FROM rawsight_source"
    )

    aggregate_row = (
        connection.execute(
            aggregate_sql
        ).fetchone()
    )

    row_count = aggregate_row[0]

    result_position = 1

    columns = []
    total_missing = 0

    for (
        name,
        data_type,
    ) in zip(
        column_names,
        column_types,
    ):
        null_count = (
            aggregate_row[
                result_position
            ]
        )

        minimum = (
            aggregate_row[
                result_position + 1
            ]
        )

        maximum = (
            aggregate_row[
                result_position + 2
            ]
        )

        result_position += 3

        total_missing += (
            null_count
        )

        non_null_count = (
            row_count
            - null_count
        )

        null_percent = (
            null_count
            / row_count
            * 100
            if row_count
            else 0.0
        )

        binary_evidence = None

        if is_numeric_type(
            data_type
        ):
            zero_count = (
                aggregate_row[
                    result_position
                ]
            )

            one_count = (
                aggregate_row[
                    result_position + 1
                ]
            )

            other_count = (
                aggregate_row[
                    result_position + 2
                ]
            )

            result_position += 3

            if (
                non_null_count > 0
                and other_count == 0
            ):
                observed_values = []

                if zero_count > 0:
                    observed_values.append(
                        0
                    )

                if one_count > 0:
                    observed_values.append(
                        1
                    )

                binary_evidence = {
                    "kind": (
                        "binary_compatible_numeric"
                    ),
                    "observed_values": (
                        observed_values
                    ),
                    "observed_state_count": (
                        len(observed_values)
                    ),
                    "zero_count": zero_count,
                    "one_count": one_count,
                    "other_count": (
                        other_count
                    ),
                }

        columns.append({
            "name": name,
            "type": data_type,

            "null_count": (
                null_count
            ),
            "null_percent": round(
                null_percent,
                4,
            ),

            # Expensive generic cardinality is
            # deliberately not evaluated here.
            "distinct_count": None,
            "unique_percent": None,

            "min": json_safe(
                minimum
            ),
            "max": json_safe(
                maximum
            ),

            "semantic_hint": None,

            "value_evidence": (
                binary_evidence
            ),
        })

    total_cells = (
        row_count
        * len(columns)
    )

    missing_percent = (
        total_missing
        / total_cells
        * 100
        if total_cells
        else 0.0
    )

    structural_model = (
        inspection.get(
            "structural_model",
            {},
        )
    )

    logical_structure = (
        structural_model.get(
            "logical_structure",
            {},
        )
    )

    temporal_axis = (
        logical_structure.get(
            "temporal_axis"
        )
    )

    temporal_column_index = None
    temporal_column_name = None
    range_start = None
    range_end = None

    if (
        isinstance(
            temporal_axis,
            dict,
        )
        and temporal_axis.get(
            "orientation"
        ) == "vertical"
    ):
        candidate_index = (
            temporal_axis.get(
                "sequence_index"
            )
        )

        if (
            isinstance(
                candidate_index,
                int,
            )
            and 0 <= candidate_index
            < len(columns)
        ):
            temporal_column_index = (
                candidate_index
            )

            temporal_column = (
                columns[
                    candidate_index
                ]
            )

            temporal_column_name = (
                temporal_column[
                    "name"
                ]
            )

            range_start = (
                temporal_column[
                    "min"
                ]
            )

            range_end = (
                temporal_column[
                    "max"
                ]
            )

    progress(
        "Preparing long temporal overview"
    )

    return {
        "file": path.name,
        "rows": row_count,
        "column_count": len(
            columns
        ),

        "duplicate_rows": None,
        "duplicate_percent": None,

        "missing_values": (
            total_missing
        ),
        "missing_percent": round(
            missing_percent,
            4,
        ),

        "columns": columns,

        "analysis_strategy": (
            analysis_strategy
        ),

        "structural_model": (
            structural_model
        ),

        "long_temporal": {
            "status": "candidate",
            "axis_orientation": (
                "vertical"
                if temporal_column_index
                is not None
                else None
            ),
            "temporal_column_index": (
                temporal_column_index
            ),
            "temporal_column_name": (
                temporal_column_name
            ),
            "range_start": (
                range_start
            ),
            "range_end": (
                range_end
            ),
        },
    }

def profile_dataset(file_path: str) -> dict:
    """
    Route dataset analysis according to detected structural
    characteristics.

    Unsafe generic profiling is bypassed when structural evidence
    indicates that a specialized or conservative strategy is required.

    The routed DuckDB analysis phase shares one SourceExecutionContext.
    Source inspection remains a separate detection phase.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    progress(
        "Inspecting source structure"
    )

    inspection = inspect_source(
        file_path
    )

    structural_model = inspection.get(
        "structural_model",
        {},
    )

    analysis_strategy = (
        select_analysis_strategy(
            structural_model
        )
    )

    strategy = analysis_strategy[
        "strategy"
    ]

    progress(
        f"Analysis strategy: {strategy}"
    )

    progress(
        "Opening dataset safely"
    )

    with SourceExecutionContext(
        file_path
    ) as source_context:
        if strategy == "wide_temporal":
            return profile_wide_temporal_safe(
                file_path=file_path,
                inspection=inspection,
                analysis_strategy=analysis_strategy,
                source_context=source_context,
            )

        if strategy == "long_temporal":
             return profile_long_temporal_safe(
            file_path=file_path,
            inspection=inspection,
             analysis_strategy=analysis_strategy,
            source_context=source_context,
            )

        if strategy == "conservative_tabular":
            return profile_conservative_dataset(
                file_path=file_path,
                inspection=inspection,
                analysis_strategy=analysis_strategy,
                source_context=source_context,
            )

        return profile_conservative_dataset(
            file_path=file_path,
            inspection=inspection,
            analysis_strategy=analysis_strategy,
            source_context=source_context,
        )

def profile_wide_temporal_safe(
    file_path: str,
    inspection: dict,
    analysis_strategy: dict,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict:
    """
    Produce a safe profile for a wide temporal dataset.

    Structural profiling and wide-temporal value analysis share one
    source context. If called directly without a context, this function
    creates one context for both steps and closes it afterwards.
    """

    if source_context is None:
        progress(
            "Opening dataset safely"
        )

        with SourceExecutionContext(
            file_path
        ) as owned_context:
            return profile_wide_temporal_safe(
                file_path=file_path,
                inspection=inspection,
                analysis_strategy=analysis_strategy,
                source_context=owned_context,
            )

    source_context.assert_source(
        file_path
    )

    if not source_context.is_open:
        raise RuntimeError(
            "Supplied SourceExecutionContext "
            "must already be open"
        )

    profile = profile_conservative_dataset(
        file_path=file_path,
        inspection=inspection,
        analysis_strategy=analysis_strategy,
        source_context=source_context,
        count_rows=False,
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
            end_index
            - start_index
            + 1
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
        "temporal_column_start_index": (
            start_index
        ),
        "temporal_column_end_index": (
            end_index
        ),
        "temporal_column_count": (
            temporal_column_count
        ),
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

    value_execution = (
        execute_wide_temporal_analysis(
            file_path=file_path,
            temporal_axis=temporal_axis,
            progress=progress,
            source_context=source_context,
        )
    )

    profile["rows"] = (
        value_execution.get(
            "rows_processed"
        )
    )

    profile["wide_temporal"][
        "value_analysis"
    ] = value_execution.get(
        "analysis"
    )

    profile["wide_temporal"][
        "value_analysis_execution"
    ] = {
        "status": value_execution.get(
            "status"
        ),
        "execution_mode": (
            value_execution.get(
                "execution_mode"
            )
        ),
        "rows_processed": (
            value_execution.get(
                "rows_processed"
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
