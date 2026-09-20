from __future__ import annotations

from .tabular_structure import (
    build_tabular_structural_evidence,
    extract_tabular_sequence,
)
from .temporal_structure import (
    analyze_temporal_values,
    build_temporal_axis_candidate,
    find_temporal_runs,
)



def _summarize_temporal_axis_orientation(
    temporal_candidates: list[dict],
) -> dict:
    """
    Summarize which tabular orientation contains temporal-axis
    evidence without deciding which individual candidate is the
    semantic temporal axis.

    Candidate counts are based on distinct structural positions,
    so multiple valid date-format interpretations of the same
    observed run do not inflate the counts.
    """

    positions = {
        "horizontal": set(),
        "vertical": set(),
    }

    for candidate in temporal_candidates:
        orientation = candidate.get("orientation")

        if orientation not in positions:
            continue

        positions[orientation].add((
            candidate.get("sequence_index"),
            candidate.get("start_index"),
            candidate.get("end_index"),
        ))

    horizontal_count = len(
        positions["horizontal"]
    )
    vertical_count = len(
        positions["vertical"]
    )

    if horizontal_count and vertical_count:
        orientation = "ambiguous"
    elif horizontal_count:
        orientation = "horizontal"
    elif vertical_count:
        orientation = "vertical"
    else:
        orientation = "none"

    return {
        "orientation": orientation,
        "horizontal_candidate_count": horizontal_count,
        "vertical_candidate_count": vertical_count,
    }


def infer_tabular_layout_candidate(
    temporal_axis: dict | None,
    structural_evidence: dict,
) -> dict | None:
    """
    Infer a candidate tabular layout from independent structural
    observations.

    The result remains a candidate. No confidence threshold is
    used and no semantic header/data assumption is required.
    """

    if temporal_axis is None:
        return None

    orientation = temporal_axis[
        "orientation"
    ]

    if orientation == "horizontal":
        horizontal = structural_evidence[
            "horizontal_regions"
        ]

        ranked = horizontal[
            "ranked_candidates"
        ]

        candidate = {
            "kind": "wide_temporal",
            "status": "candidate",
            "basis": [
                "horizontal_temporal_axis",
            ],
        }

        if ranked:
            leading = ranked[0]

            candidate[
                "leading_region_start"
            ] = leading[
                "start_sequence_index"
            ]

            candidate[
                "region_evidence_score"
            ] = leading[
                "evidence_score"
            ]

            candidate[
                "region_score_margin"
            ] = horizontal[
                "score_margin"
            ]

            if (
                temporal_axis["sequence_index"]
                < leading[
                    "start_sequence_index"
                ]
            ):
                candidate["basis"].append(
                    "stable_region_follows_temporal_axis"
                )

        return candidate

    if orientation == "vertical":
        return {
            "kind": "long_temporal",
            "status": "candidate",
            "basis": [
                "vertical_temporal_axis",
            ],
            "temporal_sequence_index": (
                temporal_axis[
                    "sequence_index"
                ]
            ),
        }

    return None


def find_tabular_temporal_runs(
    rows: list[list[object]],
    min_length: int = 3,
) -> list[dict]:
    """
    Find temporal runs in both orientations of a tabular preview.

    This function reports where temporal-looking sequences occur.
    It does not assign semantic meaning such as header, date
    column, measure, or dimension.
    """

    results = []

    # Horizontal sequences.
    for row_index in range(len(rows)):
        values = extract_tabular_sequence(
            rows,
            orientation="horizontal",
            index=row_index,
        )

        for run in find_temporal_runs(
            values,
            min_length=min_length,
        ):
            results.append({
                "orientation": "horizontal",
                "sequence_index": row_index,
                **run,
            })

    # Vertical sequences.
    max_width = max(
        (len(row) for row in rows),
        default=0,
    )

    for column_index in range(max_width):
        values = extract_tabular_sequence(
            rows,
            orientation="vertical",
            index=column_index,
        )

        for run in find_temporal_runs(
            values,
            min_length=min_length,
        ):
            results.append({
                "orientation": "vertical",
                "sequence_index": column_index,
                **run,
            })

    return results


