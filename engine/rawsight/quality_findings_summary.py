"""Read-only, streaming presentation summary of Quality Region Execution v0.2 JSONL.

Every record is counted; *display examples* are bounded, never analysis inputs.
No claims of statistical significance, correctness or business normality are made.
"""
from __future__ import annotations

from collections import Counter
import heapq
import json
from pathlib import Path
from typing import Any

VERSION = 'quality-findings-summary-v0.1'
POLARITIES = ('positive', 'attention', 'insufficient')


def _jsonl(path: Path):
    with path.open('r', encoding='utf-8') as f:
        for line_number, line in enumerate(f, 1):
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'Invalid JSONL at {path}:{line_number}') from exc
                if not isinstance(record, dict):
                    raise ValueError(f'Non-object JSONL at {path}:{line_number}')
                yield line_number, record


def _require_nonnegative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _priority(finding: dict, region: dict) -> tuple[float, str]:
    """Heuristic display priority; it is NOT business or statistical significance."""
    evidence = finding.get('evidence') or {}
    kind = finding['kind']
    size = region['stop'] - region['start']
    if kind == 'missing_values':
        score = float(evidence.get('missing', 0)) / max(1, size)
    elif kind == 'time_structure':
        score = (float(evidence.get('invalid_timestamps', 0))
                 + float(evidence.get('adjacent_equal_timestamps', 0))
                 + float(evidence.get('adjacent_reversals', 0))) / max(1, size)
        if finding['polarity'] == 'attention' and score == 0:
            # Cadence variation is a structural observation, not a defect.
            score = 0.01
        if finding['polarity'] == 'positive':
            score = min(size, 1000000) / 1000000
    elif kind == 'complete_column':
        score = min(size, 1000000) / 1000000
    else:
        score = 0.0
    return (score, kind)


def _display_text(finding: dict, region: dict) -> tuple[str, str]:
    col = str(finding.get('column', '?'))
    ev = finding.get('evidence') or {}
    n = region['stop'] - region['start']
    kind = finding['kind']
    if kind == 'complete_column':
        return (f'Inga saknade värden i {col} inom denna region',
                f'Alla {n} undersökta rader har ett registrerat värde i fältet. Det bevisar inte att värdena är korrekta.')
    if kind == 'missing_values':
        return (f'Saknade värden i {col}',
                f'{ev.get("missing", "?")} av {n} rader saknar värde i fältet. Granska fördelning och sammanhang innan tolkning.')
    if kind == 'time_structure':
        if finding['polarity'] == 'positive':
            return ('Regelbundna tidsövergångar i den undersökta regionen',
                    'De kontrollerade positiva intervallen är lika och inga lokala tidskonflikter upptäcktes. Källordningen är inte certifierad.')
        if finding['polarity'] == 'insufficient':
            return ('För få jämförbara tidsintervall',
                    'Underlaget räcker inte för att bedöma regelbundenheten i den undersökta regionen.')
        detail = []
        for key, label in [('invalid_timestamps', 'ogiltiga tider'), ('adjacent_equal_timestamps', 'upprepade intilliggande tider'),
                           ('adjacent_reversals', 'bakåtgående tidsövergångar')]:
            if ev.get(key):
                detail.append(f'{ev[key]} {label}')
        if ev.get('positive_intervals_all_equal') is False:
            detail.append('varierande mätintervall')
        return ('Tidsstrukturen förtjänar en närmare undersökning',
                ', '.join(detail) + '. Detta behöver inte vara ett datakvalitetsfel.' if detail else 'Tidsstrukturen avviker enligt de tillgängliga kontrollerna.')
    return (f'Observation: {kind} i {col}', 'Teknisk kvalitetsevidens; betydelsen är ännu inte fastställd.')


