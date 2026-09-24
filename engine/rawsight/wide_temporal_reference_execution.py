from __future__ import annotations

from typing import Any, Callable

from rawsight.source_context import (
    SourceExecutionContext,
)
from rawsight.wide_temporal_reference import (
    WideTemporalReferenceAnalyzer,
)
from rawsight.wide_temporal_reference_artifact import (
    load_reference_artifact_manifest,
    write_reference_artifact,
)


ProgressCallback = Callable[[str], None]


def _validate_temporal_axis(
    temporal_axis: dict[str, Any],
) -> tuple[int, int]:
    """
    Validate an already established horizontal temporal axis.

    This execution module consumes structural context; it does not
    perform source detection or promote an axis itself.
    """

    if temporal_axis.get(
        "orientation"
    ) != "horizontal":
        raise ValueError(
            "Wide temporal reference execution requires "
            "a horizontal temporal axis"
        )

    start_index = temporal_axis.get(
        "start_index"
    )
    end_index = temporal_axis.get(
        "end_index"
    )

    if not isinstance(
        start_index,
        int,
    ):
        raise ValueError(
            "Temporal start_index is missing or invalid"
        )

    if not isinstance(
        end_index,
        int,
    ):
        raise ValueError(
            "Temporal end_index is missing or invalid"
        )

    if (
        start_index < 0
        or end_index < start_index
    ):
        raise ValueError(
            "Temporal column range is invalid"
        )

    return start_index, end_index


def _validate_axis_against_columns(
    column_names: list[str],
    start_index: int,
    end_index: int,
) -> None:
    if end_index >= len(
        column_names
    ):
        raise ValueError(
            "Temporal column range exceeds "
            "the dataset width"
        )


def _attach_axis_metadata(
    analysis: dict[str, Any],
    column_names: list[str],
    start_index: int,
) -> dict[str, Any]:
    """
    Enrich position-only analysis with source-axis labels.

    The analysis layer remains independent of source columns; mapping
    back to column indexes and labels belongs to execution/context.
    """

    positions = []

    for position in analysis[
        "positions"
    ]:
        axis_index = position[
            "axis_index"
        ]
        column_index = (
            start_index
            + axis_index
        )

        positions.append({
            **position,
            "column_index": (
                column_index
            ),
            "label": (
                column_names[
                    column_index
                ]
            ),
        })

    return {
        **analysis,
        "positions": positions,
    }


def _cached_result(
    file_path: str,
    temporal_axis: dict[str, Any],
) -> dict[str, Any] | None:
    artifact = (
        load_reference_artifact_manifest(
            file_path=file_path,
            temporal_axis=temporal_axis,
        )
    )

    if artifact is None:
        return None

    reference_profile = (
        artifact.get(
            "reference_profile"
        )
    )

    execution_metadata = (
        artifact.get(
            "execution_metadata"
        )
    )

    if not isinstance(
        reference_profile,
        dict,
    ):
        return None

    if not isinstance(
        execution_metadata,
        dict,
    ):
        return None

    rows_processed = (
        execution_metadata.get(
            "rows_processed"
        )
    )
    dataset_column_count = (
        execution_metadata.get(
            "dataset_column_count"
        )
    )
    temporal_column_count = (
        execution_metadata.get(
            "temporal_column_count"
        )
    )

    if not isinstance(
        rows_processed,
        int,
    ):
        return None

    if not isinstance(
        dataset_column_count,
        int,
    ):
        return None

    if not isinstance(
        temporal_column_count,
        int,
    ):
        return None

    return {
        "status": "measured",
        "analysis_kind": (
            "wide_temporal_reference_execution"
        ),
        "execution_mode": (
            "cached_exact"
        ),
        "cache_status": "hit",
        "source_scan_performed": False,
        "source_rows_scanned_this_execution": 0,
        "rows_processed": (
            rows_processed
        ),
        "dataset_column_count": (
            dataset_column_count
        ),
        "temporal_column_count": (
            temporal_column_count
        ),
        "reference_profile": (
            reference_profile
        ),
    }


