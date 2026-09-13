import csv
import json
from collections import Counter
from pathlib import Path
from datetime import datetime

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
    if physical_structure is not None:
        model["physical_structure"] = physical_structure

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

def parse_temporal_header_value(
    value: object,
) -> list[datetime]:
    """
    Return possible interpretations of a temporal header value.

    Ambiguous date formats are preserved as multiple candidates
    so neighbouring values can later resolve the sequence.
    """

    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    formats = (
        "%Y-%m-%d",
        "%m/%d/%y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d/%m/%y",
    )

    candidates = []

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                text,
                date_format,
            )

            if parsed not in candidates:
                candidates.append(parsed)

        except ValueError:
            continue

    return candidates

def find_temporal_header_runs(
    row: list[object],
    min_length: int = 3,
) -> list[dict]:
    """
    Find contiguous runs of date-like values in one candidate
    header row.

    This step only identifies possible temporal regions.
    Date-format ambiguity is resolved later from the sequence.
    """

    runs = []
    run_start = None

    for index, value in enumerate(row):
        candidates = parse_temporal_header_value(value)

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
        run_length = len(row) - run_start

        if run_length >= min_length:
            runs.append({
                "start_index": run_start,
                "end_index": len(row) - 1,
                "length": run_length,
            })

    return runs

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