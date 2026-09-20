"""
Compatibility façade for RAWSIGHT dataset inspection and access.

Implementation is split into focused modules while existing imports such as

    from rawsight.datasets import inspect_source, open_dataset

remain valid.
"""

from .analysis_strategy import select_analysis_strategy
from .dataset_access import open_dataset
from .logical_structure import (
    analyze_tabular_logical_structure,
    extract_tabular_run_values,
    find_tabular_temporal_runs,
    infer_tabular_layout_candidate,
)
from .source_inspection import (
    build_delimited_physical_structure,
    inspect_delimited_file,
    inspect_source,
    preview_csv_structure,
)
from .structural_model import (
    attach_structural_model,
    create_structural_model,
)
from .tabular_structure import (
    analyze_structural_boundaries,
    build_tabular_structural_evidence,
    classify_structural_value,
    extract_tabular_sequence,
    find_structural_region_starts,
    find_structural_transitions,
    profile_structural_sequence,
    profile_tabular_structure,
    structural_profile_distance,
    structural_profile_distribution,
    summarize_structural_region_candidates,
)
from .temporal_structure import (
    TEMPORAL_FORMATS,
    analyze_temporal_cadence,
    analyze_temporal_order,
    analyze_temporal_values,
    build_temporal_axis_candidate,
    evaluate_temporal_header_run,
    evaluate_temporal_sequence,
    find_temporal_header_runs,
    find_temporal_runs,
    normalize_temporal_sequence,
    parse_temporal_header_value,
    parse_temporal_value,
)

__all__ = [
    "TEMPORAL_FORMATS",
    "preview_csv_structure",
    "create_structural_model",
    "attach_structural_model",
    "build_delimited_physical_structure",
    "parse_temporal_value",
    "parse_temporal_header_value",
    "extract_tabular_sequence",
    "classify_structural_value",
    "profile_structural_sequence",
    "profile_tabular_structure",
    "structural_profile_distribution",
    "structural_profile_distance",
    "find_structural_transitions",
    "analyze_structural_boundaries",
    "find_structural_region_starts",
    "summarize_structural_region_candidates",
    "build_tabular_structural_evidence",
    "infer_tabular_layout_candidate",
    "find_tabular_temporal_runs",
    "extract_tabular_run_values",
    "find_temporal_runs",
    "find_temporal_header_runs",
    "evaluate_temporal_sequence",
    "normalize_temporal_sequence",
    "analyze_temporal_order",
    "analyze_temporal_cadence",
    "analyze_temporal_values",
    "build_temporal_axis_candidate",
    "analyze_tabular_logical_structure",
    "select_analysis_strategy",
    "evaluate_temporal_header_run",
    "inspect_delimited_file",
    "inspect_source",
    "open_dataset",
]
