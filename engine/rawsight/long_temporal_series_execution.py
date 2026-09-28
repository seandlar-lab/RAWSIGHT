from __future__ import annotations

from typing import Any

from rawsight.long_temporal_series import (
    build_temporal_value_projection,
    build_time_bucket_projection,
    temporal_to_json,
)
from rawsight.source_context import (
    SourceExecutionContext,
)


NUMERIC_TYPE_PREFIXES = (
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "FLOAT",
    "DOUBLE",
    "DECIMAL",
)

TEMPORAL_TYPE_PREFIXES = (
    "DATE",
    "TIME",
    "TIMESTAMP",
)


def _quote_identifier(
    name: str,
) -> str:
    return (
        '"'
        + name.replace(
            '"',
            '""',
        )
        + '"'
    )


def _is_numeric_type(
    data_type: str,
) -> bool:
    return data_type.upper().startswith(
        NUMERIC_TYPE_PREFIXES
    )


def _is_temporal_type(
    data_type: str,
) -> bool:
    return data_type.upper().startswith(
        TEMPORAL_TYPE_PREFIXES
    )


def _validate_temporal_axis(
    temporal_axis: dict[str, Any],
    column_names: list[str],
) -> int:
    """
    Validate an already detected vertical temporal axis.

    Detection decides orientation. This execution path does
    not attempt to rediscover the dataset structure.
    """

    if temporal_axis.get(
        "orientation"
    ) != "vertical":
        raise ValueError(
            "Long temporal series execution requires "
            "a vertical temporal axis"
        )

    sequence_index = (
        temporal_axis.get(
            "sequence_index"
        )
    )

    if not isinstance(
        sequence_index,
        int,
    ):
        raise ValueError(
            "Temporal sequence_index is missing "
            "or invalid"
        )

    if (
        sequence_index < 0
        or sequence_index
        >= len(column_names)
    ):
        raise ValueError(
            "Temporal sequence_index exceeds "
            "the dataset width"
        )

    return sequence_index


def _build_temporal_expression(
    column_name: str,
    data_type: str,
    temporal_axis: dict[str, Any],
) -> str:
    """
    Build parsing from detected structure.

    A technically temporal source column is cast directly.
    Otherwise the format detected during normalization is
    used when available.

    No dataset-specific temporal format is hard-coded here.
    """

    column = _quote_identifier(
        column_name
    )

    if _is_temporal_type(
        data_type
    ):
        return (
            f"TRY_CAST("
            f"{column} AS TIMESTAMP"
            f")"
        )

    detected_format = (
        temporal_axis.get(
            "format"
        )
    )

    if (
        isinstance(
            detected_format,
            str,
        )
        and detected_format
    ):
        escaped_format = (
            detected_format.replace(
                "'",
                "''",
            )
        )

        return (
            "TRY_STRPTIME("
            f"CAST({column} AS VARCHAR), "
            f"'{escaped_format}'"
            ")"
        )

    return (
        f"TRY_CAST("
        f"{column} AS TIMESTAMP"
        f")"
    )


