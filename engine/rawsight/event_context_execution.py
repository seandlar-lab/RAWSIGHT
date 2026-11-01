"""Bounded source-backed event context around a *supplied* gap or point anchor.

No detection, re-sampling, interpolation or causal attribution. Query source-local
chronological observations through RAWSIGHT's SourceExecutionContext.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from rawsight.event_context import analyze_event_context
from rawsight.long_temporal_series_execution import (
    _build_temporal_expression, _is_numeric_type, _quote_identifier,
    _validate_temporal_axis,
)
from rawsight.source_context import SourceExecutionContext


def _local_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f'{name} must be a nonempty ISO datetime string')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{name} is not a valid ISO datetime') from exc
    if parsed.tzinfo is not None:
        raise ValueError('Only timezone-naive source-local timestamps are supported')
    return parsed


def execute_event_context(
    *,
    file_path: str,
    temporal_axis: dict[str, Any],
    anchor: dict[str, Any],
    selected_columns: list[str],
    expected_interval_seconds: float,
    gap_multiple: float = 3.0,
    before_points: int = 30,
    after_points: int = 30,
    max_points_per_side: int = 1000,
    source_context: SourceExecutionContext | None = None,
) -> dict[str, Any]:
    """Describe source observations near an already supplied event anchor.

    Temporal gap anchor: {'kind':'temporal_gap', 'before_time':ISO,
                          'after_time':ISO}. Both endpoint observations
    must exist uniquely with no intervening source observation.
    Point anchor: {'kind':'point_event', 'time':ISO, 'label':...}.
    No implicit signal selection; requests must name numeric columns.
    """
    if not isinstance(anchor, dict) or anchor.get('kind') not in ('temporal_gap', 'point_event'):
        raise ValueError('anchor must specify temporal_gap or point_event')
    if type(before_points) is not int or type(after_points) is not int or before_points < 1 or after_points < 1:
        raise ValueError('before_points and after_points must be positive integers')
    if type(max_points_per_side) is not int or max_points_per_side < 1:
        raise ValueError('max_points_per_side must be a positive integer')
    if before_points > max_points_per_side or after_points > max_points_per_side:
        raise ValueError('Requested window exceeds max_points_per_side; no truncation performed')
    if isinstance(expected_interval_seconds, bool) or not isinstance(expected_interval_seconds, (int,float)) or not math.isfinite(expected_interval_seconds) or expected_interval_seconds <= 0:
        raise ValueError('expected_interval_seconds must be positive and finite')
    if isinstance(gap_multiple, bool) or not isinstance(gap_multiple, (int,float)) or not math.isfinite(gap_multiple) or gap_multiple <= 1:
        raise ValueError('gap_multiple must be finite and greater than one')
    if not isinstance(selected_columns, list) or not selected_columns or any(not isinstance(c,str) or not c for c in selected_columns) or len(set(selected_columns)) != len(selected_columns):
        raise ValueError('selected_columns must be a nonempty list of unique column names')
    kind = anchor['kind']
    if kind == 'temporal_gap':
        before = _local_time(anchor.get('before_time'), 'before_time')
        after = _local_time(anchor.get('after_time'), 'after_time')
        if before >= after:
            raise ValueError('gap before_time must precede after_time')
        if (after-before).total_seconds() <= expected_interval_seconds*gap_multiple:
            raise ValueError('Supplied interval is not a gap under the specified threshold')
    else:
        point = _local_time(anchor.get('time'), 'time')

    def run(context: SourceExecutionContext) -> dict[str, Any]:
        if not context.is_open:
            raise RuntimeError('Supplied SourceExecutionContext must already be open')
        names, types = context.column_names, context.column_types
        axis = _validate_temporal_axis(temporal_axis, names)
        time_name, time_type = names[axis], types[axis]
        numeric = {name for i,(name,typ) in enumerate(zip(names,types)) if i != axis and _is_numeric_type(typ)}
        if any(col not in numeric for col in selected_columns):
            raise ValueError('selected_columns must be technically numeric source columns')
        texpr = _build_temporal_expression(time_name,time_type,temporal_axis)
        columns = ', '.join(f'TRY_CAST({_quote_identifier(c)} AS DOUBLE) AS {_quote_identifier(c)}' for c in selected_columns)
        selected = ', '.join(_quote_identifier(c) for c in selected_columns)
        cte = f'WITH normalized AS (SELECT {texpr} AS observation_time, {columns} FROM {_quote_identifier(context.view_name)}) '
        db = context.require_connection()

        def fetch(predicate: str, parameters: list[Any], order: str, limit: int) -> list[tuple[Any,...]]:
            sql = (cte + f'SELECT observation_time, {selected} FROM normalized '
                   f'WHERE observation_time IS NOT NULL AND {predicate} '
                   f'ORDER BY observation_time {order} LIMIT ?')
            return db.execute(sql, [*parameters,limit]).fetchall()

        def packed(rows: list[tuple[Any,...]]) -> list[dict[str,Any]]:
            return [dict(time=row[0].isoformat(), **dict(zip(selected_columns, row[1:]))) for row in rows]

        if kind == 'temporal_gap':
            # Query nearest source rows. Two extra rows expose duplicates at
            # either anchor without silently treating a duplicate as adjacent.
            left = fetch('observation_time <= CAST(? AS TIMESTAMP)', [before.isoformat()], 'DESC', before_points+1)
            right = fetch('observation_time >= CAST(? AS TIMESTAMP)', [after.isoformat()], 'ASC', after_points+1)
            if not left or not right or left[0][0] != before or right[0][0] != after:
                raise ValueError('Gap endpoints must each reference a source observation')
            if len(left)>1 and left[1][0] == before or len(right)>1 and right[1][0] == after:
                raise ValueError('Gap endpoints must have unique timestamps')
            interior = db.execute(
                cte + 'SELECT 1 FROM normalized WHERE observation_time > CAST(? AS TIMESTAMP) '
                      'AND observation_time < CAST(? AS TIMESTAMP) LIMIT 1',
                [before.isoformat(), after.isoformat()],
            ).fetchall()
            if interior:
                raise ValueError('Supplied gap endpoints are not consecutive source observations')
            observations = packed(list(reversed(left[:before_points])) + right[:after_points])
        else:
            center = fetch('observation_time = CAST(? AS TIMESTAMP)',[point.isoformat()],'ASC',2)
            if len(center) != 1:
                raise ValueError('Point anchor must refer to exactly one source observation')
            left = fetch('observation_time < CAST(? AS TIMESTAMP)',[point.isoformat()],'DESC',before_points)
            right = fetch('observation_time > CAST(? AS TIMESTAMP)',[point.isoformat()],'ASC',after_points)
            observations = packed(list(reversed(left)) + center + right)

        result = analyze_event_context(
            observations, anchor=anchor, selected_columns=selected_columns,
            expected_interval_seconds=expected_interval_seconds,
            gap_multiple=gap_multiple, before_points=before_points,
            after_points=after_points,
        )
        return {**result, 'execution': {
            'mode':'duckdb_bounded_source_observations',
            'source_order_used':False,
            'temporal_order':'parsed_time_ascending',
            'observations_retrieved':len(observations),
            'max_points_per_side':max_points_per_side,
            'anchor_verified_against_source':True,
            'sampled':False,
        }}

    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as owned:
        return run(owned)
