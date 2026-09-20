from __future__ import annotations

from typing import Any, Callable

from rawsight.execution_preflight import (
    build_preflight_report,
    run_execution_probe,
)
from rawsight.resource_assessment import (
    inspect_memory_resources,
)
from rawsight.source_context import (
    SourceExecutionContext,
)
from rawsight.wide_temporal import (
    WideTemporalAnalyzer,
)
from rawsight.wide_temporal_series import (
    analyze_wide_temporal_series_observation,
)


ProgressCallback = Callable[[str], None]


def _validate_temporal_axis(
    temporal_axis: dict[str, Any],
) -> tuple[int, int]:
    """
    Validate an already detected horizontal temporal axis.
    """

    if temporal_axis.get(
        "orientation"
    ) != "horizontal":
        raise ValueError(
            "Wide temporal execution requires "
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
    if end_index >= len(column_names):
        raise ValueError(
            "Temporal column range exceeds "
            "the dataset width"
        )


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

    cursor = (
        source_context.select_all_cursor()
    )

    analyzer = WideTemporalAnalyzer()
    rows_processed = 0

    if progress is not None:
        progress(
            "Analyzing wide temporal values"
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

    return {
        "status": "measured",
        "execution_mode": "streaming",
        "rows_processed": rows_processed,
        "dataset_column_count": len(
            column_names
        ),
        "temporal_column_count": (
            temporal_column_count
        ),
        "analysis": analyzer.result(),
    }


def probe_wide_temporal_execution(
    file_path: str,
    temporal_axis: dict[str, Any],
) -> dict[str, Any]:
    """
    Probe the real wide-temporal execution path.

    One complete row is the atomic series unit for a horizontal
    wide-temporal dataset. The probe exercises the full temporal
    width without inventing a sample percentage, byte limit, or
    arbitrary number of rows.

    The result is observational, not a guarantee. Source readers may
    buffer differently during a full run.
    """

    start_index, end_index = (
        _validate_temporal_axis(
            temporal_axis
        )
    )

    def _probe() -> dict[str, Any]:
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

            row = cursor.fetchone()

            analyzer = WideTemporalAnalyzer()

            if row is not None:
                analyzer.observe_series(
                    row[
                        start_index:
                        end_index + 1
                    ]
                )

            return {
                "row_observed": (
                    row is not None
                ),
                "dataset_column_count": len(
                    column_names
                ),
                "temporal_column_count": (
                    end_index
                    - start_index
                    + 1
                ),
                "analysis": (
                    analyzer.result()
                ),
            }

    probe_result, measurement = (
        run_execution_probe(
            _probe
        )
    )

    return {
        "probe_result": probe_result,
        "preflight": build_preflight_report(
            execution_mode="streaming",
            streaming_capable=True,
            materialization_required=False,
            probe_measurement=measurement,
        ),
        "machine_resources": (
            inspect_memory_resources()
        ),
        "limitations": {
            "full_run_not_executed": True,
            "probe_is_one_complete_series": True,
            "source_buffering_may_change": True,
            "result_is_observational": True,
        },
    }


def execute_wide_temporal_analysis(
    file_path: str,
    temporal_axis: dict[str, Any],
    progress: ProgressCallback | None = None,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Execute wide-temporal analysis incrementally.

    If a SourceExecutionContext is supplied, the caller owns its
    lifecycle and the already-open source is reused.

    If no context is supplied, this function creates and closes its own
    source context.

    Exactly one source row is presented to the analyzer at a time. No
    dataset-size threshold, batch-size threshold, or acceptance limit
    is encoded here.
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
            source_context,
            temporal_axis,
            progress,
        )

    if progress is not None:
        progress(
            "Opening wide temporal source"
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return _execute_with_context(
            owned_context,
            temporal_axis,
            progress,
        )


def execute_wide_temporal_analysis_measured(
    file_path: str,
    temporal_axis: dict[str, Any],
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """
    Execute the full analysis and record process-memory observations
    around the execution.

    This validates the streaming design. It is not itself a preflight,
    because the full analysis has already run.
    """

    def _run() -> dict[str, Any]:
        return execute_wide_temporal_analysis(
            file_path,
            temporal_axis,
            progress=progress,
        )

    result, measurement = (
        run_execution_probe(
            _run
        )
    )

    return {
        "result": result,
        "execution_measurement": (
            measurement
        ),
    }

def _json_safe_value(
    value: object,
) -> object:
    """
    Keep JSON-native scalar values unchanged and stringify other source
    values such as dates/decimals. This preserves source information
    without assigning additional semantics.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    return str(value)


def build_wide_temporal_series_result(
    column_names: list[str],
    row: tuple | list,
    temporal_axis: dict[str, Any],
    series_index: int,
    include_points: bool = False,
) -> dict[str, Any]:
    """
    Build one structure-aware series result from one source row.

    Every column outside the detected horizontal temporal axis is treated
    as a descriptor candidate. No descriptor names or domain-specific
    fields are hard-coded.
    """

    start_index, end_index = (
        _validate_temporal_axis(
            temporal_axis
        )
    )

    _validate_axis_against_columns(
        column_names,
        start_index,
        end_index,
    )

    if len(row) != len(column_names):
        raise ValueError(
            "Source row width does not match "
            "the detected dataset width"
        )

    descriptor_indexes = [
        index
        for index in range(
            len(column_names)
        )
        if not (
            start_index
            <= index
            <= end_index
        )
    ]

    temporal_values = row[
        start_index:
        end_index + 1
    ]

    observation = (
        analyze_wide_temporal_series_observation(
            temporal_values
        )
    )

    result: dict[str, Any] = {
        "series_index": series_index,
        "descriptors": [
            {
                "column_index": index,
                "column_name": (
                    column_names[index]
                ),
                "value": _json_safe_value(
                    row[index]
                ),
            }
            for index in descriptor_indexes
        ],
        "classification": observation[
            "classification"
        ],
        "temporal_value_count": observation[
            "temporal_value_count"
        ],
        "numeric_value_count": observation[
            "numeric_value_count"
        ],
        "missing_value_count": observation[
            "missing_value_count"
        ],
        "non_numeric_value_count": observation[
            "non_numeric_value_count"
        ],
        "positive_transition_count": observation[
            "positive_transition_count"
        ],
        "negative_transition_count": observation[
            "negative_transition_count"
        ],
        "unchanged_transition_count": observation[
            "unchanged_transition_count"
        ],
        "largest_positive_change": observation[
            "largest_positive_change"
        ],
        "largest_negative_change": observation[
            "largest_negative_change"
        ],
    }

    if include_points:
        result["temporal_points"] = [
            {
                "axis_index": axis_index,
                "column_index": (
                    start_index
                    + axis_index
                ),
                "label": column_names[
                    start_index
                    + axis_index
                ],
                "value": _json_safe_value(
                    value
                ),
            }
            for axis_index, value
            in enumerate(
                temporal_values
            )
        ]

        result[
            "negative_transitions"
        ] = [
            {
                **transition,
                "from_column_index": (
                    start_index
                    + transition[
                        "from_index"
                    ]
                ),
                "to_column_index": (
                    start_index
                    + transition[
                        "to_index"
                    ]
                ),
                "from_label": column_names[
                    start_index
                    + transition[
                        "from_index"
                    ]
                ],
                "to_label": column_names[
                    start_index
                    + transition[
                        "to_index"
                    ]
                ],
            }
            for transition in observation[
                "negative_transitions"
            ]
        ]

    return result


def _execute_wide_temporal_series_page_with_context(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    classification: str | None,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """
    Return one caller-sized page of matching series.

    The function streams source rows and retains at most `limit` results.
    Page size is supplied by the caller; there is no hidden dataset-size
    acceptance threshold.
    """

    if offset < 0:
        raise ValueError(
            "offset must be >= 0"
        )

    if limit < 1:
        raise ValueError(
            "limit must be >= 1"
        )

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

    cursor = (
        source_context.select_all_cursor()
    )

    results: list[dict[str, Any]] = []
    matching_seen = 0
    rows_scanned = 0
    has_more = False

    while True:
        row = cursor.fetchone()

        if row is None:
            break

        series_index = rows_scanned
        rows_scanned += 1

        series_result = (
            build_wide_temporal_series_result(
                column_names=column_names,
                row=row,
                temporal_axis=temporal_axis,
                series_index=series_index,
                include_points=False,
            )
        )

        if (
            classification is not None
            and series_result[
                "classification"
            ]
            != classification
        ):
            continue

        if matching_seen < offset:
            matching_seen += 1
            continue

        if len(results) < limit:
            results.append(
                series_result
            )
            matching_seen += 1
            continue

        has_more = True
        break

    return {
        "status": "measured",
        "execution_mode": "streaming",
        "classification_filter": (
            classification
        ),
        "offset": offset,
        "limit": limit,
        "returned_count": len(
            results
        ),
        "next_offset": (
            offset + len(results)
            if has_more
            else None
        ),
        "has_more": has_more,
        "rows_scanned": rows_scanned,
        "series": results,
    }


def execute_wide_temporal_series_page(
    file_path: str,
    temporal_axis: dict[str, Any],
    classification: str | None,
    offset: int,
    limit: int,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Explore wide-temporal series as a paged streaming result.

    Filtering uses observation classifications only. No business meaning
    is assigned to any classification.
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

        return (
            _execute_wide_temporal_series_page_with_context(
                source_context=source_context,
                temporal_axis=temporal_axis,
                classification=classification,
                offset=offset,
                limit=limit,
            )
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return (
            _execute_wide_temporal_series_page_with_context(
                source_context=owned_context,
                temporal_axis=temporal_axis,
                classification=classification,
                offset=offset,
                limit=limit,
            )
        )


def _execute_wide_temporal_series_detail_with_context(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    series_index: int,
) -> dict[str, Any]:
    if series_index < 0:
        raise ValueError(
            "series_index must be >= 0"
        )

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

    cursor = (
        source_context.select_all_cursor()
    )

    current_index = 0

    while True:
        row = cursor.fetchone()

        if row is None:
            raise IndexError(
                "series_index exceeds "
                "available source rows"
            )

        if current_index == series_index:
            return (
                build_wide_temporal_series_result(
                    column_names=column_names,
                    row=row,
                    temporal_axis=temporal_axis,
                    series_index=series_index,
                    include_points=True,
                )
            )

        current_index += 1


def execute_wide_temporal_series_detail(
    file_path: str,
    temporal_axis: dict[str, Any],
    series_index: int,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Return one complete series for drill-down.

    The source is streamed until the requested source-row ordinal is
    reached. Only that series is materialized as temporal points.
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

        return (
            _execute_wide_temporal_series_detail_with_context(
                source_context=source_context,
                temporal_axis=temporal_axis,
                series_index=series_index,
            )
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return (
            _execute_wide_temporal_series_detail_with_context(
                source_context=owned_context,
                temporal_axis=temporal_axis,
                series_index=series_index,
            )
        )

