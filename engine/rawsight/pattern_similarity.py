"""RAWSIGHT: pure-Python, dependency-free multivariate episode similarity MVP.

This module scores *supplied, time-aligned episode windows*. Discovery of
candidate windows and database ingestion intentionally belong to a separate
layer. No semantic state labels or anomaly claims are inferred here.
"""
from __future__ import annotations

import math
from typing import Any


def _numeric_series(values: list[Any]) -> list[float] | None:
    if not values:
        return None
    result = []
    for x in values:
        if x is None or isinstance(x, bool):
            return None
        try:
            y = float(x)
        except (ValueError, TypeError, OverflowError):
            return None
        if not math.isfinite(y):
            return None
        result.append(y)
    return result


def _pearson(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n < 3:
        return None
    am, bm = sum(a)/n, sum(b)/n
    ac = [x-am for x in a]
    bc = [y-bm for y in b]
    av = sum(x*x for x in ac)
    bv = sum(y*y for y in bc)
    if av < 1e-20 or bv < 1e-20:
        return None  # no defined correlation for a constant signal
    return max(-1.0, min(1.0, sum(x*y for x,y in zip(ac, bc))/math.sqrt(av*bv)))


def compare_episodes(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    selected_columns: list[str] | None = None,
    minimum_points: int = 3,
    minimum_coverage: float = 1.0,
) -> dict[str, Any]:
    """Compare aligned equal-bin episode series.

    Schema: {"id": str, "series": {"column": [bin_mean_or_None, ...]}}.
    Signal selection is automatic from the intersection unless explicit.
    Similarity is a macro-average of (r + 1) / 2, on *valid, nonconstant*
    signals only; no interpolation, no imputation, no domain semantics.
    """
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be in (0, 1]")
    if not isinstance(minimum_points, int) or isinstance(minimum_points, bool) or minimum_points < 3:
        raise ValueError("minimum_points must be an integer >= 3")
    if not isinstance(target.get("series"), dict):
        raise ValueError("target.series must be an object")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    common = set(target["series"])
    if selected_columns is not None:
        if not selected_columns or len(selected_columns) != len(set(selected_columns)):
            raise ValueError("selected_columns must be nonempty and unique")
        if not set(selected_columns).issubset(common):
            raise ValueError("selected_columns absent from target")
        columns = list(selected_columns)
    else:
        columns = sorted(common)
    results = []
    for candidate in candidates:
        if not isinstance(candidate.get("series"), dict):
            raise ValueError("candidate.series must be an object")
        evidence = []
        excluded = []
        for col in columns:
            a_raw = target["series"].get(col)
            b_raw = candidate["series"].get(col)
            if not isinstance(a_raw, list) or not isinstance(b_raw, list) or len(a_raw) != len(b_raw) or len(a_raw) < minimum_points:
                excluded.append({"column": col, "reason": "incompatible_bins"})
                continue
            paired = []
            for ax,bx in zip(a_raw,b_raw):
                aa,bb = _numeric_series([ax]),_numeric_series([bx])
                if aa is not None and bb is not None:
                    paired.append((aa[0],bb[0]))
            coverage = len(paired)/len(a_raw)
            if len(paired) < minimum_points or coverage < minimum_coverage:
                excluded.append({"column": col, "reason": "insufficient_coverage", "paired_bins": len(paired), "coverage": coverage})
                continue
            a,b = [x for x,_ in paired], [y for _,y in paired]
            r = _pearson(a,b)
            if r is None:
                excluded.append({"column": col, "reason": "constant_signal"})
                continue
            evidence.append({
                "column":col, "pearson_r":r,
                "shape_similarity":(r+1)/2,
                "paired_bins":len(paired), "coverage":coverage,
                "target_start":a[0], "candidate_start":b[0],
                "target_delta":a[-1]-a[0], "candidate_delta":b[-1]-b[0],
                "level_difference":sum(b)/len(b)-sum(a)/len(a),
            })
        similarity = sum(x["shape_similarity"] for x in evidence)/len(evidence) if evidence else None
        results.append({
            "candidate_id":candidate.get("id"),
            "status":"measured" if evidence else "insufficient_data",
            "shape_similarity":similarity,
            "measured_signal_count":len(evidence),
            "requested_signal_count":len(columns),
            "signals":evidence, "excluded_signals":excluded,
        })
    results.sort(key=lambda x: (x["shape_similarity"] is None, -(x["shape_similarity"] or 0), str(x["candidate_id"])))
    return {
        "analysis_kind":"pattern_similarity",
        "status":"measured" if any(x["status"] == "measured" for x in results) else "insufficient_data",
        "target_id":target.get("id"),
        "columns_considered":columns,
        "candidates":results,
        "limitations":[
            "Episode boundaries and aligned time bins are supplied by the caller.",
            "Correlation measures shape only and may be high for monotonic trends.",
            "Level and delta differences are descriptive and are not anomaly scores.",
            "No interpolation or inferred observations are introduced.",
            "A similar pattern does not establish normality or causality.",
        ],
    }
