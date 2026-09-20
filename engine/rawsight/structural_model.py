from __future__ import annotations


def create_structural_model(
    *,
    detected_format: str,
    format_confidence: float,
    inspection_status: str,
    extension: str,
    file_size_bytes: int,
) -> dict:
    """
    Create the format-neutral structural model used by RAWSIGHT.

    Format-specific inspectors may populate additional details,
    but downstream analysis should be able to rely on this shape.
    """

    return {
        "source": {
            "extension": extension,
            "file_size_bytes": file_size_bytes,
        },
        "format": {
            "detected_format": detected_format,
            "format_confidence": format_confidence,
            "inspection_status": inspection_status,
        },
        "physical_structure": {},
        "logical_structure": {
            "structure_type": "unknown",

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

            # Higher-level layout inference.
            "layout_candidate": None,
        },
    }


def attach_structural_model(
    inspection: dict,
    physical_structure: dict | None = None,
    logical_structure: dict | None = None,
) -> dict:
    """
    Attach the common RAWSIGHT structural model while preserving
    all format-specific inspection details.
    """

    model = create_structural_model(
        detected_format=inspection.get(
            "detected_format",
            "unknown",
        ),
        format_confidence=inspection.get(
            "format_confidence",
            0.0,
        ),
        inspection_status=inspection.get(
            "inspection_status",
            "unknown",
        ),
        extension=inspection.get(
            "extension",
            "",
        ),
        file_size_bytes=inspection.get(
            "file_size_bytes",
            0,
        ),
    )
    if logical_structure is not None:
        model["logical_structure"] = logical_structure

    return {
        **inspection,
        "structural_model": model,
    }