def _execute_with_context(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    value_column_name: str,
    point_limit: int,
) -> dict[str, Any]:
    if point_limit < 2:
        raise ValueError(
            "point_limit must be at least 2"
        )

    column_names = (
        source_context.column_names
    )

    column_types = (
        source_context.column_types
    )

    temporal_column_index = (
        _validate_temporal_axis(
            temporal_axis,
            column_names,
        )
    )

    temporal_column_name = (
        column_names[
            temporal_column_index
        ]
    )

    temporal_column_type = (
        column_types[
            temporal_column_index
        ]
    )

    if (
        value_column_name
        not in column_names
    ):
        raise ValueError(
            "Value column not found: "
            f"{value_column_name}"
        )

    value_column_index = (
        column_names.index(
            value_column_name
        )
    )

    if (
        value_column_index
        == temporal_column_index
    ):
        raise ValueError(
            "The temporal column cannot also be "
            "the selected value column"
        )

    value_column_type = (
        column_types[
            value_column_index
        ]
    )

    if not _is_numeric_type(
        value_column_type
    ):
        raise ValueError(
            "Selected value column is not "
            "technically numeric: "
            f"{value_column_name} "
            f"({value_column_type})"
        )

    connection = (
        source_context.require_connection()
    )

    view = _quote_identifier(
        source_context.view_name
    )

    temporal_expression = (
        _build_temporal_expression(
            temporal_column_name,
            temporal_column_type,
            temporal_axis,
        )
    )

    value_column = (
        _quote_identifier(
            value_column_name
        )
    )

    normalized_sql = f"""
        WITH normalized AS (
            SELECT
                {temporal_expression}
                    AS parsed_time,

                TRY_CAST(
                    {value_column}
                    AS DOUBLE
                ) AS value

            FROM {view}
        ),

        valid AS (
            SELECT
                parsed_time,
                value

            FROM normalized

            WHERE parsed_time IS NOT NULL
              AND value IS NOT NULL
              AND ISFINITE(value)
        )
    """

    bounds = connection.execute(
        normalized_sql
        + """
        SELECT
            COUNT(*) AS usable_observation_count,
            MIN(parsed_time),
            MAX(parsed_time),
            MIN(EPOCH(parsed_time)),
            MAX(EPOCH(parsed_time))

        FROM valid
        """
    ).fetchone()

    (
        usable_observation_count,
        first_observation,
        last_observation,
        first_epoch,
        last_epoch,
    ) = bounds

    source_result = {
        "usable_observation_count": int(
            usable_observation_count
        ),
        "first_observation": (
            temporal_to_json(
                first_observation
            )
        ),
        "last_observation": (
            temporal_to_json(
                last_observation
            )
        ),
    }

    if (
        usable_observation_count == 0
        or first_observation is None
        or last_observation is None
    ):
        return {
            "status": (
                "insufficient_data"
            ),
            "result_kind": (
                "long_temporal_series_projection"
            ),

            "temporal_column_index": (
                temporal_column_index
            ),
            "temporal_column_name": (
                temporal_column_name
            ),

            "value_column_index": (
                value_column_index
            ),
            "value_column_name": (
                value_column_name
            ),
            "value_technical_type": (
                value_column_type
            ),

            "source": source_result,

            "display_projection": {
                "mode": "empty",
                "point_limit": (
                    point_limit
                ),
                "point_count": 0,
                "bucket_width_seconds": (
                    None
                ),
                "points": [],
            },

            "execution": {
                "mode": (
                    "duckdb_aggregate_projection"
                ),
                "temporal_display_order": (
                    "parsed_time_ascending"
                ),
                "source_order_used": False,
                "point_limit": (
                    point_limit
                ),
            },
        }

    if (
        usable_observation_count
        <= point_limit
    ):
        rows = connection.execute(
            normalized_sql
            + """
            SELECT
                parsed_time,
                COUNT(*) AS row_count,
                AVG(value),
                MIN(value),
                MAX(value)

            FROM valid

            GROUP BY parsed_time
            ORDER BY parsed_time
            """
        ).fetchall()

        display_projection = (
            build_temporal_value_projection(
                rows=rows,
                point_limit=point_limit,
            )
        )

    else:
        span_seconds = (
            float(last_epoch)
            - float(first_epoch)
        )

        if span_seconds <= 0:
            rows = connection.execute(
                normalized_sql
                + """
                SELECT
                    parsed_time,
                    COUNT(*) AS row_count,
                    AVG(value),
                    MIN(value),
                    MAX(value)

                FROM valid

                GROUP BY parsed_time
                ORDER BY parsed_time
                """
            ).fetchall()

            display_projection = (
                build_temporal_value_projection(
                    rows=rows,
                    point_limit=point_limit,
                )
            )

        else:
            bucket_width_seconds = (
                span_seconds
                / point_limit
            )

            bucket_rows = (
                connection.execute(
                    normalized_sql
                    + """
                    SELECT
                        LEAST(
                            ?,
                            GREATEST(
                                0,
                                CAST(
                                    FLOOR(
                                        (
                                            EPOCH(
                                                parsed_time
                                            )
                                            - ?
                                        )
                                        / ?
                                    )
                                    AS INTEGER
                                )
                            )
                        ) AS bucket_index,

                        COUNT(*) AS row_count,
                        AVG(value),
                        MIN(value),
                        MAX(value)

                    FROM valid

                    GROUP BY bucket_index
                    ORDER BY bucket_index
                    """,
                    [
                        point_limit - 1,
                        float(first_epoch),
                        bucket_width_seconds,
                    ],
                ).fetchall()
            )

            display_projection = (
                build_time_bucket_projection(
                    bucket_rows=bucket_rows,
                    first_observation=(
                        first_observation
                    ),
                    bucket_width_seconds=(
                        bucket_width_seconds
                    ),
                    point_limit=point_limit,
                )
            )

    return {
        "status": "measured",

        "result_kind": (
            "long_temporal_series_projection"
        ),

        "temporal_column_index": (
            temporal_column_index
        ),
        "temporal_column_name": (
            temporal_column_name
        ),

        "value_column_index": (
            value_column_index
        ),
        "value_column_name": (
            value_column_name
        ),
        "value_technical_type": (
            value_column_type
        ),

        "source": source_result,

        "display_projection": (
            display_projection
        ),

        "execution": {
            "mode": (
                "duckdb_aggregate_projection"
            ),

            # Display projection intentionally orders by
            # normalized temporal value. This is separate
            # from the observed source/relation order used
            # by continuity analysis.
            "temporal_display_order": (
                "parsed_time_ascending"
            ),

            "source_order_used": False,

            # Resource/output bound only. It does not limit
            # analytical observation processing.
            "point_limit": (
                point_limit
            ),

            "limitations": [
                (
                    "Display projection is not "
                    "the analytical observation series."
                ),
                (
                    "Time buckets may aggregate "
                    "multiple source observations."
                ),
            ],
        },
    }


def execute_long_temporal_series_projection(
    file_path: str,
    temporal_axis: dict[str, Any],
    value_column_name: str,
    point_limit: int = 1000,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Build a bounded visual projection for one selected value
    column in a detected long-temporal dataset.

    Detection decides that this is a vertical temporal source.
    This function does not rediscover orientation.

    The point limit is a rendering/output resource bound.
    It is not an analytical sampling threshold.
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
            value_column_name=(
                value_column_name
            ),
            point_limit=point_limit,
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return _execute_with_context(
            source_context=owned_context,
            temporal_axis=temporal_axis,
            value_column_name=(
                value_column_name
            ),
            point_limit=point_limit,
        )