def summarize_quality_findings(*, evidence_path: str, boundaries_path: str | None = None,
                               source_rows: int | None = None, expected_regions: int | None = None,
                               expected_findings: int | None = None,
                               source_order_certified: bool = False,
                               examples_per_polarity: int = 5) -> dict:
    """Stream an entire v0.2 evidence file and produce a small presentation summary.

    Requires v0.2 ordering: a region record followed by its findings. Validates
    complete, contiguous half-open region coverage; validates optional counters.
    Returns line references into source JSONL (no copied/removed evidence).
    """
    if type(source_order_certified) is not bool:
        raise ValueError('source_order_certified must be boolean')
    if type(examples_per_polarity) is not int or examples_per_polarity < 1:
        raise ValueError('examples_per_polarity must be positive')
    for name, value in [('source_rows', source_rows), ('expected_regions', expected_regions),
                        ('expected_findings', expected_findings)]:
        if value is not None:
            _require_nonnegative_int(value, name)
    path = Path(evidence_path).resolve()
    boundary_path = Path(boundaries_path).resolve() if boundaries_path is not None else None
    counts = Counter()
    kinds = Counter()
    region_count = finding_count = boundaries = 0
    covered = 0
    current = None
    current_findings = 0
    # Only presentation examples held in memory, irrespective of source size.
    top = {p: [] for p in POLARITIES}
    next_id = 0
    for line_no, rec in _jsonl(path):
        rt = rec.get('record_type')
        if rt == 'region':
            if current is not None and current_findings == 0:
                raise ValueError(f'Region {current["id"]} has no findings')
            a, b = rec.get('start'), rec.get('stop')
            if type(a) is not int or type(b) is not int or a != covered or b <= a:
                raise ValueError(f'Noncontiguous or empty region at {path}:{line_no}')
            if not isinstance(rec.get('id'), str) or not rec['id']:
                raise ValueError(f'Missing region id at {path}:{line_no}')
            current = {'id': rec['id'], 'start': a, 'stop': b,
                       'discovery_role': rec.get('discovery_role'), 'line': line_no}
            current_findings = 0
            region_count += 1
            covered = b
        elif rt == 'finding':
            if current is None or rec.get('region_id') != current['id']:
                raise ValueError(f'Finding has no matching preceding region at {path}:{line_no}')
            pol = rec.get('polarity')
            if pol not in POLARITIES:
                raise ValueError(f'Unknown finding polarity at {path}:{line_no}')
            if not isinstance(rec.get('kind'), str):
                raise ValueError(f'Missing finding kind at {path}:{line_no}')
            counts[pol] += 1
            kinds[(pol, rec['kind'])] += 1
            finding_count += 1
            current_findings += 1
            title, explanation = _display_text(rec, current)
            score, kind = _priority(rec, current)
            item = {'title': title, 'explanation': explanation, 'polarity': pol,
                    'kind': kind, 'column': rec.get('column'), 'region_id': current['id'],
                    'region': {'start': current['start'], 'stop': current['stop'],
                               'discovery_role': current['discovery_role']},
                    'evidence_ref': {'path': str(path), 'line': line_no, 'region_line': current['line']},
                    'priority_score': round(score, 6)}
            next_id += 1
            heap = top[pol]
            key = (score, next_id)
            if len(heap) < examples_per_polarity:
                heapq.heappush(heap, (key, item))
            elif key > heap[0][0]:
                heapq.heapreplace(heap, (key, item))
        else:
            raise ValueError(f'Unexpected record_type at {path}:{line_no}')
    if current is not None and current_findings == 0:
        raise ValueError('Final region has no findings')
    if source_rows is not None and covered != source_rows:
        raise ValueError(f'Coverage mismatch: {covered} vs {source_rows}')
    if expected_regions is not None and region_count != expected_regions:
        raise ValueError(f'Region count mismatch: {region_count} vs {expected_regions}')
    if expected_findings is not None and finding_count != expected_findings:
        raise ValueError(f'Finding count mismatch: {finding_count} vs {expected_findings}')
    if boundary_path is not None:
        for line_no, b in _jsonl(boundary_path):
            p = b.get('after_row')
            if type(p) is not int or not 0 < p < covered:
                raise ValueError(f'Invalid boundary at {boundary_path}:{line_no}')
            boundaries += 1
    return {
        'analysis_kind': 'quality_findings_summary', 'version': VERSION,
        'status': 'complete',
        'coverage': {'rows_in_regions': covered, 'region_count': region_count,
                     'finding_count': finding_count, 'boundary_event_count': boundaries if boundary_path else None,
                     'exhaustive_evidence_read': True, 'source_order_certified': source_order_certified},
        'finding_counts': dict(counts),
        'finding_types': [{'polarity': pol, 'kind': kind, 'count': n}
                          for (pol, kind), n in sorted(kinds.items())],
        'examples': {p: [item for _, item in sorted(top[p], key=lambda x: x[0], reverse=True)]
                     for p in POLARITIES},
        'source_evidence': {'evidence_jsonl': str(path),
                            'boundaries_jsonl': str(boundary_path) if boundary_path else None},
        'interpretation': {'priority_meaning': 'Heuristic display ordering only; not statistical significance or business impact.',
                           'positive_meaning': 'Passed specific checks only; not certified truth or business normality.',
                           'scope': 'Region findings reflect the v0.2 checks: missing values and adjacent time structure.',
                           'caveat': 'Source scan order is not certified unless a caller supplies a separately verified certification.'},
    }


def summarize_quality_run(result: dict, *, examples_per_polarity: int = 5) -> dict:
    """Use exact paths, counts and provenance from the v0.2 execution result."""
    if result.get('analysis_kind') != 'quality_region_execution' or result.get('status') != 'complete':
        raise ValueError('Expected completed quality_region_execution result')
    cov = result['region_coverage']
    if cov.get('exhaustive') is not True or cov.get('rows_evaluated') != cov.get('source_rows'):
        raise ValueError('Cannot summarize incomplete coverage as complete')
    return summarize_quality_findings(
        evidence_path=result['region_quality']['evidence_jsonl'],
        boundaries_path=result['discovery']['boundaries_jsonl'],
        source_rows=cov['source_rows'],
        expected_regions=result['discovery']['regions'],
        expected_findings=result['region_quality']['findings'],
        source_order_certified=cov.get('source_order_certified', False),
        examples_per_polarity=examples_per_polarity)
