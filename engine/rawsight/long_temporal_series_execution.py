from __future__ import annotations

from typing import Any

from rawsight.long_temporal_series import (
    build_temporal_value_projection,
    build_time_bucket_extrema_projection,
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
    """
    Build one bounded temporal display projection.

    Detection and structural normalization have already
    established the vertical temporal axis.

    Small temporal series are represented directly as
    temporal-value groups.

    Large temporal series are reduced with an
    extrema-preserving display projection. Each time bucket
    may contribute representative source observations for:

    - first
    - minimum
    - maximum
    - last

    The display point limit is a rendering/output resource
    bound. It is not an analytical threshold.
    """

    if point_limit < 4:
        raise ValueError(
            "point_limit must be at least 4 "
            "for temporal display projection"
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

    usable_observation_count = int(
        usable_observation_count
    )

    source_result = {
        "usable_observation_count": (
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
            "source": (
                source_result
            ),
            "display_projection": {
                "mode": "empty",
                "point_limit": (
                    point_limit
                ),
                "point_count": 0,
                "bucket_count": None,
                "bucket_width_seconds": (
                    None
                ),
                "points": [],
            },
            "execution": {
                "mode": (
                    "duckdb_temporal_display_projection"
                ),
                "temporal_display_order": (
                    "parsed_time_ascending"
                ),
                "source_order_used": False,
                "point_limit": (
                    point_limit
                ),
                "limitations": [
                    (
                        "Display projection is not "
                        "the analytical observation series."
                    ),
                ],
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
                AVG(value) AS mean_value,
                MIN(value) AS minimum_value,
                MAX(value) AS maximum_value

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
                    AVG(value) AS mean_value,
                    MIN(value) AS minimum_value,
                    MAX(value) AS maximum_value

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
            # A bucket may contribute at most four actual
            # representative observations:
            #
            # first / minimum / maximum / last
            #
            # Therefore the number of buckets is derived from
            # the rendering point limit rather than treating
            # point_limit as the bucket count.
            bucket_count = max(
                1,
                point_limit // 4,
            )

            bucket_width_seconds = (
                span_seconds
                / bucket_count
            )

            bucket_rows = (
                connection.execute(
                    normalized_sql
                    + """
                    , bucketed AS (
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

                            parsed_time,
                            value

                        FROM valid
                    ),

                    ranked AS (
                        SELECT
                            bucket_index,
                            parsed_time,
                            value,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    parsed_time ASC,
                                    value ASC
                            ) AS first_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    value ASC,
                                    parsed_time ASC
                            ) AS minimum_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    value DESC,
                                    parsed_time ASC
                            ) AS maximum_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    parsed_time DESC,
                                    value ASC
                            ) AS last_rank

                        FROM bucketed
                    )

                    SELECT
                        bucket_index,

                        COUNT(*) AS row_count,
                        AVG(value) AS mean_value,
                        MIN(value) AS minimum_value,
                        MAX(value) AS maximum_value,

                        MIN(parsed_time)
                            FILTER (
                                WHERE first_rank = 1
                            ) AS first_time,

                        MIN(value)
                            FILTER (
                                WHERE first_rank = 1
                            ) AS first_value,

                        MIN(parsed_time)
                            FILTER (
                                WHERE minimum_rank = 1
                            ) AS minimum_time,

                        MIN(parsed_time)
                            FILTER (
                                WHERE maximum_rank = 1
                            ) AS maximum_time,

                        MIN(parsed_time)
                            FILTER (
                                WHERE last_rank = 1
                            ) AS last_time,

                        MIN(value)
                            FILTER (
                                WHERE last_rank = 1
                            ) AS last_value

                    FROM ranked

                    GROUP BY bucket_index
                    ORDER BY bucket_index
                    """,
                    [
                        bucket_count - 1,
                        float(first_epoch),
                        bucket_width_seconds,
                    ],
                ).fetchall()
            )

            display_projection = (
                build_time_bucket_extrema_projection(
                    bucket_rows=(
                        bucket_rows
                    ),
                    first_observation=(
                        first_observation
                    ),
                    last_observation=(
                        last_observation
                    ),
                    bucket_width_seconds=(
                        bucket_width_seconds
                    ),
                    bucket_count=(
                        bucket_count
                    ),
                    point_limit=(
                        point_limit
                    ),
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
        "source": (
            source_result
        ),
        "display_projection": (
            display_projection
        ),
        "execution": {
            "mode": (
                "duckdb_temporal_display_projection"
            ),

            # Display projection intentionally uses normalized
            # chronological time. This is independent of the
            # observed relation order used by continuity
            # analysis.
            "temporal_display_order": (
                "parsed_time_ascending"
            ),

            "source_order_used": False,

            # Rendering/output resource bound only.
            # It does not limit analytical observation
            # processing.
            "point_limit": (
                point_limit
            ),

            "limitations": [
                (
                    "Display projection is not "
                    "the analytical observation series."
                ),
                (
                    "Large temporal series are reduced "
                    "for display while preserving selected "
                    "first, minimum, maximum and last "
                    "source observations per time bucket."
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
def _build_exact_detail_projection(
    rows: list[tuple[Any, ...]],
    point_limit: int,
) -> dict[str, Any]:
    """
    Build an exact display projection from matching source
    observations.

    Every returned point corresponds to one usable source
    observation in the selected temporal interval.

    The ordering is chronological. Observations sharing the
    same timestamp are deterministically ordered by value.
    """

    if len(rows) > point_limit:
        raise ValueError(
            "Exact detail projection exceeds point_limit"
        )

    if not rows:
        return {
            "mode": "empty",
            "point_limit": point_limit,
            "point_count": 0,
            "bucket_count": None,
            "bucket_width_seconds": None,
            "points": [],
        }

    first_epoch = float(
        rows[0][2]
    )

    last_epoch = float(
        rows[-1][2]
    )

    span_seconds = (
        last_epoch
        - first_epoch
    )

    points: list[dict[str, Any]] = []

    for (
        projection_index,
        row,
    ) in enumerate(rows):
        parsed_time = row[0]
        value = float(row[1])
        epoch = float(row[2])

        if span_seconds > 0:
            position = (
                epoch - first_epoch
            ) / span_seconds
        else:
            position = 0.5

        position = max(
            0.0,
            min(
                1.0,
                position,
            ),
        )

        points.append({
            "projection_index": (
                projection_index
            ),
            "time": temporal_to_json(
                parsed_time
            ),
            "value": value,
            "position": position,
            "roles": [
                "observation",
            ],
            "break_before": False,
        })

    return {
        "mode": "exact_observations",
        "point_limit": point_limit,
        "point_count": len(points),
        "bucket_count": None,
        "bucket_width_seconds": None,
        "points": points,
    }


def _execute_detail_with_context(
    source_context: SourceExecutionContext,
    temporal_axis: dict[str, Any],
    continuity: dict[str, Any] | None,
    value_column_name: str,
    start_time: str,
    end_time: str,
    point_limit: int,
) -> dict[str, Any]:
    """
    Read one temporal detail interval from the original source.

    The overview projection is not used as input data.

    The selected interval is applied directly to normalized
    source observations.

    When all matching observations fit within point_limit,
    every usable source observation is returned directly.

    When the interval contains more observations than can be
    rendered safely, a bounded extrema-preserving display
    projection is built from the original observations in the
    selected interval.

    point_limit is strictly a display/output resource bound.
    """

    if point_limit < 4:
        raise ValueError(
            "point_limit must be at least 4 "
            "for temporal detail projection"
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

    parsed_request = (
        connection.execute(
            """
            SELECT
                TRY_CAST(? AS TIMESTAMP),
                TRY_CAST(? AS TIMESTAMP)
            """,
            [
                start_time,
                end_time,
            ],
        ).fetchone()
    )

    requested_start = (
        parsed_request[0]
    )

    requested_end = (
        parsed_request[1]
    )

    if requested_start is None:
        raise ValueError(
            "start_time is not a valid timestamp"
        )

    if requested_end is None:
        raise ValueError(
            "end_time is not a valid timestamp"
        )

    if (
        requested_end
        < requested_start
    ):
        raise ValueError(
            "end_time must be greater than or "
            "equal to start_time"
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
        ),

        interval_valid AS (
            SELECT
                parsed_time,
                value

            FROM valid

            WHERE parsed_time >= ?
              AND parsed_time <= ?
        )
    """

    interval_parameters = [
        requested_start,
        requested_end,
    ]

    bounds = (
        connection.execute(
            normalized_sql
            + """
            SELECT
                COUNT(*),
                MIN(parsed_time),
                MAX(parsed_time),
                MIN(EPOCH(parsed_time)),
                MAX(EPOCH(parsed_time))

            FROM interval_valid
            """,
            interval_parameters,
        ).fetchone()
    )

    (
        matching_observation_count,
        first_observation,
        last_observation,
        first_epoch,
        last_epoch,
    ) = bounds

    matching_observation_count = int(
        matching_observation_count
    )

    source_result = {
        "matching_observation_count": (
            matching_observation_count
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

    requested_range = {
        "start": temporal_to_json(
            requested_start
        ),
        "end": temporal_to_json(
            requested_end
        ),
    }

    if (
        matching_observation_count == 0
        or first_observation is None
        or last_observation is None
    ):
        return {
            "status": "insufficient_data",
            "result_kind": (
                "long_temporal_series_detail"
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
            "requested_range": (
                requested_range
            ),
            "source": (
                source_result
            ),
            "display_projection": {
                "mode": "empty",
                "point_limit": (
                    point_limit
                ),
                "point_count": 0,
                "bucket_count": None,
                "bucket_width_seconds": None,
                "points": [],
            },
            "execution": {
                "mode": (
                    "duckdb_temporal_detail"
                ),
                "temporal_display_order": (
                    "parsed_time_ascending"
                ),
                "source_order_used": False,
                "point_limit": (
                    point_limit
                ),
                "limitations": [],
            },
        }

    if (
        matching_observation_count
        <= point_limit
    ):
        rows = (
            connection.execute(
                normalized_sql
                + """
                SELECT
                    parsed_time,
                    value,
                    EPOCH(parsed_time)

                FROM interval_valid

                ORDER BY
                    parsed_time,
                    value
                """,
                interval_parameters,
            ).fetchall()
        )

        display_projection = (
            _build_exact_detail_projection(
                rows=rows,
                point_limit=point_limit,
            )
        )

        limitations = [
            (
                "All matching usable observations "
                "are represented directly."
            ),
        ]

    else:
        span_seconds = (
            float(last_epoch)
            - float(first_epoch)
        )

        if span_seconds <= 0:
            rows = (
                connection.execute(
                    normalized_sql
                    + """
                    SELECT
                        parsed_time,
                        COUNT(*) AS row_count,
                        AVG(value) AS mean_value,
                        MIN(value) AS minimum_value,
                        MAX(value) AS maximum_value

                    FROM interval_valid

                    GROUP BY parsed_time
                    ORDER BY parsed_time
                    """,
                    interval_parameters,
                ).fetchall()
            )

            display_projection = (
                build_temporal_value_projection(
                    rows=rows,
                    point_limit=point_limit,
                )
            )

        else:
            bucket_count = max(
                1,
                point_limit // 4,
            )

            bucket_width_seconds = (
                span_seconds
                / bucket_count
            )

            bucket_rows = (
                connection.execute(
                    normalized_sql
                    + """
                    , bucketed AS (
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

                            parsed_time,
                            value

                        FROM interval_valid
                    ),

                    ranked AS (
                        SELECT
                            bucket_index,
                            parsed_time,
                            value,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    parsed_time ASC,
                                    value ASC
                            ) AS first_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    value ASC,
                                    parsed_time ASC
                            ) AS minimum_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    value DESC,
                                    parsed_time ASC
                            ) AS maximum_rank,

                            ROW_NUMBER() OVER (
                                PARTITION BY bucket_index
                                ORDER BY
                                    parsed_time DESC,
                                    value ASC
                            ) AS last_rank

                        FROM bucketed
                    )

                    SELECT
                        bucket_index,

                        COUNT(*) AS row_count,
                        AVG(value) AS mean_value,
                        MIN(value) AS minimum_value,
                        MAX(value) AS maximum_value,

                        MIN(parsed_time)
                            FILTER (
                                WHERE first_rank = 1
                            ) AS first_time,

                        MIN(value)
                            FILTER (
                                WHERE first_rank = 1
                            ) AS first_value,

                        MIN(parsed_time)
                            FILTER (
                                WHERE minimum_rank = 1
                            ) AS minimum_time,

                        MIN(parsed_time)
                            FILTER (
                                WHERE maximum_rank = 1
                            ) AS maximum_time,

                        MIN(parsed_time)
                            FILTER (
                                WHERE last_rank = 1
                            ) AS last_time,

                        MIN(value)
                            FILTER (
                                WHERE last_rank = 1
                            ) AS last_value

                    FROM ranked

                    GROUP BY bucket_index
                    ORDER BY bucket_index
                    """,
                    [
                        *interval_parameters,
                        bucket_count - 1,
                        float(first_epoch),
                        bucket_width_seconds,
                    ],
                ).fetchall()
            )

            display_projection = (
                build_time_bucket_extrema_projection(
                    bucket_rows=(
                        bucket_rows
                    ),
                    first_observation=(
                        first_observation
                    ),
                    last_observation=(
                        last_observation
                    ),
                    bucket_width_seconds=(
                        bucket_width_seconds
                    ),
                    bucket_count=(
                        bucket_count
                    ),
                    point_limit=(
                        point_limit
                    ),
                )
            )

        limitations = [
            (
                "The selected interval contains "
                "more usable observations than "
                "the display point limit."
            ),
            (
                "The display projection is reduced "
                "from original observations in the "
                "selected interval."
            ),
        ]

    return {
        "status": "measured",
        "result_kind": (
            "long_temporal_series_detail"
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
        "requested_range": (
            requested_range
        ),
        "source": (
            source_result
        ),
        "display_projection": (
            display_projection
        ),
        "execution": {
            "mode": (
                "duckdb_temporal_detail"
            ),
            "temporal_display_order": (
                "parsed_time_ascending"
            ),
            "source_order_used": False,
            "point_limit": (
                point_limit
            ),
            "limitations": (
                limitations
            ),
        },
    }


def execute_long_temporal_series_detail(
    file_path: str,
    temporal_axis: dict[str, Any],
    continuity: dict[str, Any] | None,
    value_column_name: str,
    start_time: str,
    end_time: str,
    point_limit: int = 1000,
    source_context: (
        SourceExecutionContext | None
    ) = None,
) -> dict[str, Any]:
    """
    Build a temporal detail view directly from original source
    observations inside one requested time interval.

    Detection and normalization are not repeated here.
    The caller supplies the established vertical temporal axis
    and continuity evidence from Light Analysis.

    point_limit controls only the returned display projection.
    It is not an analytical acceptance threshold.
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

        return _execute_detail_with_context(
            source_context=source_context,
            temporal_axis=temporal_axis,
            continuity=continuity,
            value_column_name=(
                value_column_name
            ),
            start_time=start_time,
            end_time=end_time,
            point_limit=point_limit,
        )

    with SourceExecutionContext(
        file_path
    ) as owned_context:
        return _execute_detail_with_context(
            source_context=owned_context,
            temporal_axis=temporal_axis,
            continuity=continuity,
            value_column_name=(
                value_column_name
            ),
            start_time=start_time,
            end_time=end_time,
            point_limit=point_limit,
        )