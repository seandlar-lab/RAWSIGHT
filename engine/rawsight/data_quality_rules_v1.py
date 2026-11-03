"""RAWSIGHT DQ-COMP-001 v0.1: narrow, deterministic per-area completeness assessment.

No guessing of required columns, quality thresholds, or source truth.
This module does not change, clean, or reclassify existing quality evidence.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
import json
from pathlib import Path
from typing import Any

RULE_ID = "DQ-COMP-001"
RULE_VERSION = "0.1.0"
ASSESSMENT_SCHEMA = "rawsight.dq.assessment/0.1"


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} måste vara ett heltal >= 0")
    return value


def _validate_requirement(requirement: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(requirement, Mapping):
        raise ValueError("Kravdefinition måste vara ett objekt")
    if requirement.get("rule_id") != RULE_ID or requirement.get("rule_version") != RULE_VERSION:
        raise ValueError("Fel regel-ID eller regelversion")
    column = requirement.get("column")
    source = requirement.get("source")
    area_id = requirement.get("area_id")
    if not isinstance(column, str) or not column.strip():
        raise ValueError("Kravet måste ange kolumn")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Kravet måste ange spårbar källa")
    if not isinstance(area_id, str) or not area_id.strip():
        raise ValueError("Kravet måste ange exakt analysområde (area_id)")
    max_missing = _nonnegative_int(requirement.get("max_missing"), "max_missing")
    return {"rule_id": RULE_ID, "rule_version": RULE_VERSION,
            "column": column, "area_id": area_id,
            "max_missing": max_missing, "source": source}


def _extract_fact(finding: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if finding is None:
        return None
    if not isinstance(finding, Mapping):
        raise ValueError("Evidensfynd måste vara ett objekt")
    if finding.get("record_type") != "finding" or finding.get("kind") != "complete_column":
        raise ValueError("Endast complete_column-fynd stöds")
    column, area_id = finding.get("column"), finding.get("region_id")
    if not isinstance(column, str) or not column.strip():
        raise ValueError("Evidensfynd saknar giltig kolumn")
    if not isinstance(area_id, str) or not area_id.strip():
        raise ValueError("Evidensfynd saknar giltigt region_id")
    evidence = finding.get("evidence")
    rows = missing = None
    if isinstance(evidence, Mapping):
        if "rows" in evidence:
            rows = _nonnegative_int(evidence["rows"], "evidence.rows")
        if "missing" in evidence:
            missing = _nonnegative_int(evidence["missing"], "evidence.missing")
        if rows is not None and missing is not None and missing > rows:
            raise ValueError("Antal saknade värden kan inte överstiga antal rader")
    return {"column": column, "area_id": area_id, "rows": rows,
            "missing": missing, "interpretation_status": finding.get("interpretation_status")}


def assess_completeness(
    finding: Mapping[str, Any] | None,
    requirement: Mapping[str, Any] | None = None,
    *, evidence_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess only one column in one analysis area; never infer whole-dataset quality.

    requirement example: {"rule_id":"DQ-COMP-001", "rule_version":"0.1.0",
      "column":"TP3", "area_id":"region_000000149", "max_missing":0,
      "source":"customer-data-contract:2026-11"}
    The source string identifies the REQUIREMENT origin, not the evidence origin.
    """
    fact = _extract_fact(finding)
    req = _validate_requirement(requirement) if requirement is not None else None
    if evidence_ref is not None and not isinstance(evidence_ref, Mapping):
        raise ValueError("evidence_ref måste vara ett objekt")

    status, reason = "not_assessed", "Ingen tillämplig, dokumenterad kravdefinition angiven."
    if req is not None:
        if fact is not None and (req["column"] != fact["column"] or req["area_id"] != fact["area_id"]):
            raise ValueError("Kravets kolumn eller analysområde matchar inte evidensen")
        if fact is None or fact["rows"] is None or fact["rows"] == 0 or fact["missing"] is None or fact["interpretation_status"] not in (None, "observed"):
            status, reason = "insufficient_evidence", "Saknar komplett, direkt observerad evidens för kravets omfattning."
        else:
            status = "verified" if fact["missing"] <= req["max_missing"] else "violation"
            reason = (f"Observerat {fact['missing']} saknade av {fact['rows']} värden; "
                      f"kravet tillåter högst {req['max_missing']} i detta analysområde.")
    return {
        "schema": ASSESSMENT_SCHEMA,
        "rule_id": RULE_ID, "rule_version": RULE_VERSION,
        "status": status, "reason_sv": reason,
        "scope": {"type": "area_column", "area_id": (req or fact or {}).get("area_id"),
                  "column": (req or fact or {}).get("column")},
        "fact": {"rows": fact["rows"], "missing": fact["missing"]} if fact else None,
        "requirement": {"max_missing": req["max_missing"], "source": req["source"]} if req else None,
        "evidence_ref": dict(evidence_ref) if evidence_ref is not None else None,
        "limitations": ["Gäller endast angiven kolumn och angivet analysområde; inte hela datamängden."],
    }


def iter_completeness_assessments(
    evidence_path: str | Path,
    requirements: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream an existing evidence JSONL; key requirements by (area_id, column).

    Only `complete_column` findings are assessed. The file is never modified.
    A requirement lacking a matching fact produces insufficient_evidence at EOF.
    This API assesses per area and column; never infers whole-dataset quality.
    """
    requirements = {} if requirements is None else requirements
    if not isinstance(requirements, Mapping):
        raise ValueError("requirements måste vara en mappning")
    validated = {}
    for key, requirement in requirements.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("Kravnyckeln ska vara (area_id, column)")
        req = _validate_requirement(requirement)
        if key != (req["area_id"], req["column"]):
            raise ValueError("Kravnyckeln matchar inte kravets omfattning")
        validated[key] = requirement
    seen_requirements = set()
    path = Path(evidence_path).resolve()
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"Tom JSONL-rad: {line_no}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Ogiltig JSON på rad {line_no}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"JSONL-rad {line_no} måste vara objekt")
            if record.get("record_type") != "finding" or record.get("kind") != "complete_column":
                continue
            key = (record.get("region_id"), record.get("column"))
            if key in validated:
                if key in seen_requirements:
                    raise ValueError(f"Dubbelt fullständighetsfynd för krav: {key}")
                seen_requirements.add(key)
            yield assess_completeness(record, validated.get(key),
                                      evidence_ref={"path": str(path), "line": line_no})
    for key in validated:
        if key not in seen_requirements:
            yield assess_completeness(None, validated[key])
