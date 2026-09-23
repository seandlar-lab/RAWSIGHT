from __future__ import annotations

from typing import Any, Callable

from rawsight.source_context import (
    SourceExecutionContext,
)
from rawsight.wide_temporal_reference import (
    WideTemporalReferenceAnalyzer,
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


def _execute_with_context(
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

    return {
        "status": "measured",
        "analysis_kind": (
            "wide_temporal_reference_execution"
        ),
        "execution_mode": (
            "streaming_exact"
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
    Build one exact dataset reference profile for a wide-temporal axis.

    The source is scanned once. Counts and sums are accumulated during
    that scan. Numeric observations are retained compactly by the
    analysis layer because exact percentiles require the distribution.

    No dataset-size threshold or acceptance limit is encoded here.

    If a SourceExecutionContext is supplied, the caller owns its
    lifecycle and the already-open source is reused. Otherwise this
    function opens and deterministically closes its own source context.
    """

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
            source_context=owned_context,
            temporal_axis=temporal_axis,
            progress=progress,
        )
