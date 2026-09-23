from __future__ import annotations

from array import array
from collections.abc import Iterable

from rawsight.wide_temporal_series import (
    _classify_value,
)


_PERCENTILES = (
    ("p10", 0.10),
    ("p25", 0.25),
    ("p50", 0.50),
    ("p75", 0.75),
    ("p90", 0.90),
)


def _exact_percentile(
    sorted_values: list[float],
    quantile: float,
) -> float | None:
    """
    Return an exact percentile using linear interpolation between
    adjacent ordered observations.

    The percentile position is (n - 1) * quantile. This keeps the
    calculation deterministic and makes p50 identical to the median.
    """

    if not sorted_values:
        return None

    if not 0.0 <= quantile <= 1.0:
        raise ValueError(
            "quantile must be between 0 and 1"
        )

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (
        (len(sorted_values) - 1)
        * quantile
    )

    lower_index = int(position)
    upper_index = min(
        lower_index + 1,
        len(sorted_values) - 1,
    )

    lower_value = sorted_values[
        lower_index
    ]
    upper_value = sorted_values[
        upper_index
    ]

    fraction = position - lower_index

    return (
        lower_value
        + (
            upper_value
            - lower_value
        )
        * fraction
    )


class WideTemporalReferenceAnalyzer:
    """
    Build an exact reference population across aligned temporal series.

    Analysis responsibilities:
      - classify observed values using the same rules as the existing
        wide-temporal series analysis
      - accumulate per-position coverage and numeric totals
      - retain compact numeric observations for exact percentiles
      - calculate one distribution per temporal position

    Execution responsibilities intentionally remain elsewhere:
      - opening files
      - choosing exact vs approximate statistics
      - choosing batching / partitioning
      - assessing available machine resources
      - deciding whether to cache or reuse the result

    Exact percentiles necessarily retain numeric observations. Values
    are stored in array('d') rather than Python float lists so the
    retained numeric payload is 8 bytes per observation, excluding
    container/runtime overhead.
    """

    def __init__(
        self,
        position_count: int,
    ) -> None:
        if position_count < 1:
            raise ValueError(
                "position_count must be >= 1"
            )

        self.position_count = (
            position_count
        )
        self.population_count = 0

        self.numeric_count = [
            0
            for _ in range(
                position_count
            )
        ]
        self.missing_count = [
            0
            for _ in range(
                position_count
            )
        ]
        self.non_numeric_count = [
            0
            for _ in range(
                position_count
            )
        ]
        self.numeric_sum = [
            0.0
            for _ in range(
                position_count
            )
        ]
        self.numeric_values = [
            array("d")
            for _ in range(
                position_count
            )
        ]

    def observe_series(
        self,
        values: Iterable[object],
    ) -> None:
        """
        Observe one complete series across the shared temporal axis.

        Width mismatch is structural inconsistency and is rejected
        rather than silently padded or truncated.
        """

        observed_count = 0

        for position, value in enumerate(
            values
        ):
            if (
                position
                >= self.position_count
            ):
                raise ValueError(
                    "Observed series is wider "
                    "than the reference axis"
                )

            observed_count += 1

            kind, number = (
                _classify_value(
                    value
                )
            )

            if kind == "missing":
                self.missing_count[
                    position
                ] += 1
                continue

            if kind == "non_numeric":
                self.non_numeric_count[
                    position
                ] += 1
                continue

            assert number is not None

            self.numeric_count[
                position
            ] += 1
            self.numeric_sum[
                position
            ] += number
            self.numeric_values[
                position
            ].append(number)

        if (
            observed_count
            != self.position_count
        ):
            raise ValueError(
                "Observed series is narrower "
                "than the reference axis"
            )

        self.population_count += 1

    def observe_many(
        self,
        series: Iterable[
            Iterable[object]
        ],
    ) -> None:
        for values in series:
            self.observe_series(
                values
            )

    def result(self) -> dict:
        """
        Return exact per-position reference statistics.

        None means that a statistic could not be evaluated because the
        temporal position contained no numeric observations. A measured
        zero remains 0.0 and is never replaced by None.
        """

        positions = []

        for position in range(
            self.position_count
        ):
            numeric_count = (
                self.numeric_count[
                    position
                ]
            )

            if numeric_count == 0:
                mean = None
                percentiles = {
                    name: None
                    for name, _
                    in _PERCENTILES
                }
            else:
                mean = (
                    self.numeric_sum[
                        position
                    ]
                    / numeric_count
                )

                ordered_values = sorted(
                    self.numeric_values[
                        position
                    ]
                )

                percentiles = {
                    name: (
                        _exact_percentile(
                            ordered_values,
                            quantile,
                        )
                    )
                    for name, quantile
                    in _PERCENTILES
                }

            positions.append({
                "axis_index": position,
                "population_count": (
                    self.population_count
                ),
                "numeric_count": (
                    numeric_count
                ),
                "missing_count": (
                    self.missing_count[
                        position
                    ]
                ),
                "non_numeric_count": (
                    self.non_numeric_count[
                        position
                    ]
                ),
                "sum": (
                    self.numeric_sum[
                        position
                    ]
                    if numeric_count > 0
                    else None
                ),
                "mean": mean,
                "median": (
                    percentiles[
                        "p50"
                    ]
                ),
                **percentiles,
            })

        retained_numeric_count = sum(
            self.numeric_count
        )

        return {
            "status": "measured",
            "analysis_kind": (
                "wide_temporal_reference"
            ),
            "statistics_mode": "exact",
            "percentile_method": (
                "linear_interpolation_n_minus_1"
            ),
            "population_count": (
                self.population_count
            ),
            "temporal_position_count": (
                self.position_count
            ),
            "retained_numeric_value_count": (
                retained_numeric_count
            ),
            "retained_numeric_payload_bytes": (
                retained_numeric_count * 8
            ),
            "positions": positions,
        }
