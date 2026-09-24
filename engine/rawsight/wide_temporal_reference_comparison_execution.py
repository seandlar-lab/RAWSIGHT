from __future__ import annotations

from typing import Any, Callable

from rawsight.source_context import (
    SourceExecutionContext,
)
from rawsight.wide_temporal_reference_artifact import (
    load_reference_artifact,
)
from rawsight.wide_temporal_reference_comparison import (
    compare_wide_temporal_series_to_reference,
)
from rawsight.wide_temporal_reference_execution import (
    execute_wide_temporal_reference,
)


ProgressCallback = Callable[[str], None]


def _validate_temporal_axis(
    temporal_axis: dict[str, Any],
) -> tuple[int, int]:
    if temporal_axis.get(
        "orientation"
    ) != "horizontal":
        raise ValueError(
            "Wide temporal reference comparison "
            "requires a horizontal temporal axis"
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

    return (
        start_index,
        end_index,
    )


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


def _ensure_reference_artifact(
    file_path: str,
    temporal_axis: dict[str, Any],
    progress: ProgressCallback | None,
) -> tuple[
    dict[str, Any],
    str,
]:
    """
    Return a full exact reference artifact.

    If no valid artifact exists, build it through the established
    reference execution path and then load the finalized distributions.

    A cache miss therefore pays the one-time reference build cost.
    Subsequent comparisons reuse the artifact across Python processes.
    """

    artifact = load_reference_artifact(
        file_path=file_path,
        temporal_axis=temporal_axis,
    )

    if artifact is not None:
        return (
            artifact,
            "hit",
        )

    if progress is not None:
        progress(
            "Reference artifact not found; "
            "building exact reference"
        )

    reference_execution = (
        execute_wide_temporal_reference(
            file_path=file_path,
            temporal_axis=temporal_axis,
            progress=progress,
        )
    )

    artifact = load_reference_artifact(
        file_path=file_path,
        temporal_axis=temporal_axis,
    )

    if artifact is None:
        raise RuntimeError(
            "Reference execution completed but "
            "no reusable reference artifact is available"
        )

    cache_status = (
        "built"
        if reference_execution.get(
            "cache_status"
        )
        in (
            "built",
            "write_failed",
        )
        else "hit"
    )

    return (
        artifact,
        cache_status,
    )


def _read_selected_series(
    file_path: str,
    temporal_axis: dict[str, Any],
    series_index: int,
    progress: ProgressCallback | None,
) -> tuple[
    list[str],
    tuple[object, ...],
    int,
]:
    """
    Read only as far as the selected source-row ordinal.

    `series_index` keeps the same semantics as Series Explorer:
    it is the zero-based source row ordinal, not a semantic identifier.
    """

    if series_index < 0:
        raise ValueError(
            "series_index must be >= 0"
        )

    start_index, end_index = (
        _validate_temporal_axis(
            temporal_axis
        )
    )

    if progress is not None:
        progress(
            "Reading selected wide temporal series"
        )

    with SourceExecutionContext(
        file_path
    ) as source_context:
        column_names = (
            source_context.column_names
        )

        _validate_axis_against_columns(
            column_names,
            start_index,
            end_index,
        )

        cursor = (
            source_context.select_all_cursor()
        )

        rows_scanned = 0

        while True:
            row = cursor.fetchone()

            if row is None:
                raise IndexError(
                    "series_index exceeds "
                    "available source rows"
                )

            current_index = (
                rows_scanned
            )
            rows_scanned += 1

            if (
                current_index
                == series_index
            ):
                temporal_values = tuple(
                    row[
                        start_index:
                        end_index + 1
                    ]
                )

                return (
                    column_names,
                    temporal_values,
                    rows_scanned,
                )


def _attach_axis_metadata(
    comparison: dict[str, Any],
    column_names: list[str],
    start_index: int,
) -> dict[str, Any]:
    positions = []

    for position in comparison[
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
        **comparison,
        "positions": positions,
    }


def execute_wide_temporal_reference_comparison(
    file_path: str,
    temporal_axis: dict[str, Any],
    series_index: int,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Compare one selected wide-temporal series with the exact dataset
    reference population.

    Execution flow:
      1. reuse a valid reference artifact, or build it once if missing
      2. read only as far as the selected source row
      3. compute exact midrank percentile position and signed distance
         from the reference median for every temporal position

    The result remains observational. It does not label a deviation as
    an anomaly, error, or domain problem.

    On a reference-cache hit the source is not rescanned for the
    population. Only the selected row path is read.
    """

    start_index, end_index = (
        _validate_temporal_axis(
            temporal_axis
        )
    )

    artifact, reference_cache_status = (
        _ensure_reference_artifact(
            file_path=file_path,
            temporal_axis=temporal_axis,
            progress=progress,
        )
    )

    ordered_reference_values = (
        artifact.get(
            "ordered_reference_values"
        )
    )

    if not isinstance(
        ordered_reference_values,
        tuple,
    ):
        raise RuntimeError(
            "Reference artifact does not contain "
            "ordered reference distributions"
        )

    expected_position_count = (
        end_index
        - start_index
        + 1
    )

    if (
        len(ordered_reference_values)
        != expected_position_count
    ):
        raise RuntimeError(
            "Reference artifact width does not match "
            "the temporal axis"
        )

    (
        column_names,
        temporal_values,
        selected_rows_scanned,
    ) = _read_selected_series(
        file_path=file_path,
        temporal_axis=temporal_axis,
        series_index=series_index,
        progress=progress,
    )

    comparison = (
        compare_wide_temporal_series_to_reference(
            values=temporal_values,
            ordered_reference_values=(
                ordered_reference_values
            ),
        )
    )

    comparison_with_axis = (
        _attach_axis_metadata(
            comparison=comparison,
            column_names=column_names,
            start_index=start_index,
        )
    )

    return {
        "status": "measured",
        "analysis_kind": (
            "wide_temporal_reference_comparison_execution"
        ),
        "execution_mode": (
            "cached_reference_exact_comparison"
        ),
        "series_index": series_index,
        "reference_cache_status": (
            reference_cache_status
        ),
        "reference_population_count": (
            artifact.get(
                "population_count"
            )
        ),
        "reference_statistics_mode": (
            artifact.get(
                "statistics_mode"
            )
        ),
        "reference_percentile_method": (
            artifact.get(
                "percentile_method"
            )
        ),
        "selected_series_rows_scanned": (
            selected_rows_scanned
        ),
        "temporal_column_count": (
            expected_position_count
        ),
        "comparison": (
            comparison_with_axis
        ),
        "limitations": {
            "series_index_is_source_row_ordinal": True,
            "cache_miss_builds_reference_before_selected_series_read": True,
            "source_and_artifact_are_not_a_transactional_snapshot": True,
        },
    }
