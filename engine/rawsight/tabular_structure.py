from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .temporal_structure import parse_temporal_value


def extract_tabular_sequence(
    rows: list[list[object]],
    *,
    orientation: str,
    index: int,
) -> list[object]:
    """
    Extract one sequence from a two-dimensional tabular preview.

    Horizontal and vertical orientation are handled only at this
    extraction boundary. Missing cells in ragged rows are
    preserved as None so downstream detection can see the gap.
    """

    if orientation == "horizontal":
        if index < 0 or index >= len(rows):
            return []

        return list(rows[index])

    if orientation == "vertical":
        if index < 0:
            return []

        return [
            (
                row[index]
                if index < len(row)
                else None
            )
            for row in rows
        ]

    raise ValueError(
        f"Unsupported orientation: {orientation}"
    )


def classify_structural_value(
    value: object,
) -> str:
    """
    Classify one observed value structurally.

    Classification is deliberately conservative and does not
    assign business semantics such as measure, identifier,
    dimension, or missing-value marker.
    """

    if value is None:
        return "empty"

    text = str(value).strip()

    if not text:
        return "empty"

    if parse_temporal_value(value):
        return "temporal"

    try:
        numeric = Decimal(text)

        if numeric.is_finite():
            return "numeric"

    except InvalidOperation:
        pass

    return "text"


def profile_structural_sequence(
    values: list[object],
) -> dict:
    """
    Profile one structural sequence without assigning semantics.

    The sequence may represent a row, a column, or another
    ordered collection. No header/data assumption is made.
    """

    type_counts = {
        "empty": 0,
        "temporal": 0,
        "numeric": 0,
        "text": 0,
    }

    for value in values:
        value_type = classify_structural_value(
            value
        )

        type_counts[value_type] += 1

    value_count = len(values)
    nonempty_count = (
        value_count - type_counts["empty"]
    )

    def fraction(
        count: int,
    ) -> float:
        if not nonempty_count:
            return 0.0

        return count / nonempty_count

    return {
        "value_count": value_count,
        "nonempty_count": nonempty_count,
        "empty_count": type_counts["empty"],
        "temporal_candidate_count": type_counts[
            "temporal"
        ],
        "numeric_candidate_count": type_counts[
            "numeric"
        ],
        "text_candidate_count": type_counts[
            "text"
        ],
        "temporal_fraction": fraction(
            type_counts["temporal"]
        ),
        "numeric_fraction": fraction(
            type_counts["numeric"]
        ),
        "text_fraction": fraction(
            type_counts["text"]
        ),
    }


def profile_tabular_structure(
    rows: list[list[object]],
) -> dict:
    """
    Profile both orientations of a tabular preview.

    Profiling is structural only. Rows and columns are not
    classified as headers, dimensions, measures, or data here.
    """

    horizontal = []

    for row_index in range(len(rows)):
        values = extract_tabular_sequence(
            rows,
            orientation="horizontal",
            index=row_index,
        )

        horizontal.append({
            "sequence_index": row_index,
            **profile_structural_sequence(values),
        })

    max_width = max(
        (len(row) for row in rows),
        default=0,
    )

    vertical = []

    for column_index in range(max_width):
        values = extract_tabular_sequence(
            rows,
            orientation="vertical",
            index=column_index,
        )

        vertical.append({
            "sequence_index": column_index,
            **profile_structural_sequence(values),
        })

    return {
        "horizontal": horizontal,
        "vertical": vertical,
    }


def structural_profile_distribution(
    profile: dict,
) -> dict:
    """
    Convert a structural profile to a normalized distribution.

    The four fractions sum to 1.0 when values are present.
    """

    value_count = profile.get(
        "value_count",
        0,
    )

    if not value_count:
        return {
            "empty": 0.0,
            "temporal": 0.0,
            "numeric": 0.0,
            "text": 0.0,
        }

    return {
        "empty": (
            profile.get("empty_count", 0)
            / value_count
        ),
        "temporal": (
            profile.get(
                "temporal_candidate_count",
                0,
            )
            / value_count
        ),
        "numeric": (
            profile.get(
                "numeric_candidate_count",
                0,
            )
            / value_count
        ),
        "text": (
            profile.get(
                "text_candidate_count",
                0,
            )
            / value_count
        ),
    }


def structural_profile_distance(
    first: dict,
    second: dict,
) -> float:
    """
    Measure structural difference between two sequence profiles.

    0.0 means identical type distributions.
    1.0 means completely different distributions.
    """

    first_distribution = (
        structural_profile_distribution(first)
    )

    second_distribution = (
        structural_profile_distribution(second)
    )

    return sum(
        abs(
            first_distribution[key]
            - second_distribution[key]
        )
        for key in (
            "empty",
            "temporal",
            "numeric",
            "text",
        )
    ) / 2.0


def find_structural_transitions(
    profiles: list[dict],
) -> list[dict]:
    """
    Compare adjacent structural profiles.

    Transitions are evidence only. No header/data semantic
    interpretation is assigned here.
    """

    transitions = []

    for first, second in zip(
        profiles,
        profiles[1:],
    ):
        transitions.append({
            "from_sequence_index": first[
                "sequence_index"
            ],
            "to_sequence_index": second[
                "sequence_index"
            ],
            "distance": structural_profile_distance(
                first,
                second,
            ),
        })

    return sorted(
        transitions,
        key=lambda item: item["distance"],
        reverse=True,
    )