def _execute_with_context(
    file_path: str,
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    progress: ProgressCallback | None,
) -> dict[str, Any]:
    start_index, end_index = (
        _validate_temporal_axis(
            temporal_axis
        )
    )

    column_names = (
        source_context.column_names
    )

    _validate_axis_against_columns(
        column_names,
        start_index,
        end_index,
    )

    temporal_column_count = (
        end_index
        - start_index
        + 1
    )

    analyzer = (
        WideTemporalReferenceAnalyzer(
            temporal_column_count
        )
    )

    cursor = (
        source_context.select_all_cursor()
    )

    rows_processed = 0

    if progress is not None:
        progress(
            "Building wide temporal "
            "reference population"
        )

    while True:
        row = cursor.fetchone()

        if row is None:
            break

        analyzer.observe_series(
            row[
                start_index:
                end_index + 1
            ]
        )

        rows_processed += 1

    if progress is not None:
        progress(
            "Calculating exact reference "
            "percentiles"
        )

    analysis = analyzer.result()

    reference_profile = (
        _attach_axis_metadata(
            analysis=analysis,
            column_names=column_names,
            start_index=start_index,
        )
    )

    cache_status = "built"

    try:
        write_reference_artifact(
            file_path=file_path,
            temporal_axis=temporal_axis,
            ordered_reference_values=(
                analyzer.ordered_reference_values()
            ),
            population_count=(
                analyzer.population_count
            ),
            statistics_mode=(
                analysis[
                    "statistics_mode"
                ]
            ),
            percentile_method=(
                analysis[
                    "percentile_method"
                ]
            ),
            reference_profile=(
                reference_profile
            ),
            execution_metadata={
                "rows_processed": (
                    rows_processed
                ),
                "dataset_column_count": (
                    len(column_names)
                ),
                "temporal_column_count": (
                    temporal_column_count
                ),
            },
        )
    except OSError:
        # Cache persistence is an optimization. A cache-write failure
        # must not invalidate a successfully calculated analysis.
        cache_status = "write_failed"

    return {
        "status": "measured",
        "analysis_kind": (
            "wide_temporal_reference_execution"
        ),
        "execution_mode": (
            "streaming_exact"
        ),
        "cache_status": (
            cache_status
        ),
        "source_scan_performed": True,
        "source_rows_scanned_this_execution": (
            rows_processed
        ),
        "rows_processed": (
            rows_processed
        ),
        "dataset_column_count": len(
            column_names
        ),
        "temporal_column_count": (
            temporal_column_count
        ),
        "reference_profile": (
            reference_profile
        ),
    }


def execute_wide_temporal_reference(
    file_path: str,
    temporal_axis: dict[str, Any],
    progress: ProgressCallback | None = None,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Return one exact dataset reference profile for a wide-temporal axis.

    A valid disposable artifact is reused before the source is scanned.
    Artifact identity includes source path, file size, modified time,
    temporal axis and artifact format version.

    On a cache miss the source is scanned once. Exact distributions are
    finalized, the reference profile is calculated, and both are stored
    in the disposable artifact for later processes.

    No dataset-size threshold or acceptance limit is encoded here.

    If a SourceExecutionContext is supplied, the caller owns its
    lifecycle. The artifact may still satisfy the request without
    scanning that context.
    """

    cached = _cached_result(
        file_path=file_path,
        temporal_axis=temporal_axis,
    )

    if cached is not None:
        if progress is not None:
            progress(
                "Reusing wide temporal "
                "reference artifact"
            )

        return cached

    if source_context is not None:
        source_context.assert_source(
            file_path
        )

        if not source_context.is_open:
            raise RuntimeError(
                "Supplied SourceExecutionContext "
                "must already be open"
            )

        return _execute_with_context(
            file_path=file_path,
            source_context=source_context,
            temporal_axis=temporal_axis,
            progress=progress,
        )

    if progress is not None:
        progress(
            "Opening wide temporal "
            "reference source"
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return _execute_with_context(
            file_path=file_path,
            source_context=owned_context,
            temporal_axis=temporal_axis,
            progress=progress,
        )
