import csv
import json
from collections import Counter
from pathlib import Path
from decimal import Decimal, InvalidOperation
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

import duckdb

def preview_csv_structure(
    file_path: str,
    max_rows: int = 20,
) -> dict:
    """
    Read the first CSV records without assuming that any row is a header.

    This is intentionally separate from DuckDB type/header inference so
    RAWSIGHT can inspect wide datasets and multi-row metadata/header bands.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        sample = handle.read(65536)
        handle.seek(0)

        try:
            dialect = csv.Sniffer().sniff(
                sample,
                delimiters=",;\t|",
            )
        except csv.Error:
            dialect = csv.excel

        reader = csv.reader(
            handle,
            dialect,
        )

        rows = []

        for _, row in zip(range(max_rows), reader):
            rows.append(row)

    row_widths = [len(row) for row in rows]

    return {
        "preview_row_count": len(rows),
        "column_count": max(row_widths, default=0),
        "row_widths": row_widths,
        "rows": rows,
    }

def create_structural_model(
    *,
    detected_format: str,
    format_confidence: float,
    inspection_status: str,
    extension: str,
    file_size_bytes: int,
) -> dict:
    """
    Create the format-neutral structural model used by RAWSIGHT.

    Format-specific inspectors may populate additional details,
    but downstream analysis should be able to rely on this shape.
    """

    return {
        "source": {
            "extension": extension,
            "file_size_bytes": file_size_bytes,
        },
        "format": {
            "detected_format": detected_format,
            "format_confidence": format_confidence,
            "inspection_status": inspection_status,
        },
        "physical_structure": {},
        "logical_structure": {
            "structure_type": "unknown",
            "header_band": None,
            "descriptor_fields": [],
            "temporal_axis": None,
            "measures": [],
            "dimensions": [],
            "candidate_data_start": None,
        },
    }

def attach_structural_model(
    inspection: dict,
    physical_structure: dict | None = None,
    logical_structure: dict | None = None,
) -> dict:
    """
    Attach the common RAWSIGHT structural model while preserving
    all format-specific inspection details.
    """

    model = create_structural_model(
        detected_format=inspection.get(
            "detected_format",
            "unknown",
        ),
        format_confidence=inspection.get(
            "format_confidence",
            0.0,
        ),
        inspection_status=inspection.get(
            "inspection_status",
            "unknown",
        ),
        extension=inspection.get(
            "extension",
            "",
        ),
        file_size_bytes=inspection.get(
            "file_size_bytes",
            0,
        ),
    )
    if logical_structure is not None:
        model["logical_structure"] = logical_structure

    return {
        **inspection,
        "structural_model": model,
    }

def build_delimited_physical_structure(
    inspection: dict,
) -> dict:
    """
    Build the physical structure description for
    delimited text sources.
    """

    return {
        "kind": "delimited_text",
        "encoding": inspection.get("encoding"),
        "delimiter": inspection.get("delimiter"),
        "quotechar": inspection.get("quotechar"),
        "preview_record_count": inspection.get(
            "preview_record_count",
            0,
        ),
        "dominant_field_count": inspection.get(
            "dominant_field_count",
        ),
        "field_count_consistency": inspection.get(
            "field_count_consistency",
        ),
        "row_widths": inspection.get(
            "row_widths",
            [],
        ),
    }

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

def extract_tabular_sequence(
    rows: list[list[object]],
    *,
    orientation: str,
    index: int,
) -> list[object]:
    """
    Extract one sequence from a two-dimensional tabular preview.

    Horizontal and vertical orientation are handled only at this
    extraction boundary. Missing cells in ragged rows are
    preserved as None so downstream detection can see the gap.
    """

    if orientation == "horizontal":
        if index < 0 or index >= len(rows):
            return []

        return list(rows[index])

    if orientation == "vertical":
        if index < 0:
            return []

        return [
            (
                row[index]
                if index < len(row)
                else None
            )
            for row in rows
        ]

    raise ValueError(
        f"Unsupported orientation: {orientation}"
    )    

def classify_structural_value(
    value: object,
) -> str:
    """
    Classify one observed value structurally.

    Classification is deliberately conservative and does not
    assign business semantics such as measure, identifier,
    dimension, or missing-value marker.
    """

    if value is None:
        return "empty"

    text = str(value).strip()

    if not text:
        return "empty"

    if parse_temporal_value(value):
        return "temporal"

    try:
        numeric = Decimal(text)

        if numeric.is_finite():
            return "numeric"

    except InvalidOperation:
        pass

    return "text"

def profile_structural_sequence(
    values: list[object],
) -> dict:
    """
    Profile one structural sequence without assigning semantics.

    The sequence may represent a row, a column, or another
    ordered collection. No header/data assumption is made.
    """

    type_counts = {
        "empty": 0,
        "temporal": 0,
        "numeric": 0,
        "text": 0,
    }

    for value in values:
        value_type = classify_structural_value(
            value
        )

        type_counts[value_type] += 1

    value_count = len(values)
    nonempty_count = (
        value_count - type_counts["empty"]
    )

    def fraction(
        count: int,
    ) -> float:
        if not nonempty_count:
            return 0.0

        return count / nonempty_count

    return {
        "value_count": value_count,
        "nonempty_count": nonempty_count,
        "empty_count": type_counts["empty"],
        "temporal_candidate_count": type_counts[
            "temporal"
        ],
        "numeric_candidate_count": type_counts[
            "numeric"
        ],
        "text_candidate_count": type_counts[
            "text"
        ],
        "temporal_fraction": fraction(
            type_counts["temporal"]
        ),
        "numeric_fraction": fraction(
            type_counts["numeric"]
        ),
        "text_fraction": fraction(
            type_counts["text"]
        ),
    }


def profile_tabular_structure(
    rows: list[list[object]],
) -> dict:
    """
    Profile both orientations of a tabular preview.

    Profiling is structural only. Rows and columns are not
    classified as headers, dimensions, measures, or data here.
    """

    horizontal = []

    for row_index in range(len(rows)):
        values = extract_tabular_sequence(
            rows,
            orientation="horizontal",
            index=row_index,
        )

        horizontal.append({
            "sequence_index": row_index,
            **profile_structural_sequence(values),
        })

    max_width = max(
        (len(row) for row in rows),
        default=0,
    )

    vertical = []

    for column_index in range(max_width):
        values = extract_tabular_sequence(
            rows,
            orientation="vertical",
            index=column_index,
        )

        vertical.append({
            "sequence_index": column_index,
            **profile_structural_sequence(values),
        })

    return {
        "horizontal": horizontal,
        "vertical": vertical,
    }

def find_tabular_temporal_runs(
    rows: list[list[object]],
    min_length: int = 3,
) -> list[dict]:
    """
    Find temporal runs in both orientations of a tabular preview.

    This function reports where temporal-looking sequences occur.
    It does not assign semantic meaning such as header, date
    column, measure, or dimension.
    """

    results = []

    # Horizontal sequences.
    for row_index in range(len(rows)):
        values = extract_tabular_sequence(
            rows,
            orientation="horizontal",
            index=row_index,
        )

        for run in find_temporal_runs(
            values,
            min_length=min_length,
        ):
            results.append({
                "orientation": "horizontal",
                "sequence_index": row_index,
                **run,
            })

    # Vertical sequences.
    max_width = max(
        (len(row) for row in rows),
        default=0,
    )

    for column_index in range(max_width):
        values = extract_tabular_sequence(
            rows,
            orientation="vertical",
            index=column_index,
        )

        for run in find_temporal_runs(
            values,
            min_length=min_length,
        ):
            results.append({
                "orientation": "vertical",
                "sequence_index": column_index,
                **run,
            })

    return results

def extract_tabular_run_values(
    rows: list[list[object]],
    run: dict,
) -> list[object]:
    """
    Extract the values belonging to one detected tabular run.

    Orientation and position are handled at this boundary.
    Downstream analysis receives only the resulting sequence.
    """

    sequence = extract_tabular_sequence(
        rows,
        orientation=run["orientation"],
        index=run["sequence_index"],
    )

    start_index = run["start_index"]
    end_index = run["end_index"]

    return sequence[
        start_index:end_index + 1
    ]

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

def analyze_tabular_logical_structure(
    rows: list[list[object]],
) -> dict:
    """
    Derive logical structure from a tabular preview.

    Only evidence supported by the observed data is reported.
    Header rows, descriptors, dimensions, measures, and data
    start positions are deliberately left unresolved here.
    """

    logical_structure = {
        "structure_type": "tabular",
        "header_band": None,
        "descriptor_fields": [],
        "temporal_axis": None,
        "measures": [],
        "dimensions": [],
        "candidate_data_start": None,
    }

    runs = find_tabular_temporal_runs(rows)

    analyzed_runs = []

    for run in runs:
        values = extract_tabular_run_values(
            rows,
            run,
        )

        analyses = analyze_temporal_values(
            values,
        )

        for analysis in analyses:
            analyzed_runs.append({
                **run,
                **analysis,
            })

    if not analyzed_runs:
        return logical_structure

    logical_structure["structure_type"] = (
        "tabular_temporal"
    )

    # Preserve ambiguity rather than choosing arbitrarily.
    if len(analyzed_runs) != 1:
        return logical_structure

    detected = analyzed_runs[0]

    cadence = detected["cadence"]
    order = detected["order_analysis"]

    logical_structure["temporal_axis"] = {
        "orientation": detected["orientation"],
        "sequence_index": detected["sequence_index"],
        "start_index": detected["start_index"],
        "end_index": detected["end_index"],
        "length": detected["length"],
        "format": detected["format"],
        "range_start": (
            detected["range_start"].isoformat()
        ),
        "range_end": (
            detected["range_end"].isoformat()
        ),
        "order": order["order"],
        "distinct_count": detected[
            "distinct_count"
        ],
        "dominant_interval_seconds": cadence[
            "dominant_interval_seconds"
        ],
        "cadence_consistency": cadence[
            "cadence_consistency"
        ],
    }

    return logical_structure

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

def inspect_delimited_file(
    file_path: str,
    max_rows: int = 20,
) -> dict:
    """
    Inspect a possible delimited text file without assuming
    that the file extension is correct or that the first row
    is the only header row.

    This is a physical/structural preflight only.
    It does not modify how datasets are currently opened.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    sample_bytes = path.read_bytes()[:262144]

    if not sample_bytes:
        return {
            "extension": path.suffix.lower(),
            "file_size_bytes": 0,
            "likely_text": True,
            "encoding": None,
            "delimiter": None,
            "quotechar": None,
            "physical_format": "empty",
            "format_confidence": 0.0,
            "preview_record_count": 0,
            "dominant_field_count": 0,
            "field_count_consistency": 0.0,
            "row_widths": [],
            "rows": [],
        }

    control_bytes = sum(
        1
        for value in sample_bytes
        if value < 9 or 13 < value < 32
    )

    control_ratio = (
        control_bytes / len(sample_bytes)
    )

    likely_binary = (
        b"\x00" in sample_bytes
        or control_ratio > 0.02
    )

    if likely_binary:
        return {
            "extension": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size,
            "likely_text": False,
            "encoding": None,
            "delimiter": None,
            "quotechar": None,
            "physical_format": "binary_or_unknown",
            "format_confidence": 0.0,
            "preview_record_count": 0,
            "dominant_field_count": 0,
            "field_count_consistency": 0.0,
            "row_widths": [],
            "rows": [],
        }

    encoding = None
    sample_text = None

    for candidate in (
        "utf-8-sig",
        "cp1252",
    ):
        try:
            sample_text = sample_bytes.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue

    if sample_text is None:
        return {
            "extension": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size,
            "likely_text": False,
            "encoding": None,
            "delimiter": None,
            "quotechar": None,
            "physical_format": "text_encoding_unknown",
            "format_confidence": 0.2,
            "preview_record_count": 0,
            "dominant_field_count": 0,
            "field_count_consistency": 0.0,
            "row_widths": [],
            "rows": [],
        }

    delimiter = None
    quotechar = None
    dialect = None

    try:
        dialect = csv.Sniffer().sniff(
            sample_text,
            delimiters=",;\t|",
        )
        delimiter = dialect.delimiter
        quotechar = dialect.quotechar
    except csv.Error:
        pass

    rows = []

    if dialect is not None:
        with path.open(
            "r",
            encoding=encoding,
            newline="",
        ) as handle:
            reader = csv.reader(
                handle,
                dialect,
            )

            for _, row in zip(
                range(max_rows),
                reader,
            ):
                rows.append(row)

    row_widths = [
        len(row)
        for row in rows
    ]

    dominant_field_count = 0
    field_count_consistency = 0.0

    if row_widths:
        width_counts = Counter(row_widths)

        dominant_field_count, dominant_count = (
            width_counts.most_common(1)[0]
        )

        field_count_consistency = (
            dominant_count / len(row_widths)
        )

    confidence = 0.4

    if delimiter is not None:
        confidence += 0.25

    if dominant_field_count > 1:
        confidence += 0.2

    if field_count_consistency >= 0.9:
        confidence += 0.15
    elif field_count_consistency >= 0.75:
        confidence += 0.1

    confidence = min(confidence, 1.0)

    physical_format = (
        "delimited_text"
        if (
            delimiter is not None
            and dominant_field_count > 1
            and confidence >= 0.75
        )
        else "text"
    )

    return {
        "extension": path.suffix.lower(),
        "file_size_bytes": path.stat().st_size,
        "likely_text": True,
        "encoding": encoding,
        "delimiter": delimiter,
        "quotechar": quotechar,
        "physical_format": physical_format,
        "format_confidence": round(confidence, 2),
        "preview_record_count": len(rows),
        "dominant_field_count": dominant_field_count,
        "field_count_consistency": round(
            field_count_consistency,
            2,
        ),
        "row_widths": row_widths,
        "rows": rows,
    }

