"""Full-source disk-backed quality region discovery.

Source ordering is a stable scan-order snapshot, NOT a certified original CSV row order.
Every structural boundary and every region is written to a durable JSONL manifest.
No fixed source-size, column-count, or region-count cap. Input rows remain untouched.
"""
from __future__ import annotations

from collections import Counter
import json
from math import isfinite
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Iterator

from rawsight.quality_region_execution import _calculate_full_counts, _identifier
from rawsight.quality_region_discovery import _time
from rawsight.source_context import SourceExecutionContext

VERSION = 'quality-region-execution-v0.3'


def _validate(names: list[str], time_column: str | None, columns: list[str] | None,
              batch_size: int, gap_multiplier: float, min_region_rows: int) -> list[str]:
    if len(names) != len(set(names)):
        raise ValueError('Duplicate source column names are unsupported')
    if time_column is not None and time_column not in names:
        raise ValueError('Unknown time_column')
    chosen = list(names) if columns is None else list(columns)
    if not chosen or len(chosen) != len(set(chosen)) or not set(chosen).issubset(names):
        raise ValueError('Unknown, empty or duplicate selected columns')
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError('batch_size must be a positive integer; it is not a dataset cap')
    if isinstance(gap_multiplier, bool) or not isinstance(gap_multiplier, (int, float)) or not isfinite(gap_multiplier) or gap_multiplier <= 1:
        raise ValueError('gap_multiplier must be finite and > 1')
    if type(min_region_rows) is not int or min_region_rows < 1:
        raise ValueError('min_region_rows must be >= 1')
    return chosen


def _scan(conn, table: str, projection: list[str], batch_size: int) -> Iterator[dict[str, Any]]:
    sql = ('SELECT ' + ', '.join(_identifier(c) for c in projection) +
           ' FROM ' + _identifier(table) + ' ORDER BY __rs_quality_ordinal')
    cursor = conn.execute(sql)
    while True:
        block = cursor.fetchmany(batch_size)
        if not block:
            break
        for row in block:
            yield dict(zip(projection, row))


def _delta(a: Any, b: Any) -> float | None:
    left, right = _time(a), _time(b)
    if left is None or right is None:
        return None
    try:
        seconds = (right - left).total_seconds()
    except TypeError:
        return None
    return seconds if isfinite(seconds) else None


def _boundary_reasons(a: dict, b: dict, *, time_column: str | None,
                      columns: list[str], baseline: float | None, gap_multiplier: float) -> list[str]:
    reasons = []
    if time_column is not None:
        d = _delta(a.get(time_column), b.get(time_column))
        if d is None:
            reasons.append('invalid_or_incomparable_timestamp_transition')
        elif d == 0:
            reasons.append('repeated_timestamp')
        elif d < 0:
            reasons.append('reversed_time')
        elif baseline is not None and d > baseline * gap_multiplier:
            reasons.append('large_observed_gap')
    if any((a.get(c) is None or a.get(c) == '') != (b.get(c) is None or b.get(c) == '') for c in columns):
        reasons.append('missingness_pattern_change')
    return reasons


def _median_cadence(conn, table: str, time_column: str | None) -> float | None:
    if time_column is None:
        return None
    # Median of positive adjacent intervals, like v0.1. All rows included.
    q = _identifier(time_column)
    sql = f'''WITH stamps AS (
      SELECT __rs_quality_ordinal, TRY_CAST({q} AS TIMESTAMP) AS t
      FROM {_identifier(table)}
    ), delta AS (
      SELECT date_diff('microsecond', lag(t) OVER (ORDER BY __rs_quality_ordinal), t) / 1000000.0 AS seconds
      FROM stamps
    ) SELECT median(seconds) FROM delta WHERE seconds > 0'''
    value = conn.execute(sql).fetchone()[0]
    return float(value) if value is not None else None


def _boundaries(rows: Iterable[dict], *, time_column: str | None, columns: list[str],
                baseline: float | None, gap_multiplier: float) -> Iterator[dict]:
    previous = None
    for index, row in enumerate(rows):
        if previous is not None:
            reasons = _boundary_reasons(previous, row, time_column=time_column,
                                        columns=columns, baseline=baseline, gap_multiplier=gap_multiplier)
            if reasons:
                yield {'before_row': index-1, 'after_row': index, 'reasons': reasons}
        previous = row


def _spans(boundary_path: Path, n: int, min_region_rows: int) -> Iterator[tuple[int, int, str]]:
    """Produce a full non-overlapping partition without holding boundaries in memory."""
    cursor = 0
    group_start = group_last = None
    with boundary_path.open(encoding='utf-8') as stream:
        for line in stream:
            p = json.loads(line)['after_row']
            if group_start is None:
                group_start = group_last = p
            elif p - group_last <= min_region_rows:
                group_last = p
            else:
                start = max(cursor, group_start - 1)
                end = min(n, group_last + 1)
                if start > cursor:
                    yield cursor, start, 'between_transitions'
                if end > start:
                    yield start, end, 'transition_neighborhood'
                cursor = end
                group_start = group_last = p
    if group_start is not None:
        start = max(cursor, group_start - 1)
        end = min(n, group_last + 1)
        if start > cursor:
            yield cursor, start, 'between_transitions'
        if end > start:
            yield start, end, 'transition_neighborhood'
        cursor = end
    if cursor < n:
        yield cursor, n, 'between_transitions'
    if n == 0:
        return


