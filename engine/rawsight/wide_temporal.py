from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Iterable


def _classify_value(value: object) -> tuple[str, float | None]:
    """
    Classify one observed value without assigning domain meaning.

    Returns:
        ("missing", None)
        ("numeric", number)
        ("non_numeric", None)

    Only actual null/blank values are treated as missing.
    Tokens such as "N/A", "NULL", "unknown", "-" remain
    non-numeric observations until a higher-level rule says otherwise.
    """

    if value is None:
        return "missing", None

    if isinstance(value, str):
        stripped = value.strip()

        if stripped == "":
            return "missing", None

        try:
            number = float(Decimal(stripped))
        except (InvalidOperation, ValueError, OverflowError):
            return "non_numeric", None

    elif isinstance(value, bool):
        return "non_numeric", None

    elif isinstance(value, (int, float, Decimal)):
        try:
            number = float(value)
        except (ValueError, OverflowError):
            return "non_numeric", None

    else:
        return "non_numeric", None

    if not math.isfinite(number):
        return "non_numeric", None

    return "numeric", number


class WideTemporalAnalyzer:
    """
    Incremental analyzer for wide temporal value series.

    This class contains analysis logic only. It does not open files,
    decide batch sizes, inspect available memory, or choose execution
    strategies. Those responsibilities belong to source/execution and
    resource-assessment layers.

    A caller supplies one series at a time. Each series is expected to
    represent values ordered along an already detected temporal axis.
    """

    def __init__(self) -> None:
        self.series_count = 0
        self.temporal_value_count = 0

        self.numeric_value_count = 0
        self.missing_value_count = 0
        self.non_numeric_value_count = 0
        self.zero_value_count = 0

        self.numeric_min: float | None = None
        self.numeric_max: float | None = None

        self.adjacent_transition_count = 0
        self.positive_transition_count = 0
        self.negative_transition_count = 0
        self.unchanged_transition_count = 0

        self.largest_positive_change: float | None = None
        self.largest_negative_change: float | None = None

        self.series_with_missing_values = 0
        self.series_with_non_numeric_values = 0
        self.series_with_negative_transitions = 0

        self.series_classification = {
            "no_numeric_data": 0,
            "insufficient_adjacent_observations": 0,
            "constant": 0,
            "non_decreasing": 0,
            "non_increasing": 0,
            "mixed": 0,
        }

    def observe_series(self, values: Iterable[object]) -> None:
        """
        Observe one temporal series.

        Missing or non-numeric observations break adjacency. We do not
        infer a transition across such a gap.

        No observation is classified as an error here. The analyzer
        reports structure and behaviour only.
        """

        self.series_count += 1

        series_numeric_count = 0
        series_missing_count = 0
        series_non_numeric_count = 0

        series_positive = 0
        series_negative = 0
        series_unchanged = 0

        previous_numeric: float | None = None
        previous_was_numeric = False

        for value in values:
            self.temporal_value_count += 1

            kind, number = _classify_value(value)

            if kind == "missing":
                self.missing_value_count += 1
                series_missing_count += 1
                previous_numeric = None
                previous_was_numeric = False
                continue

            if kind == "non_numeric":
                self.non_numeric_value_count += 1
                series_non_numeric_count += 1
                previous_numeric = None
                previous_was_numeric = False
                continue

            assert number is not None

            self.numeric_value_count += 1
            series_numeric_count += 1

            if number == 0:
                self.zero_value_count += 1

            if self.numeric_min is None or number < self.numeric_min:
                self.numeric_min = number

            if self.numeric_max is None or number > self.numeric_max:
                self.numeric_max = number

            if previous_was_numeric:
                assert previous_numeric is not None

                change = number - previous_numeric
                self.adjacent_transition_count += 1

                if change > 0:
                    self.positive_transition_count += 1
                    series_positive += 1

                    if (
                        self.largest_positive_change is None
                        or change > self.largest_positive_change
                    ):
                        self.largest_positive_change = change

                elif change < 0:
                    self.negative_transition_count += 1
                    series_negative += 1

                    if (
                        self.largest_negative_change is None
                        or change < self.largest_negative_change
                    ):
                        self.largest_negative_change = change

                else:
                    self.unchanged_transition_count += 1
                    series_unchanged += 1

            previous_numeric = number
            previous_was_numeric = True

        if series_missing_count > 0:
            self.series_with_missing_values += 1

        if series_non_numeric_count > 0:
            self.series_with_non_numeric_values += 1

        if series_negative > 0:
            self.series_with_negative_transitions += 1

        transition_count = (
            series_positive
            + series_negative
            + series_unchanged
        )

        if series_numeric_count == 0:
            classification = "no_numeric_data"
        elif transition_count == 0:
            classification = "insufficient_adjacent_observations"
        elif series_positive == 0 and series_negative == 0:
            classification = "constant"
        elif series_negative == 0:
            classification = "non_decreasing"
        elif series_positive == 0:
            classification = "non_increasing"
        else:
            classification = "mixed"

        self.series_classification[classification] += 1

    def observe_many(
        self,
        series: Iterable[Iterable[object]],
    ) -> None:
        """
        Observe any iterable of temporal series.

        The iterable may be backed by a list, generator, cursor,
        streaming reader, or future execution layer.
        """

        for values in series:
            self.observe_series(values)

    def result(self) -> dict:
        """
        Return JSON-safe accumulated observations.
        """

        return {
            "status": "measured",
            "analysis_kind": "wide_temporal_values",
            "series_count": self.series_count,
            "temporal_value_count": self.temporal_value_count,
            "numeric_value_count": self.numeric_value_count,
            "missing_value_count": self.missing_value_count,
            "non_numeric_value_count": self.non_numeric_value_count,
            "zero_value_count": self.zero_value_count,
            "numeric_min": self.numeric_min,
            "numeric_max": self.numeric_max,
            "adjacent_transition_count": self.adjacent_transition_count,
            "positive_transition_count": self.positive_transition_count,
            "negative_transition_count": self.negative_transition_count,
            "unchanged_transition_count": self.unchanged_transition_count,
            "largest_positive_change": self.largest_positive_change,
            "largest_negative_change": self.largest_negative_change,
            "series_with_missing_values": self.series_with_missing_values,
            "series_with_non_numeric_values": (
                self.series_with_non_numeric_values
            ),
            "series_with_negative_transitions": (
                self.series_with_negative_transitions
            ),
            "series_classification": dict(self.series_classification),
        }


def analyze_wide_temporal_series(
    series: Iterable[Iterable[object]],
) -> dict:
    """
    Convenience wrapper for callers that already have an iterable
    of temporal series.
    """

    analyzer = WideTemporalAnalyzer()
    analyzer.observe_many(series)
    return analyzer.result()
