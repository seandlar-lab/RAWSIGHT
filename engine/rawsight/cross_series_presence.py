from __future__ import annotations

from datetime import datetime
from typing import Any

from rawsight.long_temporal_series_execution import (
    _build_temporal_expression,
    _is_numeric_type,
    _quote_identifier,
    _validate_temporal_axis,
)
from rawsight.source_context import SourceExecutionContext
from rawsight.long_temporal_series import temporal_to_json


def analyze_cross_series_presence(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    """
    Profile numeric column presence in one temporal interval.

    Uses the established temporal axis and original source.
    Does not detect anomalies or infer missing observations.
    """

    columns = source_context.column_names
    types = source_context.column_types

    temporal_index = _validate_temporal_axis(
        temporal_axis, columns
    )

    connection = source_context.require_connection()

    bounds = connection.execute(
        """
        SELECT
            TRY_CAST(? AS TIMESTAMP),
            TRY_CAST(? AS TIMESTAMP)
        """,
        [start_time, end_time],
    ).fetchone()

    start, end = bounds

    if start is None or end is None:
        raise ValueError("Invalid temporal interval")

    if end < start:
        raise ValueError("End precedes start")

    temporal_expression = _build_temporal_expression(
        columns[temporal_index],
        types[temporal_index],
        temporal_axis,
    )

    numeric_columns = [
        name
        for index, (name, dtype) in enumerate(
            zip(columns, types)
        )
        if index != temporal_index
        and _is_numeric_type(dtype)
    ]

    aggregates = ["COUNT(*) AS source_rows"]

    for index, name in enumerate(numeric_columns):
        q = _quote_identifier(name)
        v = f"TRY_CAST({q} AS DOUBLE)"
        valid = f"({v} IS NOT NULL AND ISFINITE({v}))"

        aggregates.extend([
            f"COUNT(*) FILTER (WHERE {valid}) AS v{index}",
            f"COUNT(*) FILTER (WHERE {q} IS NULL) AS m{index}",
            (
                f"COUNT(*) FILTER (WHERE {q} IS NOT NULL "
                f"AND NOT {valid}) AS i{index}"
            ),
            f"MIN({v}) FILTER (WHERE {valid}) AS lo{index}",
            f"MAX({v}) FILTER (WHERE {valid}) AS hi{index}",
        ])

    aggregate_sql = ",\n".join(aggregates)

    view = _quote_identifier(source_context.view_name)

    sql = f"""
        WITH normalized AS (
            SELECT
                *,
                {temporal_expression} AS _rs_time
            FROM {view}
        )
        SELECT {aggregate_sql}
        FROM normalized
        WHERE _rs_time >= ?
          AND _rs_time <= ?
    """

    row = connection.execute(sql, [start, end]).fetchone()
    if row is None:
        raise RuntimeError("Aggregation returned no result")

    count = int(row[0])
    results = []

    for index, name in enumerate(numeric_columns):
        offset = 1 + index * 5
        valid, missing, invalid, minimum, maximum = (
            row[offset:offset + 5]
        )

        valid = int(valid)
        missing = int(missing)
        invalid = int(invalid)

        assert valid + missing + invalid == count

        results.append({
            "column_name": name,
            "valid_count": valid,
            "missing_count": missing,
            "invalid_count": invalid,
            "minimum": minimum,
            "maximum": maximum,
        })

    return {
        "status": "measured" if count else "insufficient_data",
        "analysis_kind": "cross_series_presence",
        "requested_range": {
            "start": temporal_to_json(start),
            "end": temporal_to_json(end),
        },
        "temporal_column_name": columns[temporal_index],
        "source_row_count": count,
        "numeric_column_count": len(results),
        "columns": results,
        "limitations": [
            "Presence is evaluated on source rows with valid time.",
            "Missing source rows cannot be counted here.",
            "No anomaly classification is performed.",
        ],
    }