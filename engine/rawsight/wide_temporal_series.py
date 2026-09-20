from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Iterable


def _classify_value(
    value: object,
) -> tuple[str, float | None]:
    """
    Classify one observed value without assigning domain meaning.

    Only actual null/blank values are treated as missing.
    Tokens such as "N/A", "NULL", "unknown", and "-" remain
    non-numeric observations until a higher-level rule says otherwise.
    """

    if value is None:
        return "missing", None

    if isinstance(value, str):
        stripped = value.strip()

        if stripped == "":
            return "missing", None

        try:
            number = float(
                Decimal(stripped)
            )
        except (
            InvalidOperation,
            ValueError,
            OverflowError,
        ):
            return "non_numeric", None

    elif isinstance(value, bool):
        return "non_numeric", None

    elif isinstance(
        value,
        (int, float, Decimal),
    ):
        try:
            number = float(value)
        except (
            ValueError,
            OverflowError,
        ):
            return "non_numeric", None

    else:
        return "non_numeric", None

    if not math.isfinite(number):
        return "non_numeric", None

    return "numeric", number


def analyze_wide_temporal_series_observation(
    values: Iterable[object],
) -> dict:
    """
    Analyze one already ordered wide-temporal series.

    This function describes observations only. It does not decide
    whether increases, decreases, gaps, or other behaviour are valid
    for the business meaning of the series.

    Missing and non-numeric observations break adjacency. No transition
    is inferred across such a gap.

    Negative transition positions are retained so a later Explore layer
    can map them back to temporal-axis labels without reinterpreting the
    series.
    """

    temporal_value_count = 0

    numeric_value_count = 0
    missing_value_count = 0
    non_numeric_value_count = 0
    zero_value_count = 0

    numeric_min: float | None = None
    numeric_max: float | None = None

    adjacent_transition_count = 0
    positive_transition_count = 0
    negative_transition_count = 0
    unchanged_transition_count = 0

    largest_positive_change: float | None = None
    largest_negative_change: float | None = None

    negative_transitions = []

    previous_numeric: float | None = None
    previous_index: int | None = None
    previous_was_numeric = False

    for index, value in enumerate(values):
        temporal_value_count += 1

        kind, number = _classify_value(
            value
        )

        if kind == "missing":
            missing_value_count += 1
            previous_numeric = None
            previous_index = None
            previous_was_numeric = False
            continue

        if kind == "non_numeric":
            non_numeric_value_count += 1
            previous_numeric = None
            previous_index = None
            previous_was_numeric = False
            continue

        assert number is not None

        numeric_value_count += 1

        if number == 0:
            zero_value_count += 1

        if (
            numeric_min is None
            or number < numeric_min
        ):
            numeric_min = number

        if (
            numeric_max is None
            or number > numeric_max
        ):
            numeric_max = number

        if previous_was_numeric:
            assert previous_numeric is not None
            assert previous_index is not None

            change = number - previous_numeric
            adjacent_transition_count += 1

            if change > 0:
                positive_transition_count += 1

                if (
                    largest_positive_change is None
                    or change > largest_positive_change
                ):
                    largest_positive_change = (
                        change
                    )

            elif change < 0:
                negative_transition_count += 1

                if (
                    largest_negative_change is None
                    or change < largest_negative_change
                ):
                    largest_negative_change = (
                        change
                    )

                negative_transitions.append({
                    "from_index": previous_index,
                    "to_index": index,
                    "previous_value": (
                        previous_numeric
                    ),
                    "current_value": number,
                    "change": change,
                })

            else:
                unchanged_transition_count += 1

        previous_numeric = number
        previous_index = index
        previous_was_numeric = True

    if numeric_value_count == 0:
        classification = (
            "no_numeric_data"
        )
    elif adjacent_transition_count == 0:
        classification = (
            "insufficient_adjacent_observations"
        )
    elif (
        positive_transition_count == 0
        and negative_transition_count == 0
    ):
        classification = "constant"
    elif negative_transition_count == 0:
        classification = "non_decreasing"
    elif positive_transition_count == 0:
        classification = "non_increasing"
    else:
        classification = "mixed"

    return {
        "status": "measured",
        "analysis_kind": (
            "wide_temporal_series"
        ),
        "classification": classification,
        "temporal_value_count": (
            temporal_value_count
        ),
        "numeric_value_count": (
            numeric_value_count
        ),
        "missing_value_count": (
            missing_value_count
        ),
        "non_numeric_value_count": (
            non_numeric_value_count
        ),
        "zero_value_count": (
            zero_value_count
        ),
        "numeric_min": numeric_min,
        "numeric_max": numeric_max,
        "adjacent_transition_count": (
            adjacent_transition_count
        ),
        "positive_transition_count": (
            positive_transition_count
        ),
        "negative_transition_count": (
            negative_transition_count
        ),
        "unchanged_transition_count": (
            unchanged_transition_count
        ),
        "largest_positive_change": (
            largest_positive_change
        ),
        "largest_negative_change": (
            largest_negative_change
        ),
        "negative_transitions": (
            negative_transitions
        ),
    }
