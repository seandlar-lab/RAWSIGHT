from __future__ import annotations

from collections import Counter
from datetime import datetime

TEMPORAL_FORMATS = (
    # ISO dates.
    "%Y-%m-%d",

    # ISO-like timestamps.
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",

    # ISO timestamps with timezone.
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",

    # Slash-separated dates.
    "%m/%d/%y",
    "%m/%d/%Y",
    "%d/%m/%y",
    "%d/%m/%Y",

    # Slash-separated timestamps.
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
)


def parse_temporal_value(
    value: object,
) -> list[datetime]:
    """
    Return possible temporal interpretations of one value.

    Ambiguous representations are preserved as multiple
    candidates. No ordering or source-orientation assumptions
    are made here.
    """

    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    candidates = []

    for temporal_format in TEMPORAL_FORMATS:
        try:
            parsed = datetime.strptime(
                text,
                temporal_format,
            )

            if parsed not in candidates:
                candidates.append(parsed)

        except ValueError:
            continue

    return candidates


def parse_temporal_header_value(
    value: object,
) -> list[datetime]:
    """
    Compatibility wrapper for existing header-oriented callers.
    """

    return parse_temporal_value(value)


def find_temporal_runs(
    values: list[object],
    min_length: int = 3,
) -> list[dict]:
    """
    Find contiguous runs of date-like values in a sequence.

    The sequence may originate from a row, a column, or another
    source representation. Orientation is deliberately unknown
    at this level.
    """

    runs = []
    run_start = None

    for index, value in enumerate(values):
        candidates = parse_temporal_value(value)

        if candidates:
            if run_start is None:
                run_start = index
            continue

        if run_start is not None:
            run_length = index - run_start

            if run_length >= min_length:
                runs.append({
                    "start_index": run_start,
                    "end_index": index - 1,
                    "length": run_length,
                })

            run_start = None

    if run_start is not None:
        run_length = len(values) - run_start

        if run_length >= min_length:
            runs.append({
                "start_index": run_start,
                "end_index": len(values) - 1,
                "length": run_length,
            })

    return runs


def find_temporal_header_runs(
    row: list[object],
    min_length: int = 3,
) -> list[dict]:
    """
    Find temporal runs horizontally in a candidate header row.

    Horizontal extraction is specific to this wrapper.
    Run detection itself is orientation-neutral.
    """

    return find_temporal_runs(
        row,
        min_length=min_length,
    )


def evaluate_temporal_sequence(
    values: list[object],
) -> list[dict]:
    """
    Evaluate possible temporal interpretations of a sequence.

    Parsing and temporal typing are independent of row order.
    Repeated, unsorted, increasing, and decreasing timestamps
    are all valid temporal data.

    Ambiguous format interpretations are preserved.
    """

    candidates = []
    seen_sequences = set()

    for temporal_format in TEMPORAL_FORMATS:
        parsed_dates = []

        for value in values:
            try:
                parsed = datetime.strptime(
                    str(value).strip(),
                    temporal_format,
                )
                parsed_dates.append(parsed)

            except ValueError:
                parsed_dates = []
                break

        if not parsed_dates:
            continue

        sequence_key = tuple(parsed_dates)

        if sequence_key in seen_sequences:
            continue

        seen_sequences.add(sequence_key)

        candidates.append({
            "format": temporal_format,
            "first": parsed_dates[0],
            "last": parsed_dates[-1],
            "count": len(parsed_dates),
            "distinct_count": len(
                set(parsed_dates)
            ),
            "range_start": min(parsed_dates),
            "range_end": max(parsed_dates),
        })

    return candidates


def normalize_temporal_sequence(
    values: list[object],
    date_format: str,
) -> list[datetime]:
    """
    Normalize temporal values to datetime objects.

    Source format, orientation, and structural position are
    deliberately outside this function.
    """

    return [
        datetime.strptime(
            str(value).strip(),
            date_format,
        )
        for value in values
    ]


