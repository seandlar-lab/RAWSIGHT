from __future__ import annotations

from typing import Any, Callable

import duckdb

from rawsight.datasets import open_dataset
from rawsight.execution_preflight import (
    build_preflight_report,
    run_execution_probe,
)
from rawsight.resource_assessment import inspect_memory_resources
from rawsight.wide_temporal import WideTemporalAnalyzer


ProgressCallback = Callable[[str], None]


def _validate_temporal_axis(
    temporal_axis: dict[str, Any],
) -> tuple[int, int]:
    """Validate an already detected horizontal temporal axis."""

    if temporal_axis.get("orientation") != "horizontal":
        raise ValueError(
            "Wide temporal execution requires "
            "a horizontal temporal axis"
        )

    start_index = temporal_axis.get("start_index")
    end_index = temporal_axis.get("end_index")

    if not isinstance(start_index, int):
        raise ValueError(
            "Temporal start_index is missing or invalid"
        )

    if not isinstance(end_index, int):
        raise ValueError(
            "Temporal end_index is missing or invalid"
        )

    if start_index < 0 or end_index < start_index:
        raise ValueError(
            "Temporal column range is invalid"
        )

    return start_index, end_index


def _open_stream(
    connection: duckdb.DuckDBPyConnection,
    file_path: str,
) -> tuple[Any, list[str]]:
    """
    Open the dataset and expose it through a temporary view.

    SELECT * is intentional here: rows are fetched incrementally and
    the executor needs original positional column order so the detected
    temporal range can be sliced without generating a large per-column
    SQL expression.
    """

    relation = open_dataset(
        connection,
        file_path,
    )

    column_names = list(relation.columns)

    relation.create_view(
        "rawsight_wide_temporal_source",
        replace=True,
    )

    cursor = connection.execute(
        "SELECT * FROM rawsight_wide_temporal_source"
    )

    return cursor, column_names


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


def probe_wide_temporal_execution(
    file_path: str,
    temporal_axis: dict[str, Any],
) -> dict[str, Any]:
    """
    Probe the real wide-temporal execution path.

    One complete row is the atomic series unit for a horizontal
    wide-temporal dataset. The probe therefore exercises the full
    temporal width without inventing a sample percentage, byte limit,
    or arbitrary number of rows.

    The result is observational, not a guarantee. Source readers may
    buffer differently during a full run.
    """

    start_index, end_index = _validate_temporal_axis(
        temporal_axis
    )

    def _probe() -> dict[str, Any]:
        connection = duckdb.connect()

        try:
            cursor, column_names = _open_stream(
                connection,
                file_path,
            )

            _validate_axis_against_columns(
                column_names,
                start_index,
                end_index,
            )

            row = cursor.fetchone()

            analyzer = WideTemporalAnalyzer()

            if row is not None:
                analyzer.observe_series(
                    row[start_index:end_index + 1]
                )

            return {
                "row_observed": row is not None,
                "dataset_column_count": len(
                    column_names
                ),
                "temporal_column_count": (
                    end_index - start_index + 1
                ),
                "analysis": analyzer.result(),
            }

        finally:
            connection.close()

    probe_result, measurement = run_execution_probe(
        _probe
    )

    return {
        "probe_result": probe_result,
        "preflight": build_preflight_report(
            execution_mode="streaming",
            streaming_capable=True,
            materialization_required=False,
            probe_measurement=measurement,
        ),
        "machine_resources": inspect_memory_resources(),
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
) -> dict[str, Any]:
    """
    Execute wide-temporal analysis incrementally.

    Exactly one source row is presented to the analyzer at a time.
    The analyzer therefore does not accumulate the dataset itself in
    Python memory.

    No dataset-size threshold, batch-size threshold, or acceptance
    limit is encoded here.
    """

    start_index, end_index = _validate_temporal_axis(
        temporal_axis
    )

    if progress is not None:
        progress("Opening wide temporal source")

    connection = duckdb.connect()

    try:
        cursor, column_names = _open_stream(
            connection,
            file_path,
        )

        _validate_axis_against_columns(
            column_names,
            start_index,
            end_index,
        )

        temporal_column_count = (
            end_index - start_index + 1
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
                row[start_index:end_index + 1]
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

    finally:
        connection.close()


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

    result, measurement = run_execution_probe(
        _run
    )

    return {
        "result": result,
        "execution_measurement": measurement,
    }
