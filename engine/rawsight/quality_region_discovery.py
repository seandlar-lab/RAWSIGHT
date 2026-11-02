"""RAWSIGHT v0.1: bounded, deterministic structural Analysis Region discovery.

Discovery proposes areas to inspect. It does not classify observations as erroneous,
choose a calendar period, discard rows or establish normal business behavior.
Designed to work with quality_evidence.assess_quality(..., regions=...).
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from statistics import median
from typing import Any

VERSION = 'quality-region-discovery-v0.1'
MAX_ROWS = 100_000
MAX_REGIONS = 100


def _time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _missing(value: Any) -> bool:
    return value is None or value == ''


def discover_quality_regions(
    rows: list[dict[str, Any]], *,
    time_column: str | None = None,
    value_columns: list[str] | None = None,
    max_regions: int = 40,
    gap_multiplier: float = 5.0,
    min_region_rows: int = 3,
) -> dict:
    """Propose contiguous source-row regions using observed structural transitions.

    The whole-dataset region is always returned. Additional row ranges are
    half-open [start, stop) and partition source order without loss or overlap.
    Failure to fit the region budget is disclosed; no partial partition is sold
    as exhaustive. A gap is a boundary *between* rows, not a bad observation.
    """
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise ValueError(f'rows must be a list of at most {MAX_ROWS} objects')
    if time_column is not None and (not isinstance(time_column, str) or not time_column):
        raise ValueError('time_column must be a nonempty string or None')
    if value_columns is None:
        value_columns = []
    if (not isinstance(value_columns, list) or
            any(not isinstance(c, str) or not c for c in value_columns) or
            len(set(value_columns)) != len(value_columns)):
        raise ValueError('value_columns must contain unique nonempty names')
    if type(max_regions) is not int or not 1 <= max_regions <= MAX_REGIONS:
        raise ValueError(f'max_regions must be between 1 and {MAX_REGIONS}')
    if not isinstance(gap_multiplier, (float, int)) or isinstance(gap_multiplier, bool) or not isfinite(gap_multiplier) or gap_multiplier <= 1:
        raise ValueError('gap_multiplier must be finite and > 1')
    if type(min_region_rows) is not int or min_region_rows < 1:
        raise ValueError('min_region_rows must be a positive integer')

    n = len(rows)
    whole = {'id': 'dataset', 'kind': 'whole'}
    findings: list[dict] = []
    boundaries: dict[int, set[str]] = {}
    if not rows:
        return {'version': VERSION, 'status': 'insufficient_data', 'regions': [whole],
                'boundaries': [], 'findings': [], 'limitations': ['Empty source.']}

    # Adjacent source-order timestamps only. Never sort or collapse duplicates.
    if time_column:
        stamps = [_time(r.get(time_column)) for r in rows]
        intervals = []
        for i in range(1, n):
            a, b = stamps[i - 1], stamps[i]
            if a is None or b is None:
                continue
            try:
                d = (b - a).total_seconds()
            except TypeError:
                findings.append({'kind': 'incomparable_timezones', 'row_before': i - 1, 'row_after': i})
                boundaries.setdefault(i, set()).add('incomparable_timezones')
                continue
            if isfinite(d) and d > 0:
                intervals.append(d)
        baseline = median(intervals) if intervals else None
        for i in range(1, n):
            a, b = stamps[i - 1], stamps[i]
            if a is None or b is None:
                boundaries.setdefault(i, set()).add('invalid_timestamp_transition')
                continue
            try:
                d = (b - a).total_seconds()
            except TypeError:
                continue
            if not isfinite(d):
                boundaries.setdefault(i, set()).add('invalid_time_interval')
            elif d == 0:
                boundaries.setdefault(i, set()).add('repeated_timestamp')
            elif d < 0:
                boundaries.setdefault(i, set()).add('reversed_time')
            elif baseline is not None and d > baseline * gap_multiplier:
                boundaries.setdefault(i, set()).add('large_observed_gap')
    else:
        baseline = None

    # For non-temporal data, changes between complete/incomplete records are
    # potentially meaningful structure (not proof of a data-quality problem).
    # For temporal data these are supplemental boundaries.
    if value_columns:
        signatures = [tuple(_missing(r.get(c)) for c in value_columns) for r in rows]
        for i in range(1, n):
            if signatures[i] != signatures[i-1]:
                boundaries.setdefault(i, set()).add('missingness_pattern_change')

    candidates = sorted(boundaries)
    if not candidates:
        return {'version': VERSION, 'status': 'whole_only', 'regions': [whole],
                'boundaries': [], 'findings': [], 'baseline_seconds': baseline,
                'limitations': ['No structural transition detected by the enabled checks; this is not proof of clean or normal data.']}

    # Prevent tiny islands by grouping adjacent transitions into clusters, while
    # preserving their original positions in boundary evidence. Region budget is
    # enforced without silently dropping transitions.
    groups: list[list[int]] = []
    for p in candidates:
        if groups and p - groups[-1][-1] <= min_region_rows:
            groups[-1].append(p)
        else:
            groups.append([p])
    # Two partitions around each group: stable stretch, change zone, stable stretch.
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for group in groups:
        start = max(cursor, group[0] - 1)
        end = min(n, group[-1] + 1)
        if start > cursor:
            spans.append((cursor, start, 'between_transitions'))
        if end > start:
            spans.append((start, end, 'transition_neighborhood'))
        cursor = end
    if cursor < n:
        spans.append((cursor, n, 'between_transitions'))
    if not spans or spans[0][0] != 0 or spans[-1][1] != n or any(a[1] != b[0] for a,b in zip(spans, spans[1:])):
        raise RuntimeError('Internal partition error')

    if len(spans) + 1 > max_regions:
        return {'version': VERSION, 'status': 'region_limit_exceeded', 'regions': [whole],
                'boundaries': [{'before_row': p - 1, 'after_row': p, 'reasons': sorted(boundaries[p])} for p in candidates[:max_regions]],
                'total_boundaries': len(candidates), 'required_regions': len(spans) + 1,
                'baseline_seconds': baseline,
                'findings': [{'kind':'region_limit_exceeded', 'total_boundaries':len(candidates), 'required_regions':len(spans) + 1}],
                'limitations': ['Full row partition not returned due to region limit; boundary preview is incomplete. Narrow scope or raise bound explicitly.']}

    regions = [whole]
    for k, (start, end, role) in enumerate(spans, 1):
        regions.append({'id': f'region_{k:03d}', 'kind': 'row_range', 'start': start,
                        'stop': end, 'discovery_role': role})
    for p in candidates:
        findings.append({'kind': 'structural_transition', 'row_before': p - 1,
                         'row_after': p, 'reasons': sorted(boundaries[p]),
                         'interpretation_status': 'observed'})
    return {'version': VERSION, 'status': 'partitioned', 'regions': regions,
            'boundaries': [{'before_row': p - 1, 'after_row': p, 'reasons': sorted(boundaries[p])} for p in candidates],
            'total_boundaries': len(candidates), 'baseline_seconds': baseline,
            'findings': findings,
            'limitations': ['Source-order regions do not establish normal behavior or correctness.',
                            'A structural transition may be the most significant discovery; no data were removed.',
                            'Time gaps describe absent observations between adjacent rows, not evidence of what happened during the gap.',
                            'The in-memory reference implementation is bounded to 100,000 rows.']}
