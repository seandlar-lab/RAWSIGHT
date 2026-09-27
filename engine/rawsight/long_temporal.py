from collections import Counter
from datetime import date, datetime, time
from typing import Iterable
from heapq import heappush, heapreplace


def _normalize_temporal_value(
    value: object,
) -> datetime | None:
    """
    Accept already-normalized temporal values.

    Parsing source-specific representations belongs to
    detection/normalization, not to this analysis function.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(
            value,
            time.min,
        )

    raise TypeError(
        "Long temporal analysis requires normalized "
        f"date/datetime values, got {type(value).__name__}"
    )


def _classify_order(
    positive: int,
    zero: int,
    negative: int,
) -> str:
    """
    Describe the order in which temporal values were observed.

    No assumption is made about physical source order,
    canonical order, or whether this order can be reused by
    an execution strategy.
    """

    if positive == 0 and zero == 0 and negative == 0:
        return "single_or_empty"

    if positive and not zero and not negative:
        return "strictly_increasing"

    if positive and zero and not negative:
        return "non_decreasing"

    if negative and not zero and not positive:
        return "strictly_decreasing"

    if negative and zero and not positive:
        return "non_increasing"

    if zero and not positive and not negative:
        return "constant"

    return "unordered"


def analyze_long_temporal_axis(
    values: Iterable[object],
    *,
    interval_frequency_limit: int | None = None,
    largest_positive_interval_limit: int = 0,
) -> dict:
    """
    Analyze one normalized temporal sequence in observed order.

    The input is consumed as a stream. Values are not
    materialized or sorted.

    Missing values break adjacency for interval analysis, while
    ordering among the observed temporal values can still be
    described.

    interval_frequency_limit is an execution/resource control.
    If the number of distinct positive adjacent intervals
    exceeds it, exact interval-frequency analysis is abandoned
    rather than approximated.
    """

    if (
        interval_frequency_limit is not None
        and interval_frequency_limit < 1
    ):
        raise ValueError(
            "interval_frequency_limit must be positive or None"
        )

    if largest_positive_interval_limit < 0:
        raise ValueError(
            "largest_positive_interval_limit "
            "must be zero or positive"
        )

    value_count = 0
    temporal_value_count = 0
    missing_count = 0

    first_value = None
    last_value = None
    range_start = None
    range_end = None

    # Ordering among observed temporal values. Missing positions
    # do not erase the ability to describe relative order.
    previous_observed = None

    positive_observed_transitions = 0
    zero_observed_transitions = 0
    negative_observed_transitions = 0

    # Adjacency is different from ordering. A missing temporal
    # value breaks the adjacent sampling relationship.
    
    previous_adjacent = None
    previous_adjacent_index = None

    # Bounded evidence only. These are observations, not
    # automatically gaps, interruptions, or anomalies.
    largest_positive_intervals = []

    adjacent_delta_count = 0

    positive_adjacent_intervals = 0
    zero_adjacent_deltas = 0
    negative_adjacent_deltas = 0

    min_observed_delta_seconds = None
    max_observed_delta_seconds = None

    min_positive_interval_seconds = None
    max_positive_interval_seconds = None

    positive_interval_counts = Counter()
    interval_frequency_complete = True

    for raw_value in values:
        value_count += 1

        current_index = value_count - 1

        value = _normalize_temporal_value(
            raw_value
        )

        if value is None:
            missing_count += 1

            # Do not create an artificial interval across a
            # missing temporal position.
            previous_adjacent_index = None
            previous_adjacent = None
            continue

        temporal_value_count += 1

        if first_value is None:
            first_value = value

        last_value = value

        if (
            range_start is None
            or value < range_start
        ):
            range_start = value

        if (
            range_end is None
            or value > range_end
        ):
            range_end = value

        if previous_observed is not None:
            observed_delta = (
                value - previous_observed
            ).total_seconds()

            if observed_delta > 0:
                positive_observed_transitions += 1

            elif observed_delta == 0:
                zero_observed_transitions += 1

            else:
                negative_observed_transitions += 1

        previous_observed = value

        if previous_adjacent is not None:
            delta_seconds = (
                value - previous_adjacent
            ).total_seconds()

            adjacent_delta_count += 1

            if (
                min_observed_delta_seconds is None
                or delta_seconds
                < min_observed_delta_seconds
            ):
                min_observed_delta_seconds = (
                    delta_seconds
                )

            if (
                max_observed_delta_seconds is None
                or delta_seconds
                > max_observed_delta_seconds
            ):
                max_observed_delta_seconds = (
                    delta_seconds
                )

            if delta_seconds > 0:
                positive_adjacent_intervals += 1

                if (
                    largest_positive_interval_limit > 0
                    and previous_adjacent_index is not None
                ):
                    candidate = (
                        delta_seconds,
                        -previous_adjacent_index,
                        previous_adjacent_index,
                        current_index,
                        previous_adjacent,
                        value,
                    )

                    if (
                        len(largest_positive_intervals)
                        < largest_positive_interval_limit
                    ):
                        heappush(
                            largest_positive_intervals,
                            candidate,
                        )

                    elif (
                        candidate[:2]
                        > largest_positive_intervals[0][:2]
                    ):
                        heapreplace(
                            largest_positive_intervals,
                            candidate,
                        )

                if (
                    min_positive_interval_seconds is None
                    or delta_seconds
                    < min_positive_interval_seconds
                ):
                    min_positive_interval_seconds = (
                        delta_seconds
                    )

                if (
                    max_positive_interval_seconds is None
                    or delta_seconds
                    > max_positive_interval_seconds
                ):
                    max_positive_interval_seconds = (
                        delta_seconds
                    )

                if interval_frequency_complete:
                    if (
                        delta_seconds
                        in positive_interval_counts
                    ):
                        positive_interval_counts[
                            delta_seconds
                        ] += 1

                    elif (
                        interval_frequency_limit is None
                        or len(
                            positive_interval_counts
                        )
                        < interval_frequency_limit
                    ):
                        positive_interval_counts[
                            delta_seconds
                        ] = 1

                    else:
                        interval_frequency_complete = False
                        positive_interval_counts.clear()

            elif delta_seconds == 0:
                zero_adjacent_deltas += 1

            else:
                negative_adjacent_deltas += 1

        previous_adjacent = value
        previous_adjacent_index = current_index

    observed_order = _classify_order(
        positive_observed_transitions,
        zero_observed_transitions,
        negative_observed_transitions,
    )

    dominant_positive_interval_seconds = None
    dominant_positive_interval_count = None
    positive_interval_consistency = None

    if (
        interval_frequency_complete
        and positive_interval_counts
    ):
        (
            dominant_positive_interval_seconds,
            dominant_positive_interval_count,
        ) = positive_interval_counts.most_common(
            1
        )[0]

        if positive_adjacent_intervals:
            positive_interval_consistency = (
                dominant_positive_interval_count
                / positive_adjacent_intervals
            )
    
        retained_largest_intervals = []

    for (
        interval_seconds,
        _,
        from_index,
        to_index,
        from_value,
        to_value,
    ) in sorted(
        largest_positive_intervals,
        key=lambda item: (
            -item[0],
            item[2],
        ),
    ):
        interval_multiple = None

        if (
            dominant_positive_interval_seconds
            is not None
            and dominant_positive_interval_seconds > 0
        ):
            interval_multiple = (
                interval_seconds
                / dominant_positive_interval_seconds
            )

        retained_largest_intervals.append({
            "from_index": from_index,
            "to_index": to_index,
            "from_value": from_value.isoformat(),
            "to_value": to_value.isoformat(),
            "interval_seconds": interval_seconds,
            "multiple_of_dominant_interval": (
                interval_multiple
            ),
        })

    return {
        "value_count": value_count,
        "temporal_value_count": temporal_value_count,
        "missing_count": missing_count,

        "first_value": (
            first_value.isoformat()
            if first_value is not None
            else None
        ),
        "last_value": (
            last_value.isoformat()
            if last_value is not None
            else None
        ),
        "range_start": (
            range_start.isoformat()
            if range_start is not None
            else None
        ),
        "range_end": (
            range_end.isoformat()
            if range_end is not None
            else None
        ),

        "observed_order": observed_order,
        "positive_observed_transitions": (
            positive_observed_transitions
        ),
        "zero_observed_transitions": (
            zero_observed_transitions
        ),
        "negative_observed_transitions": (
            negative_observed_transitions
        ),

        "adjacent_delta_count": (
            adjacent_delta_count
        ),
        "positive_adjacent_intervals": (
            positive_adjacent_intervals
        ),
        "zero_adjacent_deltas": (
            zero_adjacent_deltas
        ),
        "negative_adjacent_deltas": (
            negative_adjacent_deltas
        ),

        "min_observed_delta_seconds": (
            min_observed_delta_seconds
        ),
        "max_observed_delta_seconds": (
            max_observed_delta_seconds
        ),

        "min_positive_interval_seconds": (
            min_positive_interval_seconds
        ),
        "max_positive_interval_seconds": (
            max_positive_interval_seconds
        ),

        "dominant_positive_interval_seconds": (
            dominant_positive_interval_seconds
        ),
        "dominant_positive_interval_count": (
            dominant_positive_interval_count
        ),
        "positive_interval_consistency": (
            positive_interval_consistency
        ),

        "interval_frequency_complete": (
            interval_frequency_complete
        ),
        "distinct_positive_interval_count": (
            len(positive_interval_counts)
            if interval_frequency_complete
            else None
        ),
         "largest_positive_interval_limit": (
            largest_positive_interval_limit
        ),
        "largest_positive_interval_count": (
            len(retained_largest_intervals)
        ),
        "largest_positive_intervals": (
            retained_largest_intervals
        ),
    }