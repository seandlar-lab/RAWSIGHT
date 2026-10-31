"""Deterministic, domain-neutral candidate episode discovery for aligned observations.

This module identifies temporal-gap boundaries and concurrent numeric transitions.
It does NOT infer operating states, causality, or anomaly labels.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def discover_episodes(
    observations: list[dict[str, Any]],
    *,
    timestamp_key: str = "time",
    selected_columns: list[str] | None = None,
    expected_interval_seconds: float,
    gap_multiple: float = 3.0,
    change_thresholds: dict[str, float] | None = None,
    minimum_changed_signals: int = 2,
    minimum_episode_points: int = 3,
) -> dict[str, Any]:
    """Partition sorted observations on large time gaps or concurrent jumps.

    Observations: [{"time": ISO timestamp, "TP3": value, ...}, ...].
    A multivariate jump requires explicit, *absolute* per-column change
    thresholds; these are parameters, not learned anomaly thresholds.
    No imputation, resampling, or interpolation is performed.
    """
    if not math.isfinite(expected_interval_seconds) or expected_interval_seconds <= 0:
        raise ValueError("expected_interval_seconds must be positive and finite")
    if not math.isfinite(gap_multiple) or gap_multiple <= 1:
        raise ValueError("gap_multiple must be finite and > 1")
    if isinstance(minimum_changed_signals, bool) or not isinstance(minimum_changed_signals, int) or minimum_changed_signals < 1:
        raise ValueError("minimum_changed_signals must be an integer >= 1")
    if isinstance(minimum_episode_points, bool) or not isinstance(minimum_episode_points, int) or minimum_episode_points < 1:
        raise ValueError("minimum_episode_points must be an integer >= 1")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    if change_thresholds is None:
        change_thresholds = {}
    for name, limit in change_thresholds.items():
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
            raise ValueError(f"threshold for {name} must be finite and > 0")
    if selected_columns is None:
        selected_columns = sorted({key for row in observations for key in row if key != timestamp_key})
    if len(selected_columns) != len(set(selected_columns)) or timestamp_key in selected_columns:
        raise ValueError("selected_columns must be unique and exclude timestamp_key")
    if not set(change_thresholds).issubset(selected_columns):
        raise ValueError("change_thresholds must reference selected_columns")
    parsed: list[datetime] = []
    for row in observations:
        if not isinstance(row, dict) or not isinstance(row.get(timestamp_key), str):
            raise ValueError("every observation must have an ISO timestamp string")
        try:
            stamp = datetime.fromisoformat(row[timestamp_key].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid timestamp") from exc
        parsed.append(stamp)
    for a, b in zip(parsed, parsed[1:]):
        try:
            delta = (b - a).total_seconds()
        except TypeError as exc:
            raise ValueError("timestamps must use consistent timezone semantics") from exc
        if delta <= 0:
            raise ValueError("timestamps must be strictly increasing; duplicates need upstream normalization")
    boundaries: list[dict[str, Any]] = []
    for index in range(1, len(observations)):
        previous, current = observations[index - 1], observations[index]
        seconds = (parsed[index] - parsed[index - 1]).total_seconds()
        if seconds > expected_interval_seconds * gap_multiple:
            boundaries.append({"index": index, "reason": "temporal_gap", "gap_seconds": seconds, "signals": []})
            continue
        changed = []
        for name, threshold in sorted(change_thresholds.items()):
            a, b = _finite(previous.get(name)), _finite(current.get(name))
            if a is not None and b is not None and abs(b - a) >= threshold:
                changed.append(name)
        if len(changed) >= minimum_changed_signals:
            boundaries.append({"index": index, "reason": "concurrent_change", "gap_seconds": seconds, "signals": changed})
    starts = [0] + [boundary["index"] for boundary in boundaries]
    stops = [boundary["index"] for boundary in boundaries] + [len(observations)]
    episodes = []
    for start, stop in zip(starts, stops):
        if stop <= start:
            continue
        counts = {name: sum(_finite(row.get(name)) is not None for row in observations[start:stop]) for name in selected_columns}
        episodes.append({
            "id": f"episode-{start:08d}-{stop - 1:08d}",
            "start_index": start, "end_index": stop - 1,
            "start_time": observations[start][timestamp_key],
            "end_time": observations[stop - 1][timestamp_key],
            "observation_count": stop - start,
            "status": "candidate" if stop - start >= minimum_episode_points else "too_short",
            "valid_counts": counts,
            "coverage": {name: counts[name] / (stop - start) for name in selected_columns},
            "start_boundary": next((b for b in boundaries if b["index"] == start), None),
        })
    return {
        "analysis_kind": "automatic_episode_discovery",
        "status": "measured" if episodes else "insufficient_data",
        "method": "gap_and_explicit_concurrent_change_v0_1",
        "columns_considered": selected_columns,
        "observation_count": len(observations),
        "episode_count": len(episodes),
        "boundaries": boundaries,
        "episodes": episodes,
        "limitations": [
            "Change thresholds are caller-supplied, not learned from historical baselines.",
            "Only consecutive observations are compared; gradual trends are not detected as events.",
            "Input must be strictly ordered; duplicate timestamps require upstream normalization.",
            "No anomaly, operating-mode, normality, or causal claim is produced.",
            "IDs are deterministic for the supplied ordering, not stable across inserted rows.",
        ],
    }
