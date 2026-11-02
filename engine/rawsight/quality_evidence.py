"""Domain-neutral, deterministic quality evidence over caller-selected regions.

No implicit calendar buckets, cleaning, imputation, normality, or quality score.
This is a bounded in-memory reference implementation, not a CSV executor.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from math import isfinite
from typing import Any

VERSION = 'quality-evidence-v0.1'
MAX_ROWS = 100_000
MAX_REGIONS = 100


def _parse_time(value: Any) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _select(rows: list[dict], region: dict, time_column: str | None) -> list[dict]:
    kind = region.get('kind')
    if kind == 'whole':
        return rows
    if kind == 'row_range':
        start, stop = region.get('start'), region.get('stop')
        if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= len(rows):
            raise ValueError('row_range requires 0 <= start < stop <= number of rows')
        return rows[start:stop]
    if kind == 'category':
        col, value = region.get('column'), region.get('value')
        if not isinstance(col, str) or not col:
            raise ValueError('category requires a column')
        return [row for row in rows if row.get(col) == value]
    if kind == 'time_range':
        if not time_column:
            raise ValueError('time_range requires time_column')
        start, end = _parse_time(region.get('start')), _parse_time(region.get('end'))
        if start is None or end is None:
            raise ValueError('time_range start/end must be ISO timestamps')
        try:
            if start >= end:
                raise ValueError('time_range requires start < end')
            return [row for row in rows if (t := _parse_time(row.get(time_column))) is not None and start <= t < end]
        except TypeError as exc:
            raise ValueError('mixed timezone semantics in time_range') from exc
    raise ValueError(f'unknown region kind: {kind!r}')


def _finding(region_id: str, column: str | None, polarity: str, kind: str,
             message: str, evidence: dict) -> dict:
    return {'region_id': region_id, 'column': column, 'polarity': polarity,
            'kind': kind, 'message': message, 'evidence': evidence,
            'interpretation_status': 'observed', 'source': VERSION}


def assess_quality(
    rows: list[dict[str, Any]], *,
    regions: list[dict] | None = None,
    time_column: str | None = None,
    columns: list[str] | None = None,
) -> dict:
    """Evaluate explicit regions; default to the whole dataset.

    Regions: {'id':str, 'kind':'whole'|'row_range'|'category'|'time_range', ...}.
    Row ranges are half-open; time ranges [start,end). The caller chooses
    regions; this function does not discover a business-relevant partition.
    """
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise ValueError(f'rows must be a list of at most {MAX_ROWS} objects')
    regions = [{'id': 'dataset', 'kind': 'whole'}] if regions is None else regions
    if not isinstance(regions, list) or len(regions) > MAX_REGIONS:
        raise ValueError(f'up to {MAX_REGIONS} regions required')
    names = [r.get('id') for r in regions if isinstance(r, dict)]
    if len(names) != len(regions) or any(not isinstance(x, str) or not x for x in names) or len(names) != len(set(names)):
        raise ValueError('region IDs must be nonempty and unique')
    if time_column is not None and (not isinstance(time_column, str) or not time_column):
        raise ValueError('time_column must be a nonempty name or None')
    if columns is None:
        columns = sorted(set().union(*(set(r.keys()) for r in rows))) if rows else []
    if not isinstance(columns, list) or len(columns) != len(set(columns)) or any(not isinstance(c, str) or not c for c in columns):
        raise ValueError('columns must be unique nonempty names')
    result_regions = []
    all_findings = []
    for region in regions:
        selected = _select(rows, region, time_column)
        region_id = region['id']
        findings = []
        if not selected:
            findings.append(_finding(region_id, None, 'insufficient', 'empty_region',
                                     'Inga observationer i regionen.', {'rows': 0}))
        else:
            for col in columns:
                missing = sum(row.get(col) is None or row.get(col) == '' for row in selected)
                if missing == 0:
                    findings.append(_finding(region_id, col, 'positive', 'complete_column',
                                             'Inga saknade värden observerades för fältet.',
                                             {'rows': len(selected), 'missing': 0}))
                else:
                    findings.append(_finding(region_id, col, 'attention', 'missing_values',
                                             'Fältet innehåller saknade värden.',
                                             {'rows': len(selected), 'missing': missing}))
            if time_column:
                stamps = [_parse_time(row.get(time_column)) for row in selected]
                valid = [t for t in stamps if t is not None]
                invalid = len(stamps) - len(valid)
                if invalid:
                    findings.append(_finding(region_id, time_column, 'attention', 'invalid_timestamps',
                                             'Tidsfältet har saknade eller ogiltiga tidpunkter.',
                                             {'invalid_or_missing': invalid}))
                if valid:
                    extra = len(valid) - len(set(valid))
                    if extra:
                        findings.append(_finding(region_id, time_column, 'attention', 'repeated_timestamps',
                                                 'Flera observationer delar tidpunkt; det innebär inte automatiskt felaktiga rader.',
                                                 {'extra_rows_beyond_unique_timestamps': extra,
                                                  'distinct_timestamps': len(set(valid))}))
                    else:
                        findings.append(_finding(region_id, time_column, 'positive', 'unique_timestamps',
                                                 'Alla giltiga tidpunkter är unika i regionen.',
                                                 {'distinct_timestamps': len(valid)}))
                if len(valid) > 1 and invalid == 0:
                    try:
                        deltas = [(b-a).total_seconds() for a,b in zip(stamps, stamps[1:])]
                    except TypeError:
                        findings.append(_finding(region_id, time_column, 'insufficient', 'incomparable_timezones',
                                                 'Olika tidszonssemantik hindrar intervalljämförelse.', {}))
                    else:
                        reversed_count = sum(d < 0 for d in deltas)
                        if reversed_count:
                            findings.append(_finding(region_id, time_column, 'attention', 'out_of_order',
                                                     'Tidpunkterna är inte ordnade stigande i källordningen.',
                                                     {'negative_adjacent_intervals': reversed_count}))
                        positive = [d for d in deltas if d > 0 and isfinite(d)]
                        if len(positive) >= 2:
                            modes = Counter(positive)
                            interval, count = sorted(modes.items(), key=lambda kv: (-kv[1], kv[0]))[0]
                            if count == len(positive):
                                findings.append(_finding(region_id, time_column, 'positive', 'stable_observed_cadence',
                                                         'Alla positiva intilliggande mätintervall har samma längd.',
                                                         {'seconds': interval, 'positive_intervals': len(positive)}))
                            else:
                                findings.append(_finding(region_id, time_column, 'attention', 'variable_observed_cadence',
                                                         'Mätintervallen varierar inom regionen.',
                                                         {'dominant_seconds': interval, 'dominant_count': count,
                                                          'positive_intervals': len(positive)}))
                        else:
                            findings.append(_finding(region_id, time_column, 'insufficient', 'too_few_positive_intervals',
                                                     'För få positiva intervall för att bedöma mätfrekvens.',
                                                     {'positive_intervals': len(positive)}))
        result_regions.append({'region': region, 'row_count': len(selected), 'findings': findings})
        all_findings.extend(findings)
    return {
        'analysis_kind': 'data_quality_evidence', 'version': VERSION,
        'status': 'measured' if rows else 'insufficient_data',
        'regions': result_regions, 'findings': all_findings,
        'limitations': [
            'Findings apply only to the specified regions and tested properties.',
            'Positive evidence is not proof of correctness, validity, or normal business behavior.',
            'No cleaning, imputation, resampling, sorting, or aggregation is performed.',
            'No automatic region discovery; caller must provide meaningful partitioning.',
            f'Bounded in-memory evaluation (max {MAX_ROWS} rows), not the scalable source executor.',
        ],
    }
