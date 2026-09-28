from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable


def temporal_to_json(
    value: object,
) -> str | None:
    """
    Convert one already normalized temporal value to a
    JSON-safe representation without assigning additional
    semantics.
    """

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    return str(value)


def _number_to_float(
    value: object,
) -> float | None:
    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return float(value)

    return float(value)


def build_temporal_value_projection(
    rows: Iterable[
        tuple[
            object,
            int,
            object,
            object,
            object,
        ]
    ],
    point_limit: int,
) -> dict:
    """
    Build a bounded display projection from already grouped
    temporal values.

    One result point represents one observed temporal value.
    Multiple source rows at the same temporal value are
    represented through count / mean / minimum / maximum.

    This is a display projection. It is not the analytical
    observation model.
    """

    if point_limit < 2:
        raise ValueError(
            "point_limit must be at least 2"
        )

    points = []

    for (
        temporal_value,
        row_count,
        mean_value,
        minimum_value,
        maximum_value,
    ) in rows:
        if len(points) >= point_limit:
            raise ValueError(
                "Temporal value projection exceeded "
                "the supplied point limit"
            )

        projection_index = len(
            points
        )

        points.append({
            "projection_index": (
                projection_index
            ),
            "time": temporal_to_json(
                temporal_value
            ),
            "count": int(
                row_count
            ),
            "mean": _number_to_float(
                mean_value
            ),
            "minimum": _number_to_float(
                minimum_value
            ),
            "maximum": _number_to_float(
                maximum_value
            ),
            "bucket_start": None,
            "bucket_end": None,
        })

    return {
        "mode": (
            "temporal_value_groups"
        ),
        "point_limit": point_limit,
        "point_count": len(
            points
        ),
        "bucket_width_seconds": None,
        "points": points,
    }


def build_time_bucket_projection(
    bucket_rows: Iterable[
        tuple[
            int,
            int,
            object,
            object,
            object,
        ]
    ],
    first_observation: datetime,
    bucket_width_seconds: float,
    point_limit: int,
) -> dict:
    """
    Build an equal-time-width display projection.

    Empty buckets are retained explicitly. This lets a
    visualization preserve periods without observations
    without classifying those periods as gaps, errors,
    interruptions, or anomalies.

    This function only constructs a display representation.
    Analytical processing must use the full observation
    series rather than these aggregated points.
    """

    if point_limit < 2:
        raise ValueError(
            "point_limit must be at least 2"
        )

    if bucket_width_seconds <= 0:
        raise ValueError(
            "bucket_width_seconds must be > 0"
        )

    buckets_by_index = {}

    for (
        bucket_index,
        row_count,
        mean_value,
        minimum_value,
        maximum_value,
    ) in bucket_rows:
        if (
            bucket_index < 0
            or bucket_index >= point_limit
        ):
            raise ValueError(
                "Observed bucket index is outside "
                "the display projection"
            )

        buckets_by_index[
            int(bucket_index)
        ] = (
            int(row_count),
            mean_value,
            minimum_value,
            maximum_value,
        )

    points = []

    for bucket_index in range(
        point_limit
    ):
        bucket_start = (
            first_observation
            + timedelta(
                seconds=(
                    bucket_width_seconds
                    * bucket_index
                )
            )
        )

        bucket_end = (
            first_observation
            + timedelta(
                seconds=(
                    bucket_width_seconds
                    * (bucket_index + 1)
                )
            )
        )

        bucket_time = (
            bucket_start
            + timedelta(
                seconds=(
                    bucket_width_seconds
                    / 2
                )
            )
        )

        bucket_values = (
            buckets_by_index.get(
                bucket_index
            )
        )

        if bucket_values is None:
            points.append({
                "projection_index": (
                    bucket_index
                ),
                "time": temporal_to_json(
                    bucket_time
                ),
                "count": 0,
                "mean": None,
                "minimum": None,
                "maximum": None,
                "bucket_start": (
                    temporal_to_json(
                        bucket_start
                    )
                ),
                "bucket_end": (
                    temporal_to_json(
                        bucket_end
                    )
                ),
            })

            continue

        (
            row_count,
            mean_value,
            minimum_value,
            maximum_value,
        ) = bucket_values

        points.append({
            "projection_index": (
                bucket_index
            ),
            "time": temporal_to_json(
                bucket_time
            ),
            "count": row_count,
            "mean": _number_to_float(
                mean_value
            ),
            "minimum": _number_to_float(
                minimum_value
            ),
            "maximum": _number_to_float(
                maximum_value
            ),
            "bucket_start": (
                temporal_to_json(
                    bucket_start
                )
            ),
            "bucket_end": (
                temporal_to_json(
                    bucket_end
                )
            ),
        })

    return {
        "mode": "time_bucketed",
        "point_limit": point_limit,
        "point_count": len(
            points
        ),
        "bucket_width_seconds": (
            bucket_width_seconds
        ),
        "points": points,
    }