from __future__ import annotations

from typing import Iterable

from rawsight.wide_temporal_series import (
    analyze_wide_temporal_series_observation,
)


class WideTemporalAnalyzer:
    """
    Incremental analyzer for wide temporal value series.

    This class contains aggregate analysis logic only. It does not open
    files, decide batch sizes, inspect available memory, or choose
    execution strategies.

    One-series observation is delegated to
    analyze_wide_temporal_series_observation so the same deterministic
    rules can later be reused by Explore without duplicating them.
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

    def observe_series(
        self,
        values: Iterable[object],
    ) -> None:
        """
        Observe one temporal series and merge its measurements into the
        aggregate result.

        The one-series result itself is intentionally not retained here,
        keeping aggregate analysis memory independent of the number of
        source series.
        """

        observation = (
            analyze_wide_temporal_series_observation(
                values
            )
        )

        self.series_count += 1

        self.temporal_value_count += (
            observation[
                "temporal_value_count"
            ]
        )

        self.numeric_value_count += (
            observation[
                "numeric_value_count"
            ]
        )
        self.missing_value_count += (
            observation[
                "missing_value_count"
            ]
        )
        self.non_numeric_value_count += (
            observation[
                "non_numeric_value_count"
            ]
        )
        self.zero_value_count += (
            observation[
                "zero_value_count"
            ]
        )

        series_min = observation[
            "numeric_min"
        ]
        series_max = observation[
            "numeric_max"
        ]

        if (
            series_min is not None
            and (
                self.numeric_min is None
                or series_min < self.numeric_min
            )
        ):
            self.numeric_min = series_min

        if (
            series_max is not None
            and (
                self.numeric_max is None
                or series_max > self.numeric_max
            )
        ):
            self.numeric_max = series_max

        self.adjacent_transition_count += (
            observation[
                "adjacent_transition_count"
            ]
        )
        self.positive_transition_count += (
            observation[
                "positive_transition_count"
            ]
        )
        self.negative_transition_count += (
            observation[
                "negative_transition_count"
            ]
        )
        self.unchanged_transition_count += (
            observation[
                "unchanged_transition_count"
            ]
        )

        series_largest_positive = (
            observation[
                "largest_positive_change"
            ]
        )
        series_largest_negative = (
            observation[
                "largest_negative_change"
            ]
        )

        if (
            series_largest_positive
            is not None
            and (
                self.largest_positive_change
                is None
                or series_largest_positive
                > self.largest_positive_change
            )
        ):
            self.largest_positive_change = (
                series_largest_positive
            )

        if (
            series_largest_negative
            is not None
            and (
                self.largest_negative_change
                is None
                or series_largest_negative
                < self.largest_negative_change
            )
        ):
            self.largest_negative_change = (
                series_largest_negative
            )

        if (
            observation[
                "missing_value_count"
            ]
            > 0
        ):
            self.series_with_missing_values += 1

        if (
            observation[
                "non_numeric_value_count"
            ]
            > 0
        ):
            self.series_with_non_numeric_values += 1

        if (
            observation[
                "negative_transition_count"
            ]
            > 0
        ):
            self.series_with_negative_transitions += 1

        classification = observation[
            "classification"
        ]

        self.series_classification[
            classification
        ] += 1

    def observe_many(
        self,
        series: Iterable[
            Iterable[object]
        ],
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
            "analysis_kind": (
                "wide_temporal_values"
            ),
            "series_count": self.series_count,
            "temporal_value_count": (
                self.temporal_value_count
            ),
            "numeric_value_count": (
                self.numeric_value_count
            ),
            "missing_value_count": (
                self.missing_value_count
            ),
            "non_numeric_value_count": (
                self.non_numeric_value_count
            ),
            "zero_value_count": (
                self.zero_value_count
            ),
            "numeric_min": self.numeric_min,
            "numeric_max": self.numeric_max,
            "adjacent_transition_count": (
                self.adjacent_transition_count
            ),
            "positive_transition_count": (
                self.positive_transition_count
            ),
            "negative_transition_count": (
                self.negative_transition_count
            ),
            "unchanged_transition_count": (
                self.unchanged_transition_count
            ),
            "largest_positive_change": (
                self.largest_positive_change
            ),
            "largest_negative_change": (
                self.largest_negative_change
            ),
            "series_with_missing_values": (
                self.series_with_missing_values
            ),
            "series_with_non_numeric_values": (
                self.series_with_non_numeric_values
            ),
            "series_with_negative_transitions": (
                self.series_with_negative_transitions
            ),
            "series_classification": dict(
                self.series_classification
            ),
        }


def analyze_wide_temporal_series(
    series: Iterable[
        Iterable[object]
    ],
) -> dict:
    """
    Convenience wrapper for callers that already have an iterable
    of temporal series.
    """

    analyzer = WideTemporalAnalyzer()
    analyzer.observe_many(series)
    return analyzer.result()
