from __future__ import annotations

import math
import statistics
from typing import Any

from rawsight.long_temporal_series_execution import (
    _build_temporal_expression,
    _is_numeric_type,
    _quote_identifier,
    _validate_temporal_axis,
)
from rawsight.source_context import SourceExecutionContext
from rawsight.long_temporal_series import temporal_to_json


def _describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "valid_count": 0,
            "mean": None,
            "stddev": None,
            "minimum": None,
            "maximum": None,
        }

    return {
        "valid_count": len(values),
        "mean": statistics.mean(values),
        "stddev": statistics.pstdev(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def analyze_temporal_gap_comparison(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    gap_start: str,
    gap_end: str,
    observations_per_side: int = 100,
) -> dict[str, Any]:
    """
    Compare real observations immediately before and after
    a caller-supplied temporal gap.

    The caller supplies gap boundaries established by
    an earlier continuity analysis.

    No values are interpolated inside the gap.
    """

    if (
        isinstance(observations_per_side, bool)
        or not isinstance(observations_per_side, int)
        or not 1 <= observations_per_side <= 10000
    ):
        raise ValueError(
            "observations_per_side must be an integer from 1 to 10000"
        )

    connection = source_context.require_connection()
    names = source_context.column_names
    types = source_context.column_types

    time_index = _validate_temporal_axis(
        temporal_axis, names
    )

    start, end = connection.execute(
        """
        SELECT
            TRY_CAST(? AS TIMESTAMP),
            TRY_CAST(? AS TIMESTAMP)
        """,
        [gap_start, gap_end],
    ).fetchone()

    if start is None or end is None or start >= end:
        raise ValueError(
            "Gap boundaries must be valid increasing timestamps"
        )

    time_expression = _build_temporal_expression(
        names[time_index],
        types[time_index],
        temporal_axis,
    )

    numeric_columns = [
        name
        for index, (name, dtype) in enumerate(
            zip(names, types)
        )
        if index != time_index and _is_numeric_type(dtype)
    ]

    view = _quote_identifier(source_context.view_name)

    projection = ", ".join(
        _quote_identifier(name)
        for name in numeric_columns
    )

    if not projection:
        projection = "NULL AS _rs_unused"

    sql = f"""
        WITH normalized AS (
            SELECT
                {time_expression} AS _rs_gap_time,
                {projection}
            FROM {view}
        )
        SELECT *
        FROM normalized
        WHERE _rs_gap_time IS NOT NULL
          AND _rs_gap_time {{operator}} ?
        ORDER BY _rs_gap_time {{direction}}
        LIMIT ?
    """

    before = connection.execute(
        sql.format(operator="<=", direction="DESC"),
        [start, observations_per_side],
    ).fetchall()

    after = connection.execute(
        sql.format(operator=">=", direction="ASC"),
        [end, observations_per_side],
    ).fetchall()

    before.reverse()

    def valid_values(rows, column_index):
        values = []

        for row in rows:
            raw = row[column_index + 1]

            if raw is None:
                continue

            try:
                value = float(raw)
            except (TypeError, ValueError, OverflowError):
                continue

            if math.isfinite(value):
                values.append(value)

        return values

    results = []

    for index, name in enumerate(numeric_columns):
        before_stats = _describe(
            valid_values(before, index)
        )
        after_stats = _describe(
            valid_values(after, index)
        )

        mean_before = before_stats["mean"]
        mean_after = after_stats["mean"]

        delta = (
            mean_after - mean_before
            if mean_before is not None
            and mean_after is not None
            else None
        )

        results.append({
            "column_name": name,
            "before": before_stats,
            "after": after_stats,
            "mean_delta": delta,
        })

    return {
        "analysis_kind": "temporal_gap_comparison",
        "status": (
            "measured" if before and after
            else "insufficient_data"
        ),
        "gap": {
            "start": temporal_to_json(start),
            "end": temporal_to_json(end),
            "duration_seconds": (
                end - start
            ).total_seconds(),
        },
        "temporal_column_name": names[time_index],
        "observations_per_side_requested": observations_per_side,
        "before_observation_count": len(before),
        "after_observation_count": len(after),
        "before_observed_range": (
            {
                "start": temporal_to_json(before[0][0]),
                "end": temporal_to_json(before[-1][0]),
            }
            if before else None
        ),
        "after_observed_range": (
            {
                "start": temporal_to_json(after[0][0]),
                "end": temporal_to_json(after[-1][0]),
            }
            if after else None
        ),
        "columns": results,
        "limitations": [
            "Gap boundaries are supplied by the caller.",
            "No observations are inferred inside the gap.",
            "Equal observation counts do not imply equal durations.",
            "Duplicate timestamps are not uniquely ordered.",
            "Changes are descriptive, not causal evidence.",
        ],
    }