"""Evidence-grounded, streaming overview of v0.2 quality area manifests.

Never infer business normality, root cause or statistical significance.
Keep all original findings and boundaries on disk; return concise grouped facts.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import json
from typing import Any

VERSION = "quality-findings-summary-v0.2"
ROLES = {"between_transitions", "transition_neighborhood"}
POLARITIES = {"positive", "attention", "insufficient"}


def _records(path: str, kind: str):
    target = Path(path).resolve(strict=True)
    with target.open("r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            if not raw.strip():
                raise ValueError(f"Blank {kind} line {number}")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid {kind} JSON line {number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Non-object {kind} line {number}")
            yield number, value


def _int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid nonnegative integer: {label}")
    return value


def _ref(path: str, line: int, region_line: int | None = None) -> dict:
    ref = {"path": str(Path(path).resolve()), "line": line}
    if region_line is not None:
        ref["region_line"] = region_line
    return ref


def _insert_biggest(items: list[dict], candidate: dict, size: int) -> None:
    """Small presentation-only reservoir; all rows are still checked and counted."""
    if size == 0:
        return
    items.append(candidate)
    items.sort(key=lambda x: (-x["rows"], x["start"], x["area_id"]))
    del items[size:]


def summarize_quality_areas_v2(*, evidence_path: str, boundaries_path: str,
                               source_rows: int, expected_areas: int | None = None,
                               expected_findings: int | None = None,
                               examples_per_group: int = 3,
                               source_order_certified: bool = False) -> dict:
    """Summarize full v0.2 JSONL manifests, requiring a contiguous exhaustive partition.

    Examples are *largest by row count*, not 'most significant'. No cap on input.
    Does not perform fresh data analysis. Source order caveat propagates unchanged.
    """
    n = _int(source_rows, "source_rows")
    if type(examples_per_group) is not int or examples_per_group < 0:
        raise ValueError("examples_per_group must be >= 0")
    for label, count in (("expected_areas", expected_areas), ("expected_findings", expected_findings)):
        if count is not None:
            _int(count, label)
    if type(source_order_certified) is not bool:
        raise ValueError("source_order_certified must be bool")

    by_role = defaultdict(lambda: {"areas": 0, "rows": 0, "findings": Counter(), "polarity": Counter()})
    by_type = Counter()
    by_polarity = Counter()
    by_column = defaultdict(lambda: {"assessed_areas": 0, "rows_assessed": 0, "missing_cells": 0, "areas_with_missing": 0})
    time_details = Counter()
    samples = defaultdict(list)
    cursor = 0
    count_areas = count_findings = 0
    current = None
    current_findings = Counter()
    current_columns = []

    def finalize():
        if current is None:
            return
        role = current["role"]
        # Store only a few display examples; do not claim that size implies importance.
        candidate = {**current, "finding_polarities": dict(current_findings),
                     "checked_columns": len(current_columns)}
        if role == "transition_neighborhood":
            group = "transition_examples"
        elif current_findings["attention"]:
            group = "attention_examples"
        elif current_findings["insufficient"]:
            group = "insufficient_examples"
        else:
            group = "continuity_examples"
        _insert_biggest(samples[group], candidate, examples_per_group)

    for line, record in _records(evidence_path, "evidence"):
        t = record.get("record_type")
        if t == "region":
            finalize()
            area_id = record.get("id")
            start, stop = record.get("start"), record.get("stop")
            role = record.get("discovery_role")
            if not isinstance(area_id, str) or not area_id or role not in ROLES or type(start) is not int or type(stop) is not int:
                raise ValueError(f"Invalid area at evidence line {line}")
            if start != cursor or stop <= start or stop > n:
                raise ValueError(f"Noncontiguous/invalid area at evidence line {line}")
            cursor = stop
            count_areas += 1
            rows = stop-start
            by_role[role]["areas"] += 1
            by_role[role]["rows"] += rows
            current = {"area_id": area_id, "role": role, "start": start, "stop": stop,
                       "rows": rows, "area_ref": _ref(evidence_path, line)}
            current_findings = Counter()
            current_columns = []
        elif t == "finding":
            if current is None or record.get("region_id") != current["area_id"]:
                raise ValueError(f"Unlinked finding at evidence line {line}")
            polarity, kind = record.get("polarity"), record.get("kind")
            if polarity not in POLARITIES or not isinstance(kind, str) or not kind:
                raise ValueError(f"Invalid finding at line {line}")
            e = record.get("evidence")
            if not isinstance(e, dict):
                raise ValueError(f"Missing evidence at line {line}")
            if record.get("interpretation_status") != "observed":
                raise ValueError(f"Unsupported interpretation at line {line}")
            count_findings += 1
            current_findings[polarity] += 1
            by_role[current["role"]]["findings"][kind] += 1
            by_role[current["role"]]["polarity"][polarity] += 1
            by_type[(polarity, kind)] += 1
            by_polarity[polarity] += 1
            if kind in ("complete_column", "missing_values"):
                column = record.get("column")
                if not isinstance(column, str) or not column:
                    raise ValueError(f"Missing column at evidence line {line}")
                if column in current_columns:
                    raise ValueError(f"Duplicate column assessment at line {line}")
                current_columns.append(column)
                if _int(e.get("rows"), "evidence.rows") != current["rows"]:
                    raise ValueError(f"Column observation count mismatch at line {line}")
                missing = _int(e.get("missing"), "evidence.missing")
                if missing > current["rows"]:
                    raise ValueError(f"Missing cells exceed area rows at line {line}")
                if kind == "complete_column" and (missing or polarity != "positive"):
                    raise ValueError(f"Inconsistent complete_column at line {line}")
                if kind == "missing_values" and (missing == 0 or polarity != "attention"):
                    raise ValueError(f"Inconsistent missing_values at line {line}")
                stat = by_column[column]
                stat["assessed_areas"] += 1
                stat["rows_assessed"] += current["rows"]
                stat["missing_cells"] += missing
                stat["areas_with_missing"] += int(missing > 0)
            elif kind == "time_structure":
                # Zero/one valid interval in a short artificial area is methodological insufficiency,
                # not evidence that source data is poor.
                for field in ("valid_timestamps", "invalid_timestamps", "adjacent_equal_timestamps",
                              "adjacent_reversals", "positive_intervals"):
                    time_details[field] += _int(e.get(field), field)
                if e["valid_timestamps"] + e["invalid_timestamps"] != current["rows"]:
                    raise ValueError(f"Time evidence count mismatch at line {line}")
                if polarity == "insufficient" and current["role"] == "transition_neighborhood":
                    time_details["transition_insufficient_areas"] += 1
                if polarity == "positive":
                    time_details["positive_time_areas"] += 1
                if polarity == "attention":
                    time_details["attention_time_areas"] += 1
        else:
            raise ValueError(f"Unknown record_type at evidence line {line}")
    finalize()
    if cursor != n or (n and count_areas == 0):
        raise ValueError("Evidence does not cover full source")
    if expected_areas is not None and count_areas != expected_areas:
        raise ValueError("Area count differs from execution manifest")
    if expected_findings is not None and count_findings != expected_findings:
        raise ValueError("Finding count differs from execution manifest")

    reason_counts = Counter()
    boundary_count = 0
    last_after = 0
    for line, boundary in _records(boundaries_path, "boundaries"):
        before, after = boundary.get("before_row"), boundary.get("after_row")
        reasons = boundary.get("reasons")
        if type(before) is not int or type(after) is not int or before != after-1 or not 1 <= after < n:
            raise ValueError(f"Invalid boundary index at line {line}")
        if after <= last_after:
            raise ValueError(f"Out-of-order boundary at line {line}")
        if not isinstance(reasons, list) or not reasons or not all(isinstance(x, str) and x for x in reasons):
            raise ValueError(f"Invalid boundary reasons at line {line}")
        boundary_count += 1
        last_after = after
        reason_counts.update(set(reasons))

    role_out = {k: {"areas": v["areas"], "rows": v["rows"],
                    "row_percentage": round(100*v["rows"]/n, 5) if n else 0.0,
                    "finding_types": dict(sorted(v["findings"].items())),
                    "polarity_counts": dict(sorted(v["polarity"].items()))}
                for k, v in sorted(by_role.items())}
    all_transition = by_role["transition_neighborhood"]["areas"]
    method_insufficient = time_details["transition_insufficient_areas"]
    notes = ["Kvalitetsfynd gäller endast kontrollerade egenskaper; de bevisar inte att mätvärden är korrekta.",
             "Områden med för få jämförbara tidsintervall är inte därmed felaktig källdata.",
             "Områdesstorlek styr endast visningsexempel, inte fyndens betydelse eller statistiska signifikans.",
             "Ingen datarensning, kategorisering av grundorsak eller ny avvikelsedetektion har gjorts."]
    if not source_order_certified:
        notes.append("Källans ursprungliga fysiska radordning är inte certifierad; ordningsberoende tolkningar är preliminära.")
    return {
        "version": VERSION,
        "status": "complete",
        "coverage": {"source_rows": n, "rows_in_areas": cursor, "areas": count_areas,
                     "findings": count_findings, "boundary_events": boundary_count,
                     "exhaustive_evidence_read": True,
                     "source_order_certified": source_order_certified},
        "area_roles": role_out,
        "finding_counts": {p: by_polarity[p] for p in ("positive", "attention", "insufficient")},
        "finding_types": [{"polarity": p, "kind": k, "count": c} for (p, k), c in sorted(by_type.items())],
        "boundary_reasons": dict(sorted(reason_counts.items())),
        "column_completeness": dict(sorted(by_column.items())),
        "time_evidence": dict(sorted(time_details.items())),
        "method_effects": {"transition_areas": all_transition,
                           "transition_areas_with_insufficient_time_evidence": method_insufficient,
                           "interpretation": "otillräcklig tidsevidens i korta övergångsområden är en metodbegränsning, inte ett extra källfel"},
        "examples": {name: samples[name] for name in ("continuity_examples", "attention_examples", "transition_examples", "insufficient_examples")},
        "evidence_sources": {"areas_and_findings": str(Path(evidence_path).resolve()),
                             "boundaries": str(Path(boundaries_path).resolve())},
        "limitations": notes,
    }
