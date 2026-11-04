"""RAWSIGHT Quality Requirements Profile v0.1.

A validated, immutable-in-use requirement resolver for DQ-COMP-001.
No implicit thresholds, no automatic approval, and no source-data modification.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
import json
import re
from typing import Any

from rawsight.data_quality_rules_v1 import assess_completeness

PROFILE_SCHEMA = "rawsight.dq.requirements_profile/0.1"
FINGERPRINT_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} måste vara en icke-tom sträng")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} måste vara ett icke-negativt heltal")
    return value


def validate_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Return validated deep independent copy; fail closed on ambiguity."""
    if not isinstance(profile, Mapping):
        raise ValueError("Kravprofilen måste vara ett objekt")
    if profile.get("schema") != PROFILE_SCHEMA:
        raise ValueError("Okänt schema för kravprofil")
    _string(profile.get("profile_id"), "profile_id")
    _string(profile.get("profile_version"), "profile_version")
    status = profile.get("status")
    if status not in ("draft", "approved"):
        raise ValueError("status måste vara draft eller approved")
    source = profile.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("source måste vara ett objekt")
    _string(source.get("dataset_id"), "source.dataset_id")
    fingerprint = source.get("sha256")
    if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
        raise ValueError("source.sha256 måste vara 64 hex-tecken")
    rules = profile.get("requirements")
    if not isinstance(rules, list):
        raise ValueError("requirements måste vara en lista")
    seen_ids: set[str] = set()
    keys: set[tuple[str, str, str | None]] = set()
    for idx, rule in enumerate(rules):
        label = f"requirements[{idx}]"
        if not isinstance(rule, Mapping):
            raise ValueError(f"{label} måste vara ett objekt")
        rid = _string(rule.get("requirement_id"), f"{label}.requirement_id")
        if rid in seen_ids:
            raise ValueError(f"Dubbelt krav-ID: {rid}")
        seen_ids.add(rid)
        if rule.get("rule_id") != "DQ-COMP-001" or rule.get("rule_version") != "0.1.0":
            raise ValueError(f"{label}: endast DQ-COMP-001/0.1.0 stöds")
        col = _string(rule.get("column"), f"{label}.column")
        scope = rule.get("scope")
        if scope not in ("dataset_column", "area_column"):
            raise ValueError(f"{label}: ogiltigt scope")
        area_id = rule.get("area_id")
        if scope == "area_column":
            _string(area_id, f"{label}.area_id")
        elif area_id is not None:
            raise ValueError(f"{label}: dataset_column får inte ha area_id")
        _nonnegative_int(rule.get("max_missing"), f"{label}.max_missing")
        _string(rule.get("source"), f"{label}.source")
        key = (scope, col, area_id)
        if key in keys:
            raise ValueError(f"Motstridiga krav på samma nivå: {key}")
        keys.add(key)
        override = rule.get("overrides")
        if scope == "dataset_column" and override is not None:
            raise ValueError(f"{label}: overrides stöds bara på områdesnivå")
        if scope == "area_column" and override is not None:
            _string(override, f"{label}.overrides")
    indexed = {r["requirement_id"]: r for r in rules}
    for rule in rules:
        if rule["scope"] == "area_column":
            base = next((r for r in rules if r["scope"] == "dataset_column" and r["column"] == rule["column"]), None)
            override = rule.get("overrides")
            if base is not None and override != base["requirement_id"]:
                raise ValueError(f"Områdeskrav {rule['requirement_id']} måste uttryckligen ange overrides={base['requirement_id']}")
            if base is None and override is not None:
                raise ValueError(f"Områdeskrav {rule['requirement_id']} refererar till krav som inte är tillämpligt")
            if override is not None and override not in indexed:
                raise ValueError(f"Okänt overrides-ID: {override}")
    if status == "approved":
        _string(profile.get("approved_by"), "approved_by")
        _string(profile.get("approved_at"), "approved_at")
    # JSON roundtrip enforces JSON serialisability and yields standalone copy.
    try:
        return json.loads(json.dumps(profile, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("Kravprofilen måste vara JSON-kompatibel") from exc


def load_profile(path: str | Path) -> dict[str, Any]:
    return validate_profile(json.loads(Path(path).read_text(encoding="utf-8-sig")))


def resolve_requirement(
    profile: Mapping[str, Any], *, dataset_id: str, source_sha256: str,
    area_id: str, column: str,
) -> dict[str, Any] | None:
    """Resolve an approved profile to existing narrow DQ-COMP-001 contract.

    None means not assessed. Dataset identity and SHA-256 must both match.
    Area-specific overrides must be explicitly declared in profile.
    """
    p = validate_profile(profile)
    _string(dataset_id, "dataset_id")
    _string(area_id, "area_id")
    _string(column, "column")
    if not isinstance(source_sha256, str) or not FINGERPRINT_RE.fullmatch(source_sha256):
        raise ValueError("source_sha256 måste vara SHA-256 (64 hex-tecken)")
    if p["source"]["dataset_id"] != dataset_id or p["source"]["sha256"].lower() != source_sha256.lower():
        raise ValueError("Kravprofilen är inte bunden till den valda datakällan/versionen")
    if p["status"] != "approved":
        return None
    return _resolve_validated(p, area_id, column)


def _resolve_validated(p: Mapping[str, Any], area_id: str, column: str) -> dict[str, Any] | None:
    if p["status"] != "approved":
        return None
    selected = None
    for r in p["requirements"]:
        if r["column"] != column:
            continue
        if r["scope"] == "dataset_column":
            if selected is None:
                selected = r
        elif r["area_id"] == area_id:
            selected = r
            break
    if selected is None:
        return None
    return {
        "rule_id": "DQ-COMP-001", "rule_version": "0.1.0",
        "column": column, "area_id": area_id,
        "max_missing": selected["max_missing"],
        "source": f"{selected['source']} | profile:{p['profile_id']}@{p['profile_version']} | requirement:{selected['requirement_id']}",
    }


def iter_profile_assessments(
    evidence_path: str | Path, profile: Mapping[str, Any], *,
    dataset_id: str, source_sha256: str,
) -> Iterator[dict[str, Any]]:
    """Stream observed complete_column facts, assess with an approved profile.

    No claims about requirements absent from evidence; missing area facts require
    a separate source/coverage audit, not guessed observations.
    """
    p = validate_profile(profile)
    # Validate binding up front, even if the evidence file has no finding.
    if p["source"]["dataset_id"] != dataset_id or p["source"]["sha256"].lower() != source_sha256.lower():
        raise ValueError("Kravprofil och datakälla matchar inte")
    path = Path(evidence_path).resolve()
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            if not line.strip():
                raise ValueError(f"Tom evidensrad {lineno}")
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Ogiltigt evidensobjekt på rad {lineno}")
            if record.get("record_type") != "finding" or record.get("kind") != "complete_column":
                continue
            req = _resolve_validated(p, record["region_id"], record["column"])
            yield assess_completeness(record, req, evidence_ref={"path": str(path), "line": lineno})
