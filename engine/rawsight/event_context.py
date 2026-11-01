"""Domain-neutral observation context surrounding supplied event anchors.

No event detection, interpolation, causality, or anomaly classification.
Window sizes are counts of source observations (not elapsed time).
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _parse(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('timestamps must be ISO strings')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc


def analyze_event_context(
    observations: list[dict[str, Any]],
    *,
    anchor: dict[str, Any],
    selected_columns: list[str],
    expected_interval_seconds: float,
    gap_multiple: float = 3.0,
    before_points: int = 30,
    after_points: int = 30,
    timestamp_key: str = 'time',
) -> dict[str, Any]:
    """Describe immediate context for either a gap or a point event.

    anchor = {'kind':'temporal_gap', 'before_time':ISO, 'after_time':ISO}
          or {'kind':'point_event', 'time':ISO, 'label': 'extreme_value'}.
    Point-event windows exclude the anchor observation, which is returned separately.
    A context window stops at any earlier/later temporal discontinuity.
    """
    if not isinstance(observations, list):
        raise ValueError('observations must be a list')
    if not isinstance(anchor, dict):
        raise ValueError('anchor must be an object')
    if not isinstance(selected_columns, list) or not selected_columns or not all(isinstance(c, str) and c and c != timestamp_key for c in selected_columns) or len(selected_columns) != len(set(selected_columns)):
        raise ValueError('selected_columns must be unique non-time names')
    for key, value in [('before_points',before_points),('after_points',after_points)]:
        if type(value) is not int or value < 1:
            raise ValueError(f'{key} must be an integer >= 1')
    if isinstance(expected_interval_seconds, bool) or not isinstance(expected_interval_seconds,(int,float)) or not math.isfinite(expected_interval_seconds) or expected_interval_seconds <= 0:
        raise ValueError('expected_interval_seconds must be positive finite')
    if isinstance(gap_multiple, bool) or not isinstance(gap_multiple,(int,float)) or not math.isfinite(gap_multiple) or gap_multiple <= 1:
        raise ValueError('gap_multiple must be >1 finite')
    if any(not isinstance(row,dict) for row in observations):
        raise ValueError('every observation must be an object')
    stamps = [_parse(row.get(timestamp_key)) for row in observations]
    for x,y in zip(stamps, stamps[1:]):
        try:
            dt=(y-x).total_seconds()
        except TypeError as exc:
            raise ValueError('inconsistent timezone semantics') from exc
        if dt <= 0:
            raise ValueError('timestamps must be strictly increasing')
    times={t.isoformat():i for i,t in enumerate(stamps)}
    threshold=expected_interval_seconds*gap_multiple
    kind=anchor.get('kind')
    if kind == 'temporal_gap':
        t1,t2=_parse(anchor.get('before_time')),_parse(anchor.get('after_time'))
        a,b=times.get(t1.isoformat()),times.get(t2.isoformat())
        if a is None or b is None or b != a+1:
            raise ValueError('temporal_gap anchor must reference consecutive source observations')
        gap=(stamps[b]-stamps[a]).total_seconds()
        if gap <= threshold:
            raise ValueError('temporal_gap must exceed continuity threshold')
        before_end,after_start=a,b
        anchor_row=None
        anchor_metadata={'kind':kind,'before_time':observations[a][timestamp_key], 'after_time':observations[b][timestamp_key], 'gap_seconds':gap}
    elif kind == 'point_event':
        t=_parse(anchor.get('time'))
        index=times.get(t.isoformat())
        if index is None:
            raise ValueError('point event must reference an existing observation')
        before_end = index-1 if index > 0 and (stamps[index]-stamps[index-1]).total_seconds() <= threshold else -1
        after_start = index+1 if index+1 < len(stamps) and (stamps[index+1]-stamps[index]).total_seconds() <= threshold else len(stamps)
        anchor_row={name:observations[index].get(name) for name in selected_columns}
        anchor_metadata={'kind':kind,'time':observations[index][timestamp_key], 'label':anchor.get('label')}
    else:
        raise ValueError('unsupported anchor kind')

    def collect(start:int, step:int, limit:int) -> list[int]:
        result=[]
        i=start
        while 0 <= i < len(observations) and len(result)<limit:
            if result:
                prev=result[-1]
                delta=abs((stamps[prev]-stamps[i]).total_seconds())
                if delta > threshold:
                    break
            result.append(i)
            i+=step
        if step < 0:
            result.reverse()
        return result

    def describe(indices:list[int]) -> dict[str,Any]:
        columns={}
        for name in selected_columns:
            values=[_num(observations[i].get(name)) for i in indices]
            good=[v for v in values if v is not None]
            columns[name]={
                'valid_count':len(good), 'coverage':len(good)/len(indices) if indices else 0.0,
                'first_value': next((v for v in values if v is not None),None),
                'last_value':next((v for v in reversed(values) if v is not None),None),
                'delta':(good[-1]-good[0]) if len(good)>=2 else None,
                'minimum':min(good) if good else None,'maximum':max(good) if good else None,
            }
        return {'observation_count':len(indices),
                'start_time':observations[indices[0]][timestamp_key] if indices else None,
                'end_time':observations[indices[-1]][timestamp_key] if indices else None,
                'columns':columns}
    before=describe(collect(before_end,-1,before_points))
    after=describe(collect(after_start,1,after_points))
    return {'analysis_kind':'event_context', 'method':'bounded_observation_context_v0_1',
            'status':'measured' if before['observation_count'] and after['observation_count'] else 'insufficient_context',
            'anchor':anchor_metadata, 'anchor_values':anchor_row,
            'selected_columns':list(selected_columns), 'before':before, 'after':after,
            'window_spec':{'unit':'observations','before_points':before_points,'after_points':after_points,
                           'expected_interval_seconds':expected_interval_seconds,'gap_multiple':gap_multiple},
            'limitations':[
                'Anchor is supplied by the caller; this function does not detect events.',
                'Fixed observation-count windows do not represent identical elapsed durations.',
                'Windows stop at detected gaps; no interpolation or imputation.',
                'First-to-last deltas describe each side independently, not changes across gaps.',
                'No similarity, anomaly, normality or causal assessment is made.',
            ]}
