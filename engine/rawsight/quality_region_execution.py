"""RAWSIGHT Quality Region Execution v0.1.

Exact source-wide quality counts in DuckDB; bounded, explicitly scoped
region discovery through the existing in-memory engines. Source never edited.
A bounded preview is NOT an exhaustive region map of a larger source.
"""
from __future__ import annotations

from typing import Any

from rawsight.quality_evidence import assess_quality
from rawsight.quality_region_discovery import discover_quality_regions
from rawsight.source_context import SourceExecutionContext

VERSION = 'quality-region-execution-v0.1'
MAX_PREVIEW_ROWS = 100_000
MAX_COLUMNS = 24


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _check_inputs(names: list[str], *, time_column: str | None,
                  columns: list[str] | None, max_rows: int) -> list[str]:
    if type(max_rows) is not int or not 1 <= max_rows <= MAX_PREVIEW_ROWS:
        raise ValueError(f'max_rows must be an integer from 1 to {MAX_PREVIEW_ROWS}')
    if len(names) != len(set(names)):
        raise ValueError('Duplicate source column names are unsupported')
    if time_column is not None and time_column not in names:
        raise ValueError('time_column must be an existing source column')
    if columns is None:
        selected = list(names)
    elif isinstance(columns, list) and all(isinstance(c, str) for c in columns):
        selected = list(columns)
    else:
        raise ValueError('columns must be an explicit list of source column names')
    if not selected or len(selected) > MAX_COLUMNS or len(selected) != len(set(selected)):
        raise ValueError(f'Select between 1 and {MAX_COLUMNS} unique columns')
    if not set(selected).issubset(names):
        raise ValueError('Unknown selected column')
    return selected


def _calculate_full_counts(context: SourceExecutionContext, columns: list[str],
                           time_column: str | None) -> dict[str, Any]:
    """Database aggregates cover every source row; no Python row materialization."""
    view = _identifier(context.view_name)
    expressions = ['COUNT(*) AS row_count']
    for index, name in enumerate(columns):
        q = _identifier(name)
        expressions.append(
            f"COUNT(*) FILTER (WHERE {q} IS NULL OR CAST({q} AS VARCHAR) = '') AS missing_{index}"
        )
    if time_column is not None:
        q = _identifier(time_column)
        t = f'TRY_CAST({q} AS TIMESTAMP)'
        expressions.extend([
            f'COUNT({t}) AS valid_timestamps',
            f'COUNT(DISTINCT {t}) AS distinct_timestamps',
        ])
    sql = 'SELECT ' + ', '.join(expressions) + ' FROM ' + view
    cur = context.require_connection().execute(sql)
    values = dict(zip([d[0] for d in cur.description], cur.fetchone()))
    count = int(values['row_count'])
    findings = []
    for i, column in enumerate(columns):
        missing = int(values[f'missing_{i}'])
        findings.append({
            'region_id': 'dataset', 'column': column,
            'polarity': 'positive' if missing == 0 else 'attention',
            'kind': 'complete_column' if missing == 0 else 'missing_values',
            'evidence': {'rows': count, 'missing': missing},
            'scope': 'entire_source', 'interpretation_status': 'observed',
        })
    temporal = None
    if time_column is not None:
        valid = int(values['valid_timestamps'])
        distinct = int(values['distinct_timestamps'])
        extra = valid - distinct
        temporal = {'valid_timestamps': valid, 'invalid_or_missing_timestamps': count - valid,
                    'distinct_timestamps': distinct,
                    'extra_rows_beyond_unique_timestamps': extra}
        findings.append({
            'region_id': 'dataset', 'column': time_column,
            'polarity': 'attention' if extra else ('positive' if valid else 'insufficient'),
            'kind': 'repeated_timestamps' if extra else ('unique_timestamps' if valid else 'no_valid_timestamps'),
            'evidence': {'extra_rows_beyond_unique_timestamps': extra,
                         'distinct_timestamps': distinct},
            'scope': 'entire_source', 'interpretation_status': 'observed',
        })
        if count != valid:
            findings.append({
                'region_id': 'dataset', 'column': time_column, 'polarity': 'attention',
                'kind': 'invalid_timestamps',
                'evidence': {'invalid_or_missing': count - valid},
                'scope': 'entire_source', 'interpretation_status': 'observed',
            })
    return {'row_count': count, 'columns': columns,
            'missing_by_column': {col: int(values[f'missing_{i}']) for i, col in enumerate(columns)},
            'temporal': temporal, 'findings': findings,
            'coverage': {'kind': 'entire_source', 'rows_evaluated': count, 'exact': True}}


def execute_quality_regions(*, file_path: str,
                            time_column: str | None = None,
                            columns: list[str] | None = None,
                            max_rows: int = 60_000,
                            max_regions: int = 40,
                            gap_multiplier: float = 5.0,
                            source_context: SourceExecutionContext | None = None) -> dict[str, Any]:
    """Full-source exact column/time counts + bounded structural region assessment.

    For a source larger than max_rows, the region results describe ONLY the
    first max_rows records returned by the source view. They are not a random
    representative sample and cannot be extrapolated to the remaining rows.
    The returned view order is not certified original file row order.
    """
    def run(context: SourceExecutionContext) -> dict[str, Any]:
        if not context.is_open:
            raise RuntimeError('SourceExecutionContext must be open')
        chosen = _check_inputs(context.column_names, time_column=time_column,
                               columns=columns, max_rows=max_rows)
        if type(max_regions) is not int or not 1 <= max_regions <= 100:
            raise ValueError('max_regions must be between 1 and 100')
        all_counts = _calculate_full_counts(context, chosen, time_column)
        n = all_counts['row_count']
        projection = list(chosen)
        if time_column is not None and time_column not in projection:
            projection.append(time_column)
        sql = ('SELECT ' + ', '.join(_identifier(c) for c in projection) +
               f' FROM {_identifier(context.view_name)} LIMIT ?')
        cur = context.require_connection().execute(sql, [max_rows])
        records = cur.fetchall()
        rows = [dict(zip(projection, record)) for record in records]
        discovery = discover_quality_regions(
            rows, time_column=time_column,
            value_columns=[col for col in chosen if col != time_column],
            max_regions=max_regions, gap_multiplier=gap_multiplier,
        )
        # Explicitly preserve source-wide findings separately, never confuse
        # the preview's 'dataset' region with the entire source.
        assessment = assess_quality(rows, regions=discovery['regions'],
                                    time_column=time_column, columns=chosen)
        complete = len(rows) == n
        limitations = [
            'Positive findings only establish the properties actually checked.',
            'Source view retrieval order is not guaranteed to be canonical original-row order.',
            'No rows cleaned, sorted, collapsed, imputed or changed.',
            'A structural transition may be an important finding rather than erroneous data.',
        ]
        if not complete:
            limitations.append(
                f'Region detection covers only the first {len(rows)} rows returned by the source view '
                f'of {n} total. Regional findings are non-exhaustive and not representative.'
            )
        return {
            'analysis_kind': 'quality_region_execution', 'version': VERSION,
            'status': 'complete' if complete else 'partial_region_coverage',
            'source': {'file_path': context.file_path, 'row_count': n},
            'whole_source_quality': all_counts,
            'region_coverage': {'kind': 'entire_source' if complete else 'bounded_source_prefix',
                                'rows_evaluated': len(rows), 'source_rows': n,
                                'exhaustive': complete, 'source_order_certified': False},
            'discovery': discovery,
            'region_quality': assessment,
            'limitations': limitations + list(discovery.get('limitations', [])),
        }

    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as context:
        return run(context)
