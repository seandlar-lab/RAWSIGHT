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


def _require_datetime(
    value: object,
    field_name: str,
) -> datetime:
    if not isinstance(
        value,
        datetime,
    ):
        raise ValueError(
            f"{field_name} must be a normalized datetime"
        )

    return value


def _temporal_position(
    value: datetime,
    first_observation: datetime,
    last_observation: datetime,
) -> float:
    """
    Return the normalized temporal position of one display
    point in the complete displayed temporal span.

    Position is a rendering coordinate only. It does not
    assign analytical meaning to the observation.
    """

    total_span = (
        last_observation
        - first_observation
    ).total_seconds()

    if total_span <= 0:
        return 0.5

    position = (
        (
            value
            - first_observation
        ).total_seconds()
        / total_span
    )

    return max(
        0.0,
        min(
            1.0,
            float(position),
        ),
    )


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
    Build a bounded display projection when the normalized
    temporal value groups already fit inside point_limit.

    All display points use the common temporal display
    contract:

    - projection_index
    - time
    - value
    - position
    - roles
    - break_before

    A source timestamp containing exactly one usable row is
    represented as an observation.

    Multiple usable source rows sharing the same timestamp are
    represented as one temporal-value group. Its display value
    is the group mean. This is stated explicitly through the
    role rather than pretending that the mean is an observed
    source value.

    This is a display projection. It is not the analytical
    observation model.
    """

    if point_limit < 2:
        raise ValueError(
            "point_limit must be at least 2"
        )

    materialized_rows = list(
        rows
    )

    if len(
        materialized_rows
    ) > point_limit:
        raise ValueError(
            "Temporal value projection exceeded "
            "the supplied point limit"
        )

    if not materialized_rows:
        return {
            "mode": (
                "temporal_value_groups"
            ),
            "point_limit": point_limit,
            "point_count": 0,
            "bucket_count": None,
            "bucket_width_seconds": None,
            "points": [],
            "groups": [],
        }

    first_observation = _require_datetime(
        materialized_rows[0][0],
        "first temporal value",
    )

    last_observation = _require_datetime(
        materialized_rows[-1][0],
        "last temporal value",
    )

    points = []
    groups = []

    for (
        temporal_value,
        row_count,
        mean_value,
        minimum_value,
        maximum_value,
    ) in materialized_rows:
        normalized_time = _require_datetime(
            temporal_value,
            "temporal value",
        )

        normalized_count = int(
            row_count
        )

        mean_float = _number_to_float(
            mean_value
        )

        minimum_float = _number_to_float(
            minimum_value
        )

        maximum_float = _number_to_float(
            maximum_value
        )

        if mean_float is None:
            continue

        role = (
            "observation"
            if normalized_count == 1
            else "temporal_value_group"
        )

        points.append({
            "projection_index": (
                len(points)
            ),
            "time": temporal_to_json(
                normalized_time
            ),
            "value": mean_float,
            "position": (
                _temporal_position(
                    value=normalized_time,
                    first_observation=(
                        first_observation
                    ),
                    last_observation=(
                        last_observation
                    ),
                )
            ),
            "roles": [
                role
            ],
            "break_before": False,
        })

        groups.append({
            "time": temporal_to_json(
                normalized_time
            ),
            "count": normalized_count,
            "mean": mean_float,
            "minimum": minimum_float,
            "maximum": maximum_float,
        })

    return {
        "mode": (
            "temporal_value_groups"
        ),
        "point_limit": point_limit,
        "point_count": len(
            points
        ),
        "bucket_count": None,
        "bucket_width_seconds": None,
        "points": points,
        "groups": groups,
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
    Build the legacy equal-time-width mean projection.

    Retained temporarily for compatibility while the
    extrema-preserving projection replaces it.

    The emitted points nevertheless use the same common
    temporal display contract as the other projection modes.

    This function must not be used as an analytical
    observation series.
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
        normalized_bucket_index = int(
            bucket_index
        )

        if (
            normalized_bucket_index < 0
            or normalized_bucket_index
            >= point_limit
        ):
            raise ValueError(
                "Observed bucket index is outside "
                "the display projection"
            )

        buckets_by_index[
            normalized_bucket_index
        ] = (
            int(row_count),
            mean_value,
            minimum_value,
            maximum_value,
        )

    last_observation = (
        first_observation
        + timedelta(
            seconds=(
                bucket_width_seconds
                * point_limit
            )
        )
    )

    points = []
    buckets = []

    previous_observed_bucket = None

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

        bucket_values = (
            buckets_by_index.get(
                bucket_index
            )
        )

        if bucket_values is None:
            buckets.append({
                "bucket_index": (
                    bucket_index
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
                "count": 0,
                "mean": None,
                "minimum": None,
                "maximum": None,
            })

            continue

        (
            row_count,
            mean_value,
            minimum_value,
            maximum_value,
        ) = bucket_values

        mean_float = _number_to_float(
            mean_value
        )

        minimum_float = _number_to_float(
            minimum_value
        )

        maximum_float = _number_to_float(
            maximum_value
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

        break_before = (
            previous_observed_bucket
            is not None
            and bucket_index
            > previous_observed_bucket + 1
        )

        if mean_float is not None:
            points.append({
                "projection_index": (
                    len(points)
                ),
                "time": temporal_to_json(
                    bucket_time
                ),
                "value": mean_float,
                "position": (
                    _temporal_position(
                        value=bucket_time,
                        first_observation=(
                            first_observation
                        ),
                        last_observation=(
                            last_observation
                        ),
                    )
                ),
                "roles": [
                    "bucket_mean"
                ],
                "break_before": (
                    break_before
                ),
            })

        buckets.append({
            "bucket_index": (
                bucket_index
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
            "count": row_count,
            "mean": mean_float,
            "minimum": minimum_float,
            "maximum": maximum_float,
        })

        previous_observed_bucket = (
            bucket_index
        )

    return {
        "mode": "time_bucketed",
        "point_limit": point_limit,
        "point_count": len(
            points
        ),
        "bucket_count": (
            point_limit
        ),
        "bucket_width_seconds": (
            bucket_width_seconds
        ),
        "points": points,
        "buckets": buckets,
    }


def build_time_bucket_extrema_projection(
    bucket_rows: Iterable[
        tuple[
            int,
            int,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
        ]
    ],
    first_observation: datetime,
    last_observation: datetime,
    bucket_width_seconds: float,
    bucket_count: int,
    point_limit: int,
) -> dict:
    """
    Build an extrema-preserving display projection.

    Each non-empty time bucket may contribute up to four
    representative source observations:

    - first
    - minimum
    - maximum
    - last

    Representatives retain their actual observed timestamp
    and actual value.

    If one source observation fulfills multiple roles, it is
    emitted once and its roles are combined.

    Empty bucket ranges are represented through break_before
    on the first following representative point. This avoids
    drawing false continuity across periods without observed
    values while avoiding artificial null data points.

    Bucket statistics are retained separately for inspection,
    semantic zoom and future detail views.

    This is a display projection only. Analytical processing
    must use the full observation series.
    """

    if point_limit < 4:
        raise ValueError(
            "point_limit must be at least 4 "
            "for extrema-preserving projection"
        )

    if bucket_count < 1:
        raise ValueError(
            "bucket_count must be at least 1"
        )

    if bucket_width_seconds <= 0:
        raise ValueError(
            "bucket_width_seconds must be > 0"
        )

    if bucket_count * 4 > point_limit:
        raise ValueError(
            "bucket_count may produce more representative "
            "points than point_limit"
        )

    rows_by_bucket: dict[
        int,
        tuple[
            int,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
            object,
        ],
    ] = {}

    for (
        bucket_index,
        row_count,
        mean_value,
        minimum_value,
        maximum_value,
        first_time,
        first_value,
        minimum_time,
        maximum_time,
        last_time,
        last_value,
    ) in bucket_rows:
        normalized_bucket_index = int(
            bucket_index
        )

        if (
            normalized_bucket_index < 0
            or normalized_bucket_index
            >= bucket_count
        ):
            raise ValueError(
                "Observed bucket index is outside "
                "the extrema display projection"
            )

        rows_by_bucket[
            normalized_bucket_index
        ] = (
            int(row_count),
            mean_value,
            minimum_value,
            maximum_value,
            first_time,
            first_value,
            minimum_time,
            maximum_time,
            last_time,
            last_value,
        )

    buckets = []
    representatives = []

    for bucket_index in range(
        bucket_count
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

        bucket_values = (
            rows_by_bucket.get(
                bucket_index
            )
        )

        if bucket_values is None:
            buckets.append({
                "bucket_index": (
                    bucket_index
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
                "count": 0,
                "mean": None,
                "minimum": None,
                "maximum": None,
            })

            continue

        (
            row_count,
            mean_value,
            minimum_value,
            maximum_value,
            first_time,
            first_value,
            minimum_time,
            maximum_time,
            last_time,
            last_value,
        ) = bucket_values

        normalized_first_time = (
            _require_datetime(
                first_time,
                "first representative time",
            )
        )

        normalized_minimum_time = (
            _require_datetime(
                minimum_time,
                "minimum representative time",
            )
        )

        normalized_maximum_time = (
            _require_datetime(
                maximum_time,
                "maximum representative time",
            )
        )

        normalized_last_time = (
            _require_datetime(
                last_time,
                "last representative time",
            )
        )

        mean_float = _number_to_float(
            mean_value
        )

        minimum_float = (
            _number_to_float(
                minimum_value
            )
        )

        maximum_float = (
            _number_to_float(
                maximum_value
            )
        )

        first_float = _number_to_float(
            first_value
        )

        last_float = _number_to_float(
            last_value
        )

        buckets.append({
            "bucket_index": (
                bucket_index
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
            "count": row_count,
            "mean": mean_float,
            "minimum": minimum_float,
            "maximum": maximum_float,
        })

        candidates = [
            (
                "first",
                normalized_first_time,
                first_float,
            ),
            (
                "minimum",
                normalized_minimum_time,
                minimum_float,
            ),
            (
                "maximum",
                normalized_maximum_time,
                maximum_float,
            ),
            (
                "last",
                normalized_last_time,
                last_float,
            ),
        ]

        representatives_by_key = {}

        for (
            role,
            temporal_value,
            numeric_value,
        ) in candidates:
            if numeric_value is None:
                continue

            key = (
                temporal_value,
                numeric_value,
            )

            existing = (
                representatives_by_key.get(
                    key
                )
            )

            if existing is None:
                representatives_by_key[
                    key
                ] = {
                    "bucket_index": (
                        bucket_index
                    ),
                    "time_value": (
                        temporal_value
                    ),
                    "value": (
                        numeric_value
                    ),
                    "roles": [
                        role
                    ],
                }

                continue

            existing[
                "roles"
            ].append(
                role
            )

        bucket_representatives = sorted(
            representatives_by_key.values(),
            key=lambda item: (
                item["time_value"],
                item["value"],
            ),
        )

        representatives.extend(
            bucket_representatives
        )

    representatives.sort(
        key=lambda item: (
            item["time_value"],
            item["value"],
        )
    )

    if len(
        representatives
    ) > point_limit:
        raise ValueError(
            "Extrema projection exceeded "
            "the supplied point limit"
        )

    points = []
    previous_bucket_index = None

    for representative in representatives:
        temporal_value = (
            representative[
                "time_value"
            ]
        )

        bucket_index = (
            representative[
                "bucket_index"
            ]
        )

        break_before = (
            previous_bucket_index
            is not None
            and bucket_index
            > previous_bucket_index + 1
        )

        points.append({
            "projection_index": (
                len(points)
            ),
            "time": temporal_to_json(
                temporal_value
            ),
            "value": (
                representative[
                    "value"
                ]
            ),
            "position": (
                _temporal_position(
                    value=temporal_value,
                    first_observation=(
                        first_observation
                    ),
                    last_observation=(
                        last_observation
                    ),
                )
            ),
            "roles": list(
                representative[
                    "roles"
                ]
            ),
            "break_before": (
                break_before
            ),
        })

        previous_bucket_index = (
            bucket_index
        )

    return {
        "mode": (
            "time_bucketed_extrema"
        ),
        "point_limit": point_limit,
        "point_count": len(
            points
        ),
        "bucket_count": (
            bucket_count
        ),
        "bucket_width_seconds": (
            bucket_width_seconds
        ),
        "points": points,
        "buckets": buckets,
    }