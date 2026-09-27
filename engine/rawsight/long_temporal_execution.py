from typing import Iterator

from rawsight.long_temporal import (
    analyze_long_temporal_axis,
)
from rawsight.source_context import (
    SourceExecutionContext,
)


def _quote_identifier(
    name: str,
) -> str:
    return '"' + name.replace('"', '""') + '"'


def _stream_column_values(
    connection,
    column_name: str,
    *,
    batch_size: int,
) -> Iterator[object]:
    """
    Stream one column from the open source relation.

    Rows are consumed in batches and are never materialized as
    one complete Python collection.
    """

    if batch_size < 1:
        raise ValueError(
            "batch_size must be positive"
        )

    column = _quote_identifier(
        column_name
    )

    cursor = connection.execute(
        f"""
        SELECT {column}
        FROM rawsight_source
        """
    )

    while True:
        rows = cursor.fetchmany(
            batch_size
        )

        if not rows:
            break

        for row in rows:
            yield row[0]


def execute_long_temporal_axis_analysis(
    file_path: str,
    temporal_axis: dict,
    *,
    source_context: (
        SourceExecutionContext | None
    ) = None,
    batch_size: int = 65536,
    interval_frequency_limit: int | None = None,
    largest_positive_interval_limit: int = 10,
) -> dict:
    """
    Execute streaming analysis of one detected vertical
    temporal axis.

    No sorting is performed here.

    The order analyzed is the order delivered by the source
    relation. This function deliberately does not claim that
    relation scan order is a canonical or physically guaranteed
    source order.
    """

    if temporal_axis.get(
        "orientation"
    ) != "vertical":
        raise ValueError(
            "Long temporal execution requires "
            "a vertical temporal axis"
        )

    temporal_column_index = (
        temporal_axis.get(
            "sequence_index"
        )
    )

    if not isinstance(
        temporal_column_index,
        int,
    ):
        raise ValueError(
            "Temporal axis sequence_index "
            "must be an integer"
        )

    if source_context is None:
        with SourceExecutionContext(
            file_path
        ) as owned_context:
            return execute_long_temporal_axis_analysis(
                file_path=file_path,
                temporal_axis=temporal_axis,
                source_context=owned_context,
                batch_size=batch_size,
                interval_frequency_limit=(
                    interval_frequency_limit
                ),
                largest_positive_interval_limit=(
                    largest_positive_interval_limit
                ),
            )
    source_context.assert_source(
        file_path
    )

    if not source_context.is_open:
        raise RuntimeError(
        "Supplied SourceExecutionContext "
        "must already be open"
        )

    column_names = (
        source_context.column_names
    )

    if not (
        0
        <= temporal_column_index
        < len(column_names)
    ):
        raise ValueError(
            "Temporal column index is outside "
            "the source schema"
        )

    temporal_column_name = (
        column_names[
            temporal_column_index
        ]
    )

    connection = (
        source_context.require_connection()
    )

    values = _stream_column_values(
        connection,
        temporal_column_name,
        batch_size=batch_size,
    )

    analysis = analyze_long_temporal_axis(
        values,
        interval_frequency_limit=(
            interval_frequency_limit
        ),
        largest_positive_interval_limit=(
            largest_positive_interval_limit
        ),
    )

    return {
        "mode": (
            "streaming_long_temporal_axis"
        ),
        "temporal_column_index": (
            temporal_column_index
        ),
        "temporal_column_name": (
            temporal_column_name
        ),
        "batch_size": batch_size,

        # This is intentionally descriptive rather than
        # claiming canonical/source ordering.
        "observed_order_basis": (
            "relation_scan"
        ),
        "canonical_order_established": (
            False
        ),

        "analysis": analysis,

        "limitations": [
            (
                "No sorting was performed."
            ),
            (
                "Observed relation scan order is analyzed "
                "but is not asserted to be canonical order."
            ),
        ],
    }