def _region_findings_v3(rows: Iterable[dict], start: int, stop: int, *,
                        columns: list[str], time_column: str | None, region_id: str,
                        baseline_seconds: float | None = None) -> Iterator[dict]:
    # All values are measured from the same stable scan-order snapshot as v0.2.
    # Streaming Welford variance: constant memory regardless of interval diversity.
    missing = Counter()
    valid = adjacent_repeats = reversals = valid_intervals = 0
    invalid_or_incomparable_adjacent_pairs = 0
    first_interval = minimum = maximum = None
    mean = m2 = 0.0
    exact_baseline_matches = 0
    all_equal = True
    prev = None
    have_prev = False
    for row in rows:
        for c in columns:
            if row.get(c) is None or row.get(c) == '':
                missing[c] += 1
        if time_column is None:
            continue
        current = _time(row.get(time_column))
        if current is not None:
            valid += 1
        if have_prev:
            d = _delta(prev, current) if prev is not None and current is not None else None
            if d is None:
                invalid_or_incomparable_adjacent_pairs += 1
            elif d == 0:
                adjacent_repeats += 1
            elif d < 0:
                reversals += 1
            else:
                valid_intervals += 1
                if first_interval is None:
                    first_interval = minimum = maximum = d
                else:
                    minimum = min(minimum, d)
                    maximum = max(maximum, d)
                    if d != first_interval:
                        all_equal = False
                # Online mean and population variance. No stored samples / histogram.
                delta = d - mean
                mean += delta / valid_intervals
                m2 += delta * (d - mean)
                if baseline_seconds is not None and d == baseline_seconds:
                    exact_baseline_matches += 1
        prev = current
        have_prev = True
    for c in columns:
        m = missing[c]
        yield {'record_type': 'finding', 'region_id': region_id, 'column': c,
               'kind': 'complete_column' if m == 0 else 'missing_values',
               'polarity': 'positive' if m == 0 else 'attention',
               'evidence': {'rows': stop-start, 'missing': m},
               'interpretation_status': 'observed'}
    if time_column is not None:
        structural_issue = adjacent_repeats > 0 or reversals > 0 or valid != stop-start or invalid_or_incomparable_adjacent_pairs > 0
        # Variability alone is an observation, not a defect and not proof of stability.
        if structural_issue:
            polarity = 'attention'
        elif valid_intervals < 2:
            polarity = 'insufficient'
        elif all_equal:
            polarity = 'positive'
        else:
            polarity = 'informational'
        distribution = {'count': valid_intervals,
                        'min_seconds': minimum, 'max_seconds': maximum,
                        'mean_seconds': mean if valid_intervals else None,
                        'population_stddev_seconds': (m2 / valid_intervals) ** 0.5 if valid_intervals else None,
                        'whole_source_median_baseline_seconds': baseline_seconds,
                        'exact_baseline_matches': exact_baseline_matches if baseline_seconds is not None else None}
        yield {'record_type': 'finding', 'region_id': region_id, 'column': time_column,
               'kind': 'time_structure', 'polarity': polarity,
               'evidence': {'valid_timestamps': valid, 'invalid_timestamps': stop-start-valid,
                            'adjacent_equal_timestamps': adjacent_repeats,
                            'adjacent_reversals': reversals,
                            'invalid_or_incomparable_adjacent_pairs': invalid_or_incomparable_adjacent_pairs,
                            'positive_intervals': valid_intervals,
                            'positive_intervals_all_equal': all_equal if valid_intervals >= 2 else None,
                            'positive_interval_distribution': distribution,
                            'cadence_observation': ('insufficient_intervals' if valid_intervals < 2 else
                                                    'all_positive_intervals_equal' if all_equal else
                                                    'positive_intervals_vary')},
               'interpretation_status': 'observed',
               'limitations': ['Interval statistics describe the snapshotted scan sequence, not certified original source order.',
                               'Whole-source baseline is the median of positive adjacent intervals and not a declared expected cadence.',
                               'Non-adjacent repeats are not measured per area; global distinct timestamp count is exact.',
                               'Variability alone does not establish a quality defect, cause, or analysis suitability.']}


