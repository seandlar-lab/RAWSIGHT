"""Source-backed discovery and comparison of bounded temporal-gap contexts.

One data source, explicitly selected numeric signals, observation-index alignment.
No interpolation, extrapolation, causality or significance assessment.
"""
from __future__ import annotations

from datetime import datetime
import math
from typing import Any

from rawsight.event_context_similarity import compare_event_contexts
from rawsight.event_context_execution import execute_event_context
from rawsight.long_temporal_series_execution import (
    _build_temporal_expression, _is_numeric_type, _quote_identifier,
    _validate_temporal_axis,
)
from rawsight.source_context import SourceExecutionContext


def _check_int(name: str, value: Any, lower: int, upper: int) -> None:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f'{name} must be an integer from {lower} to {upper}')


def _find_gaps(context: SourceExecutionContext, temporal_axis: dict[str, Any],
               expected_interval_seconds: float, gap_multiple: float,
               max_events: int,
               scan_start: datetime | None = None,
               scan_end: datetime | None = None) -> list[dict[str, Any]]:
    names, types = context.column_names, context.column_types
    axis = _validate_temporal_axis(temporal_axis, names)
    expression = _build_temporal_expression(names[axis], types[axis], temporal_axis)
    view = _quote_identifier(context.view_name)
    # Partition counts flag duplicate endpoints rather than treating duplicates as
    # safely ordered rows. Window LAG scans source times; LIMIT bounds results.
    bounds = ''
    parameters: list[Any] = [expected_interval_seconds * gap_multiple]
    if scan_start is not None:
        bounds += ' AND prior >= CAST(? AS TIMESTAMP)'
        parameters.append(scan_start)
    if scan_end is not None:
        bounds += ' AND t <= CAST(? AS TIMESTAMP)'
        parameters.append(scan_end)
    parameters.append(max_events + 1)
    sql = f'''WITH times AS (
        SELECT {expression} AS t FROM {view}
    ), ordered AS (
        SELECT t, LAG(t) OVER (ORDER BY t) AS prior,
               COUNT(*) OVER (PARTITION BY t) AS duplicates
        FROM times WHERE t IS NOT NULL
    ), gaps AS (
        SELECT prior, t, duplicates,
               EXTRACT(EPOCH FROM (t-prior)) AS duration_seconds
        FROM ordered WHERE prior IS NOT NULL
    )
    SELECT prior, t, duration_seconds, duplicates
    FROM gaps
    WHERE duration_seconds > ? {bounds}
    ORDER BY duration_seconds DESC, prior ASC, t ASC
    LIMIT ?'''
    records = context.require_connection().execute(
        sql, parameters
    ).fetchall()
    if len(records) > max_events:
        # Explicit rejection: a partial top-N candidate set must not be mistaken
        # for exhaustive event discovery.
        raise ValueError('More gaps than max_events; narrow the scope or increase the cap')
    results = []
    for prior, current, duration, duplicates in records:
        if duplicates != 1:
            raise ValueError('Temporal gap endpoint has duplicate timestamps')
        results.append({'id': f'gap:{prior.isoformat()}:{current.isoformat()}',
                        'anchor': {'kind':'temporal_gap',
                                   'before_time':prior.isoformat(),
                                   'after_time':current.isoformat()},
                        'gap_seconds': float(duration)})
    return results


def _side_rows(context: SourceExecutionContext, temporal_axis: dict[str, Any],
               selected_columns: list[str], endpoint: str, side: str,
               count: int) -> list[dict[str, Any]]:
    names, types = context.column_names, context.column_types
    axis = _validate_temporal_axis(temporal_axis, names)
    expression = _build_temporal_expression(names[axis], types[axis], temporal_axis)
    columns = ', '.join(f'TRY_CAST({_quote_identifier(col)} AS DOUBLE) AS {_quote_identifier(col)}'
                        for col in selected_columns)
    projection = ', '.join(_quote_identifier(col) for col in selected_columns)
    comparator, direction = ('<=', 'DESC') if side == 'before' else ('>=', 'ASC')
    query = (f'WITH normalized AS (SELECT {expression} AS t, {columns} '
             f'FROM {_quote_identifier(context.view_name)}) '
             f'SELECT t, {projection} FROM normalized '
             f'WHERE t IS NOT NULL AND t {comparator} CAST(? AS TIMESTAMP) '
             f'ORDER BY t {direction} LIMIT ?')
    raw = context.require_connection().execute(query, [endpoint, count]).fetchall()
    if side == 'before':
        raw.reverse()
    return [{'time':row[0].isoformat(), **dict(zip(selected_columns, row[1:]))}
            for row in raw]


