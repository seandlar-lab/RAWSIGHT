from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Sequence

from rawsight.wide_temporal_reference import _exact_percentile
from rawsight.wide_temporal_series import _classify_value


def _percentile_position_midrank(
    sorted_values: Sequence[float],
    value: float,
) -> float | None:
    """Exact empirical percentile position using midrank tie handling."""
    population_count = len(sorted_values)

    if population_count == 0:
        return None

    lower_index = bisect_left(sorted_values, value)
    upper_index = bisect_right(sorted_values, value)

    count_less = lower_index
    count_equal = upper_index - lower_index

    return (
        (count_less + 0.5 * count_equal)
        / population_count
        * 100.0
    )


def compare_wide_temporal_series_to_reference(
    values: Iterable[object],
    ordered_reference_values: Sequence[Sequence[float]],
) -> dict:
    """
    Compare one aligned series with one exact numeric reference
    distribution per temporal position.

    The reference populations must already be sorted ascending.
    This function assigns no domain meaning and does not label
    observations as anomalies or errors.
    """
    position_count = len(ordered_reference_values)

    if position_count < 1:
        raise ValueError(
            "ordered_reference_values must contain at least one position"
        )

    positions: list[dict] = []

    observed_count = 0
    evaluated_count = 0
    missing_count = 0
    non_numeric_count = 0
    reference_without_numeric_count = 0

    percentile_min: float | None = None
    percentile_max: float | None = None
    difference_min: float | None = None
    difference_max: float | None = None

    for axis_index, value in enumerate(values):
        if axis_index >= position_count:
            raise ValueError(
                "Selected series is wider than the reference axis"
            )

        observed_count += 1

        kind, number = _classify_value(value)
        reference_values = ordered_reference_values[axis_index]
        reference_numeric_count = len(reference_values)

        reference_median = (
            _exact_percentile(
                reference_values,  # type: ignore[arg-type]
                0.50,
            )
            if reference_numeric_count > 0
            else None
        )

        if kind == "missing":
            missing_count += 1
            positions.append({
                "axis_index": axis_index,
                "selected_value_kind": "missing",
                "selected_value": None,
                "reference_numeric_count": reference_numeric_count,
                "reference_median": reference_median,
                "difference_from_median": None,
                "percentile_position": None,
            })
            continue

        if kind == "non_numeric":
            non_numeric_count += 1
            positions.append({
                "axis_index": axis_index,
                "selected_value_kind": "non_numeric",
                "selected_value": None,
                "reference_numeric_count": reference_numeric_count,
                "reference_median": reference_median,
                "difference_from_median": None,
                "percentile_position": None,
            })
            continue

        assert number is not None

        if reference_numeric_count == 0:
            reference_without_numeric_count += 1
            positions.append({
                "axis_index": axis_index,
                "selected_value_kind": "numeric",
                "selected_value": number,
                "reference_numeric_count": 0,
                "reference_median": None,
                "difference_from_median": None,
                "percentile_position": None,
            })
            continue

        assert reference_median is not None

        difference_from_median = number - reference_median
        percentile_position = _percentile_position_midrank(
            reference_values,
            number,
        )

        assert percentile_position is not None

        evaluated_count += 1

        percentile_min = (
            percentile_position
            if percentile_min is None
            else min(percentile_min, percentile_position)
        )
        percentile_max = (
            percentile_position
            if percentile_max is None
            else max(percentile_max, percentile_position)
        )
        difference_min = (
            difference_from_median
            if difference_min is None
            else min(difference_min, difference_from_median)
        )
        difference_max = (
            difference_from_median
            if difference_max is None
            else max(difference_max, difference_from_median)
        )

        positions.append({
            "axis_index": axis_index,
            "selected_value_kind": "numeric",
            "selected_value": number,
            "reference_numeric_count": reference_numeric_count,
            "reference_median": reference_median,
            "difference_from_median": difference_from_median,
            "percentile_position": percentile_position,
        })

    if observed_count != position_count:
        raise ValueError(
            "Selected series is narrower than the reference axis"
        )

    return {
        "status": "measured",
        "analysis_kind": "wide_temporal_reference_comparison",
        "percentile_position_method": "exact_empirical_midrank",
        "temporal_position_count": position_count,
        "evaluated_position_count": evaluated_count,
        "selected_missing_count": missing_count,
        "selected_non_numeric_count": non_numeric_count,
        "reference_without_numeric_count": reference_without_numeric_count,
        "percentile_position_min": percentile_min,
        "percentile_position_max": percentile_max,
        "difference_from_median_min": difference_min,
        "difference_from_median_max": difference_max,
        "positions": positions,
    }
