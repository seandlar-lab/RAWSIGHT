from __future__ import annotations


def select_analysis_strategy(
    structural_model: dict,
) -> dict:
    """
    Select a safe analysis strategy from observed structural
    evidence.

    Routing is safety-oriented. A structural candidate may be
    sufficient to avoid an unsafe generic analysis path even
    when semantic interpretation is not yet definitive.
    """

    logical = structural_model.get(
        "logical_structure",
        {},
    )

    physical = structural_model.get(
        "physical_structure",
        {},
    )

    structure_type = logical.get(
        "structure_type",
        "unknown",
    )

    layout_candidate = logical.get(
        "layout_candidate"
    )

    temporal_candidates = logical.get(
        "temporal_axis_candidates",
        [],
    )

    reasons = []

    if layout_candidate is not None:
        layout_kind = layout_candidate.get(
            "kind"
        )

        if layout_kind == "wide_temporal":
            reasons.append(
                "wide_temporal_layout_candidate"
            )

            return {
                "strategy": "wide_temporal",
                "can_use_legacy_profile": False,
                "reason_codes": reasons,
            }

        if layout_kind == "long_temporal":
            reasons.append(
                "long_temporal_layout_candidate"
            )

            return {
                "strategy": "long_temporal",
                "can_use_legacy_profile": False,
                "reason_codes": reasons,
            }

    if temporal_candidates:
        reasons.append(
            "temporal_structure_is_ambiguous"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    if structure_type == "tabular":
        reasons.append(
            "tabular_structure_without_specialized_layout"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    if physical.get("kind") == "delimited_text":
        reasons.append(
            "delimited_structure_not_safely_classified"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    reasons.append(
        "structure_not_safely_classified"
    )

    return {
        "strategy": "conservative_unknown",
        "can_use_legacy_profile": False,
        "reason_codes": reasons,
    }