def inspect_source(
    file_path: str,
    max_rows: int = 20,
) -> dict:
    """
    Format-neutral entry point for source inspection.

    File extension is treated as a hint only. Content is used
    to determine the most likely physical format.

    Format-specific inspectors remain separate adapters.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    sample_bytes = path.read_bytes()[:262144]

    base_result = {
        "extension": path.suffix.lower(),
        "file_size_bytes": path.stat().st_size,
    }

    if not sample_bytes:
        return attach_structural_model({
            **base_result,
            "detected_format": "empty",
            "format_confidence": 1.0,
            "inspection_status": "ok",
        })

    if sample_bytes.startswith(b"PAR1"):
        return attach_structural_model({
            **base_result,
            "detected_format": "parquet",
            "format_confidence": 1.0,
            "inspection_status": "format_detected",
        })

    sample_text = None
    detected_encoding = None

    for encoding in (
        "utf-8-sig",
        "cp1252",
    ):
        try:
            sample_text = sample_bytes.decode(encoding)
            detected_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if sample_text is None:
        return attach_structural_model({
            **base_result,
            "detected_format": "binary_or_unknown",
            "format_confidence": 0.0,
            "inspection_status": "format_unknown",
        })

    stripped = sample_text.lstrip()

    if stripped.startswith(("{", "[")):
        try:
            json.loads(sample_text)

            return attach_structural_model({
                **base_result,
                "detected_format": "json",
                "format_confidence": 1.0,
                "encoding": detected_encoding,
                "inspection_status": "format_detected",
            })

        except json.JSONDecodeError:
            pass

    delimited = inspect_delimited_file(
    file_path,
    max_rows=max_rows,
    )

    if (
        delimited.get("physical_format")
        == "delimited_text"
    ):
        result = {
            **delimited,
            "detected_format": "delimited_text",
            "inspection_status": "ok",
        }

        return attach_structural_model(
            result,
            physical_structure=build_delimited_physical_structure(
                result,
            ),
            logical_structure=analyze_tabular_logical_structure(
                result.get("rows", []),
            ),
        )

    return attach_structural_model({
        **delimited,
        "detected_format": "text_or_unknown",
        "inspection_status": "format_uncertain",
    })

def open_dataset(
    connection: duckdb.DuckDBPyConnection,
    file_path: str,
) -> duckdb.DuckDBPyRelation:
    """
    Open a dataset as a DuckDB relation.

    Dataset access belongs here so analysis modules do not need
    their own CSV/Parquet opening logic.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    extension = path.suffix.lower()

    if extension == ".csv":
        return connection.read_csv(str(path))

    if extension == ".parquet":
        return connection.read_parquet(str(path))

    raise ValueError(
        f"Unsupported dataset format: {extension or 'unknown'}"
    )