def extract_tabular_run_values(
    rows: list[list[object]],
    run: dict,
) -> list[object]:
    """
    Extract the values belonging to one detected tabular run.

    Orientation and position are handled at this boundary.
    Downstream analysis receives only the resulting sequence.
    """

    sequence = extract_tabular_sequence(
        rows,
        orientation=run["orientation"],
        index=run["sequence_index"],
    )

    start_index = run["start_index"]
    end_index = run["end_index"]

    return sequence[
        start_index:end_index + 1
    ]


def analyze_tabular_logical_structure(
    rows: list[list[object]],
) -> dict:
    """
    Derive logical structure from a tabular preview.

    Observed evidence, candidates, and semantic conclusions are
    kept separate. Ambiguity is preserved instead of resolved
    arbitrarily.
    """

    logical_structure = {
        "structure_type": "tabular",

        # Semantic conclusions.
        "header_band": None,
        "descriptor_fields": [],
        "measures": [],
        "dimensions": [],

        # Temporal evidence.
        "temporal_axis": None,
        "temporal_axis_candidates": [],
        "temporal_axis_orientation": {
            "orientation": "none",
            "horizontal_candidate_count": 0,
            "vertical_candidate_count": 0,
        },

        # Structural evidence.
        "structural_evidence": None,
        "candidate_data_start": None,
        "candidate_pre_data_band": None,

        # Higher-level inference.
        "layout_candidate": None,
    }

    structural_evidence = (
        build_tabular_structural_evidence(
            rows
        )
    )

    logical_structure[
        "structural_evidence"
    ] = structural_evidence

    runs = find_tabular_temporal_runs(
        rows
    )

    analyzed_runs = []

    for run in runs:
        values = extract_tabular_run_values(
            rows,
            run,
        )

        analyses = analyze_temporal_values(
            values
        )

        for analysis in analyses:
            analyzed_runs.append({
                **run,
                **analysis,
            })

    temporal_candidates = [
        build_temporal_axis_candidate(
            detected
        )
        for detected in analyzed_runs
    ]

    logical_structure[
        "temporal_axis_candidates"
    ] = temporal_candidates

    logical_structure[
        "temporal_axis_orientation"
    ] = _summarize_temporal_axis_orientation(
        temporal_candidates
    )

    if temporal_candidates:
        logical_structure[
            "structure_type"
        ] = "tabular_temporal"

    # Promote only an unambiguous temporal candidate.
    if len(temporal_candidates) == 1:
        logical_structure[
            "temporal_axis"
        ] = temporal_candidates[0]

    horizontal_regions = structural_evidence[
        "horizontal_regions"
    ]

    ranked_regions = horizontal_regions[
        "ranked_candidates"
    ]

    # Preserve the structural-region inference as a candidate,
    # including its evidence and ambiguity.
    if ranked_regions:
        leading = ranked_regions[0]

        logical_structure[
            "candidate_data_start"
        ] = {
            "orientation": "horizontal",
            "sequence_index": leading[
                "start_sequence_index"
            ],
            "status": "candidate",
            "evidence_score": leading[
                "evidence_score"
            ],
            "runner_up_score": (
                horizontal_regions[
                    "runner_up_score"
                ]
            ),
            "score_margin": (
                horizontal_regions[
                    "score_margin"
                ]
            ),
            "candidate_count": (
                horizontal_regions[
                    "candidate_count"
                ]
            ),
        }

        start_index = leading[
            "start_sequence_index"
        ]

        if start_index > 0:
            logical_structure[
                "candidate_pre_data_band"
            ] = {
                "orientation": "horizontal",
                "start_sequence_index": 0,
                "end_sequence_index": (
                    start_index - 1
                ),
                "depth": start_index,
                "status": "candidate",
                "basis": [
                    "precedes_ranked_structural_region",
                ],
            }

    logical_structure[
        "layout_candidate"
    ] = infer_tabular_layout_candidate(
        logical_structure[
            "temporal_axis"
        ],
        structural_evidence,
    )

    return logical_structure