def analyze_temporal_order(
    timestamps: list[datetime],
) -> dict:
    """
    Describe observed timestamp ordering without treating
    ordering as a requirement for temporal data.
    """

    if len(timestamps) < 2:
        return {
            "order": "single_or_empty",
            "positive_transitions": 0,
            "zero_transitions": 0,
            "negative_transitions": 0,
            "duplicate_count": (
                len(timestamps)
                - len(set(timestamps))
            ),
        }

    deltas = [
        (
            current - previous
        ).total_seconds()
        for previous, current in zip(
            timestamps,
            timestamps[1:],
        )
    ]

    positive = sum(
        delta > 0
        for delta in deltas
    )

    zero = sum(
        delta == 0
        for delta in deltas
    )

    negative = sum(
        delta < 0
        for delta in deltas
    )

    if positive and not zero and not negative:
        order = "strictly_increasing"

    elif positive and zero and not negative:
        order = "non_decreasing"

    elif negative and not zero and not positive:
        order = "strictly_decreasing"

    elif negative and zero and not positive:
        order = "non_increasing"

    elif not positive and zero and not negative:
        order = "constant"

    else:
        order = "unordered"

    return {
        "order": order,
        "positive_transitions": positive,
        "zero_transitions": zero,
        "negative_transitions": negative,
        "duplicate_count": (
            len(timestamps)
            - len(set(timestamps))
        ),
    }


def analyze_temporal_cadence(
    timestamps: list[datetime],
) -> dict:
    """
    Analyze cadence from the canonical temporal axis.

    Duplicate timestamps and source row ordering do not affect
    cadence. Distinct timestamps are ordered chronologically
    before intervals are calculated.
    """

    axis = sorted(
        set(timestamps)
    )

    if len(axis) < 2:
        return {
            "distinct_timestamp_count": len(axis),
            "interval_count": 0,
            "dominant_interval_seconds": None,
            "dominant_interval_count": 0,
            "cadence_consistency": None,
        }

    intervals = [
        int(
            (
                current - previous
            ).total_seconds()
        )
        for previous, current in zip(
            axis,
            axis[1:],
        )
    ]

    interval_counts = Counter(intervals)

    (
        dominant_interval,
        dominant_count,
    ) = interval_counts.most_common(1)[0]

    return {
        "distinct_timestamp_count": len(axis),
        "interval_count": len(intervals),
        "dominant_interval_seconds": dominant_interval,
        "dominant_interval_count": dominant_count,
        "cadence_consistency": (
            dominant_count / len(intervals)
        ),
    }


def analyze_temporal_values(
    values: list[object],
) -> list[dict]:
    """
    Analyze a temporal sequence independently of source format,
    orientation, structural position, and observed ordering.

    Multiple valid temporal interpretations are preserved.
    """

    evaluated = evaluate_temporal_sequence(
        values
    )

    analyses = []

    for candidate in evaluated:
        timestamps = normalize_temporal_sequence(
            values,
            candidate["format"],
        )

        analyses.append({
            **candidate,
            "order_analysis": analyze_temporal_order(
                timestamps,
            ),
            "cadence": analyze_temporal_cadence(
                timestamps,
            ),
        })

    return analyses


def build_temporal_axis_candidate(
    detected: dict,
) -> dict:
    """
    Build a JSON-safe temporal-axis candidate from analyzed
    temporal evidence.

    The candidate describes observed structure only. It does
    not decide whether the sequence is a header, field, index,
    or record dimension.
    """

    cadence = detected["cadence"]
    order = detected["order_analysis"]

    return {
        "orientation": detected["orientation"],
        "sequence_index": detected["sequence_index"],
        "start_index": detected["start_index"],
        "end_index": detected["end_index"],
        "length": detected["length"],
        "format": detected["format"],
        "range_start": detected[
            "range_start"
        ].isoformat(),
        "range_end": detected[
            "range_end"
        ].isoformat(),
        "order": order["order"],
        "count": detected["count"],
        "distinct_count": detected[
            "distinct_count"
        ],
        "duplicate_count": order[
            "duplicate_count"
        ],
        "dominant_interval_seconds": cadence[
            "dominant_interval_seconds"
        ],
        "cadence_consistency": cadence[
            "cadence_consistency"
        ],
    }


def evaluate_temporal_header_run(
    row: list[object],
    run: dict,
) -> list[dict]:
    """
    Evaluate a temporal run detected horizontally in a
    candidate header row.

    Extraction is orientation-specific. Temporal sequence
    evaluation itself is orientation-neutral.
    """

    start_index = run["start_index"]
    end_index = run["end_index"]

    values = row[
        start_index:end_index + 1
    ]

    return evaluate_temporal_sequence(values)
