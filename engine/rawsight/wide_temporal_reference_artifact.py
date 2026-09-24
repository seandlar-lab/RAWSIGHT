from __future__ import annotations

from array import array
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence


_ARTIFACT_VERSION = "wide_temporal_reference_exact_v2"


def _source_identity(
    file_path: str,
) -> dict[str, object]:
    path = Path(file_path).resolve()
    stat = path.stat()

    return {
        "resolved_path": str(path),
        "file_size": stat.st_size,
        "modified_time_ns": stat.st_mtime_ns,
    }


def _normalized_axis(
    temporal_axis: dict[str, Any],
) -> dict[str, object]:
    orientation = temporal_axis.get(
        "orientation"
    )
    start_index = temporal_axis.get(
        "start_index"
    )
    end_index = temporal_axis.get(
        "end_index"
    )

    if orientation != "horizontal":
        raise ValueError(
            "Reference artifact requires "
            "a horizontal temporal axis"
        )

    if not isinstance(
        start_index,
        int,
    ):
        raise ValueError(
            "Temporal start_index is missing or invalid"
        )

    if not isinstance(
        end_index,
        int,
    ):
        raise ValueError(
            "Temporal end_index is missing or invalid"
        )

    if (
        start_index < 0
        or end_index < start_index
    ):
        raise ValueError(
            "Temporal column range is invalid"
        )

    return {
        "orientation": orientation,
        "start_index": start_index,
        "end_index": end_index,
    }


