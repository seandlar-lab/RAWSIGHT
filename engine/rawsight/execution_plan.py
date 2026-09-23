from __future__ import annotations

from typing import Any

from rawsight.resource_assessment import (
    compare_working_set_to_available_memory,
    inspect_memory_resources,
)


def _validate_optional_bool(
    value: bool | None,
    name: str,
) -> None:
    if value is not None and not isinstance(value, bool):
        raise TypeError(
            f"{name} must be bool or None"
        )


def build_execution_plan(
    *,
    analysis_strategy: str,
    execution_mode: str,
    estimated_peak_bytes: int | None = None,
    estimate_basis: str | None = None,
    estimate_confidence: str | None = None,
    streaming_capable: bool | None = None,
    materialization_required: bool | None = None,
    resource_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build an execution plan from analysis intent and current resources.

    The function deliberately does not invent dataset-size limits,
    batch sizes, or warning percentages.

    If an estimated peak working set is supplied, it is compared with
    currently available physical memory. If no estimate is supplied,
    the plan remains explicit about that uncertainty.

    Estimation itself belongs to an executor/source-specific estimator,
    because different formats and operations have different working-set
    behaviour.
    """

    if not analysis_strategy:
        raise ValueError(
            "analysis_strategy must not be empty"
        )

    if not execution_mode:
        raise ValueError(
            "execution_mode must not be empty"
        )

    _validate_optional_bool(
        streaming_capable,
        "streaming_capable",
    )
    _validate_optional_bool(
        materialization_required,
        "materialization_required",
    )

    if (
        estimated_peak_bytes is not None
        and estimated_peak_bytes < 0
    ):
        raise ValueError(
            "estimated_peak_bytes must not be negative"
        )

    snapshot = (
        resource_snapshot
        if resource_snapshot is not None
        else inspect_memory_resources()
    )

    memory = snapshot.get(
        "memory",
        {},
    )

    available_memory_bytes = memory.get(
        "available_memory_bytes"
    )

    if estimated_peak_bytes is None:
        comparison = {
            "status": "not_estimated",
            "estimated_peak_bytes": None,
            "available_memory_bytes": (
                available_memory_bytes
            ),
            "fits_currently_available_memory": None,
            "headroom_bytes": None,
            "estimated_fraction_of_available": None,
            "basis": "working_set_not_estimated",
        }

    else:
        comparison = (
            compare_working_set_to_available_memory(
                estimated_peak_bytes,
                snapshot,
            )
        )

    fits = comparison.get(
        "fits_currently_available_memory"
    )

    if fits is True:
        assessment = (
            "fits_currently_available_memory"
        )
        confirmation_required = False

    elif fits is False:
        assessment = (
            "exceeds_currently_available_memory"
        )
        confirmation_required = True

    else:
        assessment = "not_comparable"
        confirmation_required = None

    return {
        "analysis_strategy": analysis_strategy,
        "execution_mode": execution_mode,

        "capabilities": {
            "streaming_capable": streaming_capable,
            "materialization_required": (
                materialization_required
            ),
        },

        "working_set_estimate": {
            "estimated_peak_bytes": (
                estimated_peak_bytes
            ),
            "basis": estimate_basis,
            "confidence": estimate_confidence,
        },

        "resources": snapshot,

        "memory_comparison": comparison,

        "execution_assessment": {
            "status": assessment,
            "confirmation_required": (
                confirmation_required
            ),
        },
    }


def build_wide_temporal_execution_plan(
    *,
    estimated_peak_bytes: int | None = None,
    estimate_basis: str | None = None,
    estimate_confidence: str | None = None,
    resource_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convenience plan for the current wide-temporal analyzer.

    The analyzer itself is incremental and can consume streamed series,
    so the plan records streaming capability and that full dataset
    materialization is not an analysis requirement.

    This function still does not choose chunk sizes or estimate memory
    by itself.
    """

    return build_execution_plan(
        analysis_strategy="wide_temporal",
        execution_mode="streaming",
        estimated_peak_bytes=(
            estimated_peak_bytes
        ),
        estimate_basis=estimate_basis,
        estimate_confidence=estimate_confidence,
        streaming_capable=True,
        materialization_required=False,
        resource_snapshot=resource_snapshot,
    )


def build_wide_temporal_reference_execution_plan(
    *,
    population_count: int,
    temporal_position_count: int,
    resource_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a resource-aware plan for the current exact reference-profile
    implementation.

    The current exact analyzer streams the source but retains numeric
    observations as 64-bit doubles so exact percentiles can be produced.

    `population_count * temporal_position_count * 8` is therefore a
    structural upper bound for the retained numeric payload when every
    observation is numeric.

    Important: this is NOT a peak-working-set estimate. Python object
    overhead, per-position containers, sorting workspaces, source-reader
    buffers, DuckDB memory, and result serialization all add memory.

    The retained payload comparison is still useful:
      - if this payload alone exceeds currently available memory, the
        current exact strategy cannot safely fit as implemented;
      - if it fits, exact execution is only a candidate and peak memory
        still needs validation.

    No arbitrary dataset-size or memory-percentage threshold is used.
    """

    if population_count < 0:
        raise ValueError(
            "population_count must be >= 0"
        )

    if temporal_position_count < 1:
        raise ValueError(
            "temporal_position_count must be >= 1"
        )

    snapshot = (
        resource_snapshot
        if resource_snapshot is not None
        else inspect_memory_resources()
    )

    max_numeric_observations = (
        population_count
        * temporal_position_count
    )

    retained_numeric_payload_upper_bound_bytes = (
        max_numeric_observations
        * 8
    )

    payload_comparison = (
        compare_working_set_to_available_memory(
            retained_numeric_payload_upper_bound_bytes,
            snapshot,
        )
    )

    payload_fits = payload_comparison.get(
        "fits_currently_available_memory"
    )

    if payload_fits is True:
        exact_assessment = (
            "exact_candidate_peak_not_yet_validated"
        )
        exact_candidate = True

    elif payload_fits is False:
        exact_assessment = (
            "retained_payload_exceeds_"
            "currently_available_memory"
        )
        exact_candidate = False

    else:
        exact_assessment = (
            "resource_comparison_unavailable"
        )
        exact_candidate = None

    plan = build_execution_plan(
        analysis_strategy=(
            "wide_temporal_reference"
        ),
        execution_mode=(
            "streaming_exact_candidate"
        ),
        estimated_peak_bytes=None,
        estimate_basis=(
            "peak_working_set_not_yet_estimated"
        ),
        estimate_confidence=None,
        streaming_capable=True,
        materialization_required=True,
        resource_snapshot=snapshot,
    )

    return {
        **plan,
        "reference_statistics_plan": {
            "requested_statistics_mode": (
                "exact"
            ),
            "population_count": (
                population_count
            ),
            "temporal_position_count": (
                temporal_position_count
            ),
            "max_numeric_observations": (
                max_numeric_observations
            ),
            "retained_numeric_payload_upper_bound_bytes": (
                retained_numeric_payload_upper_bound_bytes
            ),
            "retained_payload_comparison": (
                payload_comparison
            ),
            "exact_candidate": (
                exact_candidate
            ),
            "exact_assessment": (
                exact_assessment
            ),
            "limitations": {
                "payload_is_not_peak_working_set": True,
                "runtime_overhead_not_estimated": True,
                "sorting_workspace_not_estimated": True,
                "source_buffering_not_estimated": True,
            },
        },
    }