def _contiguous_tail(rows: list[dict[str, Any]], side: str,
                     threshold_seconds: float) -> list[dict[str, Any]]:
    """Only keep the continuous portion touching the event's endpoint."""
    if not rows:
        return []
    # Query order is chronological for either side. Stop at the first further gap.
    if side == 'before':
        sequence = list(reversed(rows))
    else:
        sequence = rows
    kept = [sequence[0]]
    for record in sequence[1:]:
        dt = abs((datetime.fromisoformat(record['time']) -
                  datetime.fromisoformat(kept[-1]['time'])).total_seconds())
        if dt <= 0:
            raise ValueError('Duplicate or unsorted observation timestamps in event window')
        if dt > threshold_seconds:
            break
        kept.append(record)
    return list(reversed(kept)) if side == 'before' else kept


def _aligned_side(rows: list[dict[str, Any]], selected_columns: list[str],
                  bins: int) -> dict[str, Any]:
    if len(rows) != bins:
        # no silent truncation or padding: report unscorable segment
        values = {column: [None] * bins for column in selected_columns}
    else:
        values = {column: [row.get(column) for row in rows] for column in selected_columns}
    return {'series': values,
            'alignment': {'method':'observation_index', 'bin_count': bins}}


def execute_event_context_similarity(
    *, file_path: str, temporal_axis: dict[str, Any],
    selected_columns: list[str], expected_interval_seconds: float,
    gap_multiple: float = 3.0, points_per_side: int = 30,
    max_events: int = 20, minimum_points: int = 3,
    minimum_coverage: float = 1.0,
    minimum_measured_signals: int = 1,
    target_event_id: str | None = None,
    gap_scan_start: str | None = None,
    gap_scan_end: str | None = None,
    source_context: SourceExecutionContext | None = None,
) -> dict[str, Any]:
    """Find all gaps up to an explicit cap; compare each to the longest gap.

    target_event_id optionally selects any discovered gap. All matching
    evidence uses exactly points_per_side *source observations* on each side.
    """
    _check_int('points_per_side', points_per_side, 3, 1000)
    _check_int('max_events', max_events, 2, 100)
    _check_int('minimum_points', minimum_points, 3, points_per_side)
    if not isinstance(selected_columns, list) or not selected_columns or any(
        not isinstance(x, str) or not x for x in selected_columns
    ) or len(set(selected_columns)) != len(selected_columns):
        raise ValueError('selected_columns must be unique nonempty numeric names')
    _check_int('minimum_measured_signals', minimum_measured_signals, 1, len(selected_columns))
    for name, value in (('expected_interval_seconds',expected_interval_seconds),
                        ('gap_multiple',gap_multiple)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'{name} must be finite')
    if expected_interval_seconds <= 0 or gap_multiple <= 1:
        raise ValueError('Invalid continuity threshold')
    if isinstance(minimum_coverage,bool) or not isinstance(minimum_coverage,(int,float)) or not (0 < minimum_coverage <= 1):
        raise ValueError('minimum_coverage must be in (0, 1]')

    def parse_bound(label: str, value: str | None) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{label} must be an ISO 8601 timestamp string')
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f'{label} must be an ISO 8601 timestamp string') from exc
        if parsed.tzinfo is not None:
            raise ValueError(f'{label} must be timezone-naive, matching the source axis')
        return parsed

    scan_start = parse_bound('gap_scan_start', gap_scan_start)
    scan_end = parse_bound('gap_scan_end', gap_scan_end)
    if scan_start is not None and scan_end is not None and scan_start >= scan_end:
        raise ValueError('gap_scan_start must be earlier than gap_scan_end')

    def run(context: SourceExecutionContext) -> dict[str, Any]:
        if not context.is_open:
            raise RuntimeError('SourceExecutionContext must be open')
        axis = _validate_temporal_axis(temporal_axis, context.column_names)
        numeric = {name for i,(name,typ) in enumerate(zip(context.column_names,context.column_types))
                   if i != axis and _is_numeric_type(typ)}
        if any(name not in numeric for name in selected_columns):
            raise ValueError('Selected columns must be numeric source columns')
        events = _find_gaps(context, temporal_axis, expected_interval_seconds,
                            gap_multiple, max_events, scan_start, scan_end)
        if target_event_id is not None and (not isinstance(target_event_id, str) or not target_event_id):
            raise ValueError('target_event_id must be a nonempty string')
        if target_event_id is not None and target_event_id not in {e['id'] for e in events}:
            raise ValueError('target_event_id not found among discovered gaps')
        if len(events) < 2:
            return {'analysis_kind':'event_context_similarity_execution',
                    'status':'insufficient_events', 'events':events,
                    'gap_scan_scope':{'start':gap_scan_start,'end':gap_scan_end},
                    'comparison':None}
        target_id = target_event_id or events[0]['id']
        threshold = expected_interval_seconds * gap_multiple
        prepared = []
        for event in events:
            # Existing trusted adapter verifies both anchors are real, adjacent,
            # unique and belong to this source. Its summary also checks continuity.
            summary = execute_event_context(
                file_path=file_path, temporal_axis=temporal_axis,
                anchor=event['anchor'], selected_columns=selected_columns,
                expected_interval_seconds=expected_interval_seconds,
                gap_multiple=gap_multiple, before_points=points_per_side,
                after_points=points_per_side, source_context=context,
            )
            sides = {}
            counts = {}
            timing = {}
            for side, endpoint in (('before',event['anchor']['before_time']),
                                   ('after',event['anchor']['after_time'])):
                fetched = _side_rows(context, temporal_axis, selected_columns,
                                     endpoint, side, points_per_side)
                contiguous = _contiguous_tail(fetched, side, threshold)
                if len(contiguous) != summary[side]['observation_count']:
                    raise RuntimeError('Context and source windows disagree')
                sides[side] = _aligned_side(contiguous, selected_columns, points_per_side)
                counts[side] = len(contiguous)
                if contiguous:
                    first_time = datetime.fromisoformat(contiguous[0]['time'])
                    last_time = datetime.fromisoformat(contiguous[-1]['time'])
                    timing[side] = {
                        'first_time': contiguous[0]['time'],
                        'last_time': contiguous[-1]['time'],
                        'elapsed_seconds': (last_time - first_time).total_seconds(),
                        'complete_requested_window': len(contiguous) == points_per_side,
                    }
                else:
                    timing[side] = {'elapsed_seconds': None, 'complete_requested_window': False}
            prepared.append({'id':event['id'], **sides})
            event['context_observation_counts'] = counts
            event['context_time_spans'] = timing
        target = next(x for x in prepared if x['id'] == target_id)
        candidates = [x for x in prepared if x['id'] != target_id]
        result = compare_event_contexts(
            target, candidates, selected_columns=selected_columns,
            minimum_points=minimum_points, minimum_coverage=minimum_coverage,
            minimum_measured_signals=minimum_measured_signals,
            max_candidates=max_events-1,
        )
        target_timings = next(e['context_time_spans'] for e in events if e['id'] == target_id)
        for candidate in result['candidates']:
            candidate_times = next(e['context_time_spans'] for e in events if e['id'] == candidate['candidate_id'])
            candidate['temporal_comparability'] = {}
            for side in ('before', 'after'):
                a = target_timings[side]['elapsed_seconds']
                b = candidate_times[side]['elapsed_seconds']
                if a is not None and b is not None and a > 0 and b > 0:
                    ratio = max(a, b) / min(a, b)
                    candidate['temporal_comparability'][side] = {
                        'elapsed_span_ratio': ratio,
                        'same_elapsed_span': abs(a - b) < 1e-9,
                        'target_elapsed_seconds': a,
                        'candidate_elapsed_seconds': b,
                        'warning': 'unequal_elapsed_time' if ratio > 1.25 else None,
                    }
                else:
                    candidate['temporal_comparability'][side] = {
                        'elapsed_span_ratio': None, 'same_elapsed_span': False,
                        'target_elapsed_seconds': a, 'candidate_elapsed_seconds': b,
                        'warning': 'unavailable_elapsed_time',
                    }
        return {
            'analysis_kind':'event_context_similarity_execution',
            'method':'verified_gaps_observation_index_v0_1',
            'status':result['status'], 'target_event_id':target_id,
            'events':events, 'comparison':result,
            'gap_scan_scope':{'start':str(gap_scan_start) if gap_scan_start is not None else None,
                              'end':str(gap_scan_end) if gap_scan_end is not None else None},
            'execution':{'mode':'duckdb_gap_scan_and_bounded_windows',
                         'sampled':False, 'points_per_side':points_per_side,
                         'max_events':max_events,'target_rule':'longest_gap_first' if target_event_id is None else 'explicit'},
            'limitations':[
                'All gaps within the declared scan window must fit within max_events; no partial discovery is returned.',
                'Observation-index alignment does not imply equal elapsed durations or matching physical phases.',
                'Elapsed-time span differences are flagged, not incorporated into shape scoring.',
                'Short or interrupted event sides are marked insufficient; no resampling or interpolation.',
                'Shape similarity is correlation-based and may be high for simple monotonic trends.',
                'No causality, predictive value, statistical significance or anomaly classification is inferred.',
            ],
        }
    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as owned:
        return run(owned)

