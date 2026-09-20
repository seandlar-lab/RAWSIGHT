from __future__ import annotations


def select_analysis_strategy(
    structural_model: dict,
) -> dict:
    """
    Select a safe analysis strategy from observed structural
    evidence.

    Temporal-axis orientation is the primary routing fact.
    A specialized temporal strategy is selected only when one
    temporal axis has also been promoted unambiguously.

    Structural orientation and semantic axis selection remain
    separate decisions.
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

    temporal_axis = logical.get(
        "temporal_axis"
    )

    temporal_candidates = logical.get(
        "temporal_axis_candidates",
        [],
    )

    orientation_summary = logical.get(
        "temporal_axis_orientation",
        {},
    )

    orientation = orientation_summary.get(
        "orientation"
    )

    reasons = []

    # Backward-compatible fallback for structural models created
    # before temporal_axis_orientation became part of the common
    # contract. Current inspection paths always populate it.
    if orientation is None:
        if temporal_axis is not None:
            orientation = temporal_axis.get(
                "orientation"
            )
        elif temporal_candidates:
            candidate_orientations = {
                candidate.get("orientation")
                for candidate in temporal_candidates
                if candidate.get("orientation")
                in {"horizontal", "vertical"}
            }

            if candidate_orientations == {"horizontal"}:
                orientation = "horizontal"
            elif candidate_orientations == {"vertical"}:
                orientation = "vertical"
            elif candidate_orientations:
                orientation = "ambiguous"
            else:
                orientation = "none"
        else:
            orientation = "none"

    if orientation == "horizontal":
        if (
            temporal_axis is not None
            and temporal_axis.get("orientation")
            == "horizontal"
        ):
            reasons.append(
                "horizontal_temporal_axis_promoted"
            )

            return {
                "strategy": "wide_temporal",
                "can_use_legacy_profile": False,
                "reason_codes": reasons,
            }

        reasons.append(
            "horizontal_temporal_structure_without_promoted_axis"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    if orientation == "vertical":
        if (
            temporal_axis is not None
            and temporal_axis.get("orientation")
            == "vertical"
        ):
            reasons.append(
                "vertical_temporal_axis_promoted"
            )

            return {
                "strategy": "long_temporal",
                "can_use_legacy_profile": False,
                "reason_codes": reasons,
            }

        reasons.append(
            "vertical_temporal_structure_without_promoted_axis"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    if orientation == "ambiguous":
        reasons.append(
            "temporal_axis_orientation_ambiguous"
        )

        return {
            "strategy": "conservative_tabular",
            "can_use_legacy_profile": False,
            "reason_codes": reasons,
        }

    if temporal_candidates:
        reasons.append(
            "temporal_candidates_without_supported_orientation"
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