def analyze_structural_boundaries(
    profiles: list[dict],
) -> list[dict]:
    """
    Describe evidence around every structural boundary.

    A boundary is not assigned semantic meaning here.
    We measure both the change at the boundary and how stable
    the structure is on each side when observations exist.
    """

    if len(profiles) < 2:
        return []

    transitions = find_structural_transitions(
        profiles
    )

    distance_by_boundary = {
        (
            item["from_sequence_index"],
            item["to_sequence_index"],
        ): item["distance"]
        for item in transitions
    }

    results = []

    for position in range(
        len(profiles) - 1
    ):
        first = profiles[position]
        second = profiles[position + 1]

        boundary_distance = (
            distance_by_boundary.get(
                (
                    first["sequence_index"],
                    second["sequence_index"],
                ),
                0.0,
            )
        )

        before_distances = []

        for index in range(position):
            before_distances.append(
                structural_profile_distance(
                    profiles[index],
                    profiles[index + 1],
                )
            )

        after_distances = []

        for index in range(
            position + 1,
            len(profiles) - 1,
        ):
            after_distances.append(
                structural_profile_distance(
                    profiles[index],
                    profiles[index + 1],
                )
            )

        before_mean = (
            sum(before_distances)
            / len(before_distances)
            if before_distances
            else None
        )

        after_mean = (
            sum(after_distances)
            / len(after_distances)
            if after_distances
            else None
        )

        results.append({
            "from_sequence_index": first[
                "sequence_index"
            ],
            "to_sequence_index": second[
                "sequence_index"
            ],
            "boundary_distance": boundary_distance,
            "before_sequence_count": (
                position + 1
            ),
            "after_sequence_count": (
                len(profiles)
                - position
                - 1
            ),
            "before_mean_internal_distance": (
                before_mean
            ),
            "after_mean_internal_distance": (
                after_mean
            ),
        })

    return sorted(
        results,
        key=lambda item: item[
            "boundary_distance"
        ],
        reverse=True,
    )


def find_structural_region_starts(
    profiles: list[dict],
) -> list[dict]:
    """
    Identify candidate starts of structurally stable regions.

    Candidates are based on the contrast between the structural
    change at a boundary and the internal variation after it.

    No semantic meaning such as header or data region is
    assigned here.
    """

    boundaries = analyze_structural_boundaries(
        profiles
    )

    candidates = []

    for boundary in boundaries:
        after_mean = boundary[
            "after_mean_internal_distance"
        ]

        if after_mean is None:
            after_mean = 0.0

        region_contrast = (
            boundary["boundary_distance"]
            - after_mean
        )

        total_sequence_count = len(profiles)

        support_fraction = (
            boundary["after_sequence_count"]
            / total_sequence_count
            if total_sequence_count
            else 0.0
        )

        evidence_score = (
            max(region_contrast, 0.0)
            * support_fraction
        )

        candidates.append({
            "start_sequence_index": boundary[
                "to_sequence_index"
            ],
            "boundary_distance": boundary[
                "boundary_distance"
            ],
            "after_sequence_count": boundary[
                "after_sequence_count"
            ],
            "after_mean_internal_distance": (
                boundary[
                    "after_mean_internal_distance"
                ]
            ),
            "region_contrast": region_contrast,
            "support_fraction": support_fraction,
            "evidence_score": evidence_score,
        })

    return sorted(
        candidates,
        key=lambda item: item[
            "evidence_score"
        ],
        reverse=True,
    )


def summarize_structural_region_candidates(
    profiles: list[dict],
    *,
    orientation: str,
) -> dict:
    """
    Summarize evidence for structural region-start candidates.

    The result preserves ambiguity and does not assign semantic
    meaning such as header boundary, data start, dimension,
    measure, or record region.
    """

    ranked_candidates = [
        candidate
        for candidate in find_structural_region_starts(
            profiles
        )
        if candidate["evidence_score"] > 0.0
    ]

    if not ranked_candidates:
        return {
            "orientation": orientation,
            "candidate_count": 0,
            "ranked_candidates": [],
            "leading_score": None,
            "runner_up_score": None,
            "score_margin": None,
        }

    leading_score = ranked_candidates[0][
        "evidence_score"
    ]

    runner_up_score = (
        ranked_candidates[1]["evidence_score"]
        if len(ranked_candidates) > 1
        else None
    )

    score_margin = (
        leading_score - runner_up_score
        if runner_up_score is not None
        else None
    )

    return {
        "orientation": orientation,
        "candidate_count": len(
            ranked_candidates
        ),
        "ranked_candidates": ranked_candidates,
        "leading_score": leading_score,
        "runner_up_score": runner_up_score,
        "score_margin": score_margin,
    }


def build_tabular_structural_evidence(
    rows: list[list[object]],
) -> dict:
    """
    Build structural evidence for both orientations of a
    tabular preview.

    Evidence is preserved independently of semantic
    interpretation.
    """

    profiles = profile_tabular_structure(
        rows
    )

    return {
        "horizontal_regions": (
            summarize_structural_region_candidates(
                profiles["horizontal"],
                orientation="horizontal",
            )
        ),
        "vertical_regions": (
            summarize_structural_region_candidates(
                profiles["vertical"],
                orientation="vertical",
            )
        ),
    }