def execute_quality_regions_v3(*, file_path: str, time_column: str | None = None,
                               columns: list[str] | None = None, result_dir: str = 'local_profiles/quality_runs',
                               batch_size: int = 4096, gap_multiplier: float = 5.0,
                               min_region_rows: int = 3,
                               source_context: SourceExecutionContext | None = None) -> dict:
    """Exhaustive snapshot scan with disk-backed event output; no partial success.

    A memory/disk/compute failure raises; never silently reports complete.
    Reading source order remains provisional until source parser certifies it.
    """
    def run(context: SourceExecutionContext) -> dict:
        if not context.is_open:
            raise RuntimeError('SourceExecutionContext must be open')
        chosen = _validate(context.column_names, time_column, columns, batch_size,
                           gap_multiplier, min_region_rows)
        conn = context.require_connection()
        output = Path(result_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        projection = list(chosen)
        if time_column is not None and time_column not in projection:
            projection.append(time_column)
        # A materialized scan-order snapshot ensures chunk boundaries and passes
        # use the same row sequence. DuckDB can spill intermediate data to disk.
        table = '_rs_quality_scan_v03'
        quoted = _identifier(table)
        if '__rs_quality_ordinal' in context.column_names:
            raise ValueError('Reserved source column name __rs_quality_ordinal')
        conn.execute(f'DROP TABLE IF EXISTS {quoted}')
        tmp_paths = []
        try:
            projected = ', '.join(_identifier(c) for c in projection)
            conn.execute(f'''CREATE TEMP TABLE {quoted} AS
                SELECT row_number() OVER () - 1 AS __rs_quality_ordinal, {projected}
                FROM {_identifier(context.view_name)}''')
            # Source-wide aggregate is exact and independent from regional inference.
            # Count exactly the rows of the materialized scan-order snapshot.
            class _SnapshotContext:
                view_name = table
                def require_connection(self):
                    return conn
            all_counts = _calculate_full_counts(_SnapshotContext(), chosen, time_column)
            n = all_counts['row_count']
            baseline = _median_cadence(conn, table, time_column)
            fd, bp = tempfile.mkstemp(prefix='_quality_boundaries_', suffix='.jsonl', dir=str(output))
            os.close(fd)
            boundary_path = Path(bp)
            tmp_paths.append(boundary_path)
            transition_count = 0
            with boundary_path.open('w', encoding='utf-8') as out:
                for boundary in _boundaries(_scan(conn, table, projection, batch_size),
                                            time_column=time_column, columns=[c for c in chosen if c != time_column],
                                            baseline=baseline, gap_multiplier=gap_multiplier):
                    out.write(json.dumps(boundary, ensure_ascii=False) + '\n')
                    transition_count += 1
            fd, ep = tempfile.mkstemp(prefix='_quality_evidence_', suffix='.jsonl', dir=str(output))
            os.close(fd)
            evidence_path = Path(ep)
            tmp_paths.append(evidence_path)
            # Stream rows and consume exactly the required counts per region.
            source_rows = iter(_scan(conn, table, projection, batch_size))
            region_count = 0
            finding_count = 0
            consumed = 0
            with evidence_path.open('w', encoding='utf-8') as out:
                for start, stop, role in _spans(boundary_path, n, min_region_rows):
                    if start != consumed or stop <= start:
                        raise RuntimeError('Invalid region partition')
                    region_count += 1
                    region_id = f'region_{region_count:09d}'
                    region = {'record_type': 'region', 'id': region_id, 'kind': 'row_range',
                              'start': start, 'stop': stop, 'discovery_role': role}
                    out.write(json.dumps(region, ensure_ascii=False) + '\n')
                    batch = (next(source_rows) for _ in range(stop-start))
                    for finding in _region_findings_v3(batch, start, stop, columns=chosen,
                                                       time_column=time_column, region_id=region_id,
                                                       baseline_seconds=baseline):
                        out.write(json.dumps(finding, ensure_ascii=False) + '\n')
                        finding_count += 1
                    consumed = stop
                if consumed != n or next(source_rows, None) is not None:
                    raise RuntimeError('Not all source rows were assessed')
            # Retain every boundary in a separate durable source, no preview caps.
            final_evidence = output / (evidence_path.stem.replace('_quality_evidence_', 'quality_evidence_') + '.jsonl')
            final_boundaries = output / (boundary_path.stem.replace('_quality_boundaries_', 'quality_boundaries_') + '.jsonl')
            evidence_path.replace(final_evidence)
            boundary_path.replace(final_boundaries)
            tmp_paths.clear()
            return {'analysis_kind': 'quality_region_execution', 'version': VERSION,
                    'status': 'complete' if n else 'insufficient_data', 'source': {'file_path': context.file_path, 'row_count': n},
                    'whole_source_quality': all_counts,
                    'region_coverage': {'kind': 'entire_source', 'rows_evaluated': consumed,
                                        'source_rows': n, 'exhaustive': True,
                                        'source_order_certified': False},
                    'discovery': {'status': 'partitioned' if transition_count else 'whole_only',
                                  'total_boundaries': transition_count,
                                  'regions': region_count, 'baseline_seconds': baseline,
                                  'boundaries_jsonl': str(final_boundaries)},
                    'region_quality': {'status': 'measured', 'findings': finding_count,
                                       'evidence_jsonl': str(final_evidence)},
                    'limitations': ['Source scan order is snapshotted but not certified original file row order.',
                                    'Positive findings concern tested properties, not truth or business normality.',
                                    'Region timestamp counts check adjacent transitions only; full-source distinct count is exact.',
                                    'Source rows are not cleaned, dropped, imputed or aggregated.']}
        finally:
            conn.execute(f'DROP TABLE IF EXISTS {quoted}')
            for temp in tmp_paths:
                temp.unlink(missing_ok=True)

    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as context:
        return run(context)
