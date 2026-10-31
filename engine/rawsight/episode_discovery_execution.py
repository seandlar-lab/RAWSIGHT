"""Bounded, context-aware execution of domain-neutral episode discovery.

Uses RAWSIGHT's established vertical temporal-axis metadata and source view.
Never passes a reduced visualization projection as if it were original data.
"""
from __future__ import annotations

import math
from typing import Any

from rawsight.episode_discovery import discover_episodes
from rawsight.long_temporal_series_execution import (
    _build_temporal_expression,
    _is_numeric_type,
    _quote_identifier,
    _validate_temporal_axis,
)
from rawsight.source_context import SourceExecutionContext


def execute_episode_discovery(
    *,
    file_path: str,
    temporal_axis: dict[str, Any],
    start_time: str,
    end_time: str,
    expected_interval_seconds: float,
    selected_columns: list[str] | None = None,
    gap_multiple: float = 3.0,
    change_thresholds: dict[str, float] | None = None,
    minimum_changed_signals: int = 2,
    minimum_episode_points: int = 3,
    max_observations: int = 100_000,
    source_context: SourceExecutionContext | None = None,
) -> dict[str, Any]:
    """Analyze exact source observations in an explicit bounded time interval.

    No resampling, implicit downsampling, or inferred anomaly labels.
    If source exceeds max_observations, return resource_limit without episodes.
    Duplicate timestamps are rejected by discover_episodes, not silently merged.
    """
    if isinstance(max_observations, bool) or not isinstance(max_observations, int) or max_observations < 2:
        raise ValueError("max_observations must be an integer >= 2")
    if not isinstance(start_time, str) or not isinstance(end_time, str) or not start_time or not end_time:
        raise ValueError("start_time and end_time must be nonempty ISO datetime strings")
    if not isinstance(expected_interval_seconds, (int, float)) or isinstance(expected_interval_seconds, bool) or not math.isfinite(expected_interval_seconds) or expected_interval_seconds <= 0:
        raise ValueError("expected_interval_seconds must be positive and finite")

    def run(context: SourceExecutionContext) -> dict[str, Any]:
        if not context.is_open:
            raise RuntimeError("Supplied SourceExecutionContext must already be open")
        names = context.column_names
        types = context.column_types
        axis_index = _validate_temporal_axis(temporal_axis, names)
        time_name, time_type = names[axis_index], types[axis_index]
        numeric = [name for i, (name, typ) in enumerate(zip(names, types))
                   if i != axis_index and _is_numeric_type(typ)]
        columns = sorted(numeric) if selected_columns is None else list(selected_columns)
        if len(columns) != len(set(columns)) or not set(columns).issubset(numeric):
            raise ValueError("selected_columns must be unique technically numeric source columns")
        if not columns:
            raise ValueError("Episode discovery requires at least one numeric signal")
        if change_thresholds and not set(change_thresholds).issubset(columns):
            raise ValueError("change_thresholds must reference selected_columns")
        temporal_expr = _build_temporal_expression(time_name, time_type, temporal_axis)
        view = _quote_identifier(context.view_name)
        selects = ", ".join(
            f"TRY_CAST({_quote_identifier(name)} AS DOUBLE) AS {_quote_identifier(name)}"
            for name in columns
        )
        # Query fetches one additional observation to detect truncation. No
        # LIMIT-induced pseudo-episode is emitted when source is too large.
        sql = f"""
            WITH normalized AS (
                SELECT {temporal_expr} AS observation_time, {selects}
                FROM {view}
            )
            SELECT observation_time, {', '.join(_quote_identifier(c) for c in columns)}
            FROM normalized
            WHERE observation_time IS NOT NULL
              AND observation_time >= TRY_CAST(? AS TIMESTAMP)
              AND observation_time <= TRY_CAST(? AS TIMESTAMP)
            ORDER BY observation_time
            LIMIT ?
        """
        connection = context.require_connection()
        # Explicit type validation: avoid valid SQL but invalid date strings
        # being interpreted as an empty selection.
        from datetime import datetime
        try:
            beginning = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            ending = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("start_time and end_time must be valid ISO datetimes") from exc
        if beginning >= ending:
            raise ValueError("start_time must precede end_time")
        if beginning.tzinfo is not None or ending.tzinfo is not None:
            raise ValueError("This execution route expects timezone-naive source-local timestamps")
        rows = connection.execute(sql, [start_time, end_time, max_observations + 1]).fetchall()
        meta = {
            "mode": "duckdb_original_observations_bounded",
            "requested_range": {"start": start_time, "end": end_time},
            "max_observations": max_observations,
            "selected_columns": columns,
            "observations_retrieved": len(rows),
            "source_order_used": False,
            "temporal_display_order": "parsed_time_ascending",
        }
        if len(rows) > max_observations:
            return {
                "analysis_kind": "automatic_episode_discovery",
                "status": "resource_limit",
                "method": "gap_and_explicit_concurrent_change_v0_1",
                "observation_count": None,
                "episode_count": 0,
                "boundaries": [],
                "episodes": [],
                "columns_considered": columns,
                "execution": meta,
                "limitations": ["Requested interval exceeds resource limit; no partial episode discovery performed. Narrow the interval or raise max_observations."],
            }
        observations = [
            {"time": row[0].isoformat(), **dict(zip(columns, row[1:]))}
            for row in rows
        ]
        result = discover_episodes(
            observations,
            expected_interval_seconds=expected_interval_seconds,
            selected_columns=columns,
            gap_multiple=gap_multiple,
            change_thresholds=change_thresholds,
            minimum_changed_signals=minimum_changed_signals,
            minimum_episode_points=minimum_episode_points,
        )
        return {**result, "execution": meta}

    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as owned:
        return run(owned)