def reference_artifact_key(
    file_path: str,
    temporal_axis: dict[str, Any],
) -> str:
    """
    Build a deterministic cache key from source freshness,
    temporal-axis identity and artifact format version.

    The key is an execution concern only. It does not change
    analytical semantics.
    """

    payload = {
        "artifact_version": (
            _ARTIFACT_VERSION
        ),
        "source": _source_identity(
            file_path
        ),
        "temporal_axis": (
            _normalized_axis(
                temporal_axis
            )
        ),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return sha256(
        canonical
    ).hexdigest()


def default_reference_cache_dir() -> Path:
    """
    Return an OS-temporary RAWSIGHT cache location.

    This cache is intentionally disposable. Losing it may cost
    recomputation, but must never affect analytical correctness.
    """

    return (
        Path(
            tempfile.gettempdir()
        )
        / "rawsight"
        / "wide_temporal_reference"
    )


def _artifact_paths(
    cache_key: str,
    cache_dir: Path,
) -> tuple[Path, Path]:
    return (
        cache_dir
        / f"{cache_key}.json",
        cache_dir
        / f"{cache_key}.bin",
    )


def _validated_manifest(
    file_path: str,
    temporal_axis: dict[str, Any],
    cache_dir: Path | None,
) -> tuple[
    dict[str, Any],
    Path,
    Path,
] | None:
    directory = (
        cache_dir
        if cache_dir is not None
        else default_reference_cache_dir()
    )

    cache_key = (
        reference_artifact_key(
            file_path,
            temporal_axis,
        )
    )

    manifest_path, binary_path = (
        _artifact_paths(
            cache_key,
            directory,
        )
    )

    if (
        not manifest_path.is_file()
        or not binary_path.is_file()
    ):
        return None

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if (
        manifest.get(
            "artifact_version"
        )
        != _ARTIFACT_VERSION
    ):
        return None

    if (
        manifest.get("cache_key")
        != cache_key
    ):
        return None

    try:
        current_source = (
            _source_identity(
                file_path
            )
        )
    except OSError:
        return None

    if (
        manifest.get("source")
        != current_source
    ):
        return None

    if (
        manifest.get(
            "temporal_axis"
        )
        != _normalized_axis(
            temporal_axis
        )
    ):
        return None

    if (
        manifest.get(
            "numeric_item_size"
        )
        != array("d").itemsize
    ):
        return None

    if (
        manifest.get(
            "byte_order"
        )
        != sys.byteorder
    ):
        return None

    offsets = manifest.get(
        "offsets"
    )
    counts = manifest.get(
        "numeric_counts"
    )

    if (
        not isinstance(
            offsets,
            list,
        )
        or not isinstance(
            counts,
            list,
        )
        or len(offsets)
        != len(counts) + 1
    ):
        return None

    if (
        any(
            not isinstance(
                value,
                int,
            )
            or value < 0
            for value in offsets
        )
        or any(
            not isinstance(
                value,
                int,
            )
            or value < 0
            for value in counts
        )
    ):
        return None

    if (
        offsets[0] != 0
        or any(
            offsets[index + 1]
            < offsets[index]
            for index in range(
                len(offsets) - 1
            )
        )
    ):
        return None

    if any(
        (
            offsets[index + 1]
            - offsets[index]
        )
        != counts[index]
        for index in range(
            len(counts)
        )
    ):
        return None

    retained_count = (
        manifest.get(
            "retained_numeric_value_count"
        )
    )

    if (
        not isinstance(
            retained_count,
            int,
        )
        or retained_count < 0
        or offsets[-1]
        != retained_count
    ):
        return None

    expected_bytes = (
        retained_count
        * array("d").itemsize
    )

    try:
        actual_bytes = (
            binary_path.stat().st_size
        )
    except OSError:
        return None

    if actual_bytes != expected_bytes:
        return None

    return (
        manifest,
        manifest_path,
        binary_path,
    )


def write_reference_artifact(
    file_path: str,
    temporal_axis: dict[str, Any],
    ordered_reference_values: Sequence[
        Sequence[float]
    ],
    population_count: int,
    statistics_mode: str,
    percentile_method: str,
    reference_profile: (
        dict[str, Any] | None
    ) = None,
    execution_metadata: (
        dict[str, Any] | None
    ) = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Persist finalized exact reference distributions and, when supplied,
    the already-calculated reference profile.

    Values are flattened into one binary array('d'). A JSON manifest
    stores offsets, counts, source identity, analysis metadata and the
    lightweight profile used by Explore.

    The artifact is disposable execution state, not part of the source
    dataset and not part of the domain model.
    """

    if population_count < 0:
        raise ValueError(
            "population_count must be >= 0"
        )

    axis = _normalized_axis(
        temporal_axis
    )

    cache_key = (
        reference_artifact_key(
            file_path,
            temporal_axis,
        )
    )

    directory = (
        cache_dir
        if cache_dir is not None
        else default_reference_cache_dir()
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path, binary_path = (
        _artifact_paths(
            cache_key,
            directory,
        )
    )

    flattened = array("d")
    offsets = [0]
    counts = []

    for values in (
        ordered_reference_values
    ):
        counts.append(
            len(values)
        )
        flattened.extend(
            values
        )
        offsets.append(
            len(flattened)
        )

    expected_position_count = (
        int(axis["end_index"])
        - int(axis["start_index"])
        + 1
    )

    if (
        len(counts)
        != expected_position_count
    ):
        raise ValueError(
            "Reference distribution count "
            "does not match temporal axis width"
        )

    temporary_binary = (
        binary_path.with_suffix(
            ".bin.tmp"
        )
    )
    temporary_manifest = (
        manifest_path.with_suffix(
            ".json.tmp"
        )
    )

    try:
        with temporary_binary.open(
            "wb"
        ) as handle:
            flattened.tofile(
                handle
            )

        manifest = {
            "artifact_version": (
                _ARTIFACT_VERSION
            ),
            "cache_key": cache_key,
            "source": (
                _source_identity(
                    file_path
                )
            ),
            "temporal_axis": axis,
            "statistics_mode": (
                statistics_mode
            ),
            "percentile_method": (
                percentile_method
            ),
            "population_count": (
                population_count
            ),
            "temporal_position_count": (
                len(counts)
            ),
            "numeric_counts": counts,
            "offsets": offsets,
            "retained_numeric_value_count": (
                len(flattened)
            ),
            "retained_numeric_payload_bytes": (
                len(flattened)
                * flattened.itemsize
            ),
            "numeric_item_size": (
                flattened.itemsize
            ),
            "byte_order": (
                sys.byteorder
            ),
            "binary_file_name": (
                binary_path.name
            ),
            "reference_profile": (
                reference_profile
            ),
            "execution_metadata": (
                execution_metadata
                if execution_metadata
                is not None
                else {}
            ),
        }

        temporary_manifest.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            ),
            encoding="utf-8",
        )

        temporary_binary.replace(
            binary_path
        )
        temporary_manifest.replace(
            manifest_path
        )

    finally:
        for temporary_path in (
            temporary_binary,
            temporary_manifest,
        ):
            try:
                if temporary_path.exists():
                    temporary_path.unlink()
            except OSError:
                pass

    return {
        **manifest,
        "manifest_path": str(
            manifest_path
        ),
        "binary_path": str(
            binary_path
        ),
    }


def load_reference_artifact_manifest(
    file_path: str,
    temporal_axis: dict[str, Any],
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """
    Load only the validated manifest.

    This avoids reading the numeric binary payload when a caller only
    needs the already-calculated reference profile.
    """

    validated = _validated_manifest(
        file_path=file_path,
        temporal_axis=temporal_axis,
        cache_dir=cache_dir,
    )

    if validated is None:
        return None

    (
        manifest,
        manifest_path,
        binary_path,
    ) = validated

    return {
        **manifest,
        "manifest_path": str(
            manifest_path
        ),
        "binary_path": str(
            binary_path
        ),
    }


def load_reference_artifact(
    file_path: str,
    temporal_axis: dict[str, Any],
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """
    Load a valid finalized reference artifact for the current source.

    A stale or mismatched artifact is treated as a cache miss.
    Analytical execution may then rebuild it.

    The binary distribution payload is read only in this full-load
    function. Profile-only callers should use
    load_reference_artifact_manifest().
    """

    validated = _validated_manifest(
        file_path=file_path,
        temporal_axis=temporal_axis,
        cache_dir=cache_dir,
    )

    if validated is None:
        return None

    (
        manifest,
        manifest_path,
        binary_path,
    ) = validated

    offsets = manifest[
        "offsets"
    ]

    values = array("d")

    try:
        with binary_path.open(
            "rb"
        ) as handle:
            values.fromfile(
                handle,
                binary_path.stat().st_size
                // values.itemsize,
            )
    except (
        OSError,
        EOFError,
    ):
        return None

    if (
        offsets[-1]
        != len(values)
    ):
        return None

    values_view = memoryview(
        values
    )

    distributions = tuple(
        values_view[
            offsets[index]:
            offsets[index + 1]
        ]
        for index in range(
            len(offsets) - 1
        )
    )

    return {
        **manifest,
        "manifest_path": str(
            manifest_path
        ),
        "binary_path": str(
            binary_path
        ),
        "ordered_reference_values": (
            distributions
        ),
    }
