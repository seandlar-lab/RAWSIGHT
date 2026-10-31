"""RAWSIGHT Relationship Analysis v0.1.

Exact, pairwise-complete Pearson correlations calculated in DuckDB.
This analysis is independent of temporal orientation and business semantics.
It does not infer causation, anomaly, redundancy or statistical significance.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Any

from rawsight.long_temporal_series_execution import _is_numeric_type, _quote_identifier, _build_temporal_expression, _validate_temporal_axis
from rawsight.source_context import SourceExecutionContext


def execute_relationship_analysis(
    *,
    file_path: str,
    selected_columns: list[str] | None = None,
    max_columns: int = 16,
    min_pair_observations: int = 3,
    temporal_axis: dict[str, Any] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    source_context: SourceExecutionContext | None = None,
) -> dict[str, Any]:
    """Compute pairwise Pearson correlations on exact source rows.

    If a time window is passed, an already detected vertical temporal axis is
    required; no new temporal inference takes place. No sampling is performed.
    max_columns bounds SQL and output breadth, not the number of source rows.
    """
    if isinstance(max_columns, bool) or not isinstance(max_columns, int) or max_columns < 2 or max_columns > 64:
        raise ValueError("max_columns must be an integer between 2 and 64")
    if isinstance(min_pair_observations, bool) or not isinstance(min_pair_observations, int) or min_pair_observations < 3:
        raise ValueError("min_pair_observations must be an integer >= 3")
    if (start_time is None) != (end_time is None):
        raise ValueError("start_time and end_time must be provided together")
    if start_time is not None:
        from datetime import datetime
        if temporal_axis is None:
            raise ValueError("A detected temporal_axis is required for a time window")
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
        except (TypeError, ValueError) as exc:
            raise ValueError("Time bounds must be naive ISO-8601 datetime strings") from exc
        if start.tzinfo is not None or end.tzinfo is not None or start >= end:
            raise ValueError("Time bounds must be naive and start precede end")

    def run(context: SourceExecutionContext) -> dict[str, Any]:
        if not context.is_open:
            raise RuntimeError("Supplied SourceExecutionContext must already be open")
        names, types = context.column_names, context.column_types
        numeric = [n for n, t in zip(names, types) if _is_numeric_type(t)]
        if selected_columns is None:
            columns = list(numeric)
        else:
            if not isinstance(selected_columns, list) or not all(isinstance(x, str) for x in selected_columns):
                raise ValueError("selected_columns must be a list of column names")
            columns = list(selected_columns)
            if len(columns) != len(set(columns)) or not set(columns).issubset(numeric):
                raise ValueError("selected_columns must be unique numeric source columns")
        base = {"analysis_kind": "variable_relationships", "method": "pearson_pairwise_complete_v0_1",
                "selected_columns": columns, "available_numeric_columns": len(numeric),
                "scope": {"kind": "selected_time_range" if start_time is not None else "whole_dataset",
                          "start_time": start_time, "end_time": end_time},
                "limitations": ["Pairwise-complete Pearson correlation describes linear association, not causation.",
                                "Different pairs can use different subsets of rows.",
                                "Correlations may be misleading under trends, temporal dependence or mixed regimes."]}
        if len(columns) > max_columns:
            return {**base, "status": "resource_limit", "row_count": None, "columns": [], "relationships": [],
                    "limitations": base["limitations"] + [f"{len(columns)} numeric columns exceed max_columns={max_columns}; select columns explicitly. No subset analyzed."]}
        if len(columns) < 2:
            return {**base, "status": "insufficient_data", "row_count": None, "columns": [], "relationships": [],
                    "limitations": base["limitations"] + ["At least two numeric columns are needed."]}
        source_view = _quote_identifier(context.view_name)
        selects = [f"TRY_CAST({_quote_identifier(col)} AS DOUBLE) AS {_quote_identifier('rs_v'+str(i))}" for i, col in enumerate(columns)]
        where = ""
        parameters: list[Any] = []
        if start_time is not None:
            axis_index = _validate_temporal_axis(temporal_axis, names)
            time_expr = _build_temporal_expression(names[axis_index], types[axis_index], temporal_axis)
            selects.append(f"{time_expr} AS rs_time")
            where = "WHERE rs_time IS NOT NULL AND rs_time >= CAST(? AS TIMESTAMP) AND rs_time <= CAST(? AS TIMESTAMP)"
            parameters.extend([start_time, end_time])
        projections = []
        for i in range(len(columns)):
            col = _quote_identifier('rs_v'+str(i))
            projections.append(f"CASE WHEN {col} IS NOT NULL AND isfinite({col}) THEN {col} ELSE NULL END AS {_quote_identifier('v'+str(i))}")
        aggregates = ["COUNT(*) AS total_rows"]
        for i in range(len(columns)):
            v = _quote_identifier('v'+str(i))
            aggregates.extend([f"COUNT({v}) AS n{i}", f"STDDEV_SAMP({v}) AS sd{i}", f"MIN({v}) AS lo{i}", f"MAX({v}) AS hi{i}"])
        for i, j in combinations(range(len(columns)), 2):
            x, y = _quote_identifier('v'+str(i)), _quote_identifier('v'+str(j))
            aggregates.extend([f"COUNT(*) FILTER (WHERE {x} IS NOT NULL AND {y} IS NOT NULL) AS pair_n_{i}_{j}",
                               f"CORR({x}, {y}) AS r_{i}_{j}",
                               f"STDDEV_SAMP({x}) FILTER (WHERE {y} IS NOT NULL) AS pair_sx_{i}_{j}",
                               f"STDDEV_SAMP({y}) FILTER (WHERE {x} IS NOT NULL) AS pair_sy_{i}_{j}"])
        sql = ("WITH typed AS (SELECT " + ", ".join(selects) + f" FROM {source_view}), "
               "scoped AS (SELECT * FROM typed " + where + "), "
               "valid AS (SELECT " + ", ".join(projections) + " FROM scoped) "
               "SELECT " + ", ".join(aggregates) + " FROM valid")
        cursor = context.require_connection().execute(sql, parameters)
        keys = [d[0] for d in cursor.description]
        values = dict(zip(keys, cursor.fetchone()))
        row_count = int(values["total_rows"])
        details = []
        for i, name in enumerate(columns):
            n = int(values[f"n{i}"])
            sd = values[f"sd{i}"]
            const = n >= 2 and (values[f"lo{i}"] == values[f"hi{i}"] or sd == 0)
            details.append({"name": name, "valid_count": n, "missing_or_nonfinite_count": row_count-n,
                            "stddev": float(sd) if sd is not None and math.isfinite(sd) else None,
                            "minimum": values[f"lo{i}"], "maximum": values[f"hi{i}"],
                            "status": "constant" if const else ("insufficient_data" if n < 2 else "measured")})
        pairs = []
        for i, j in combinations(range(len(columns)), 2):
            suffix = f"{i}_{j}"
            n = int(values[f"pair_n_{suffix}"])
            r = values[f"r_{suffix}"]
            sx, sy = values[f"pair_sx_{suffix}"], values[f"pair_sy_{suffix}"]
            measurable = n >= min_pair_observations and sx is not None and sy is not None and sx > 0 and sy > 0 and r is not None and math.isfinite(r)
            pairs.append({"column_a": columns[i], "column_b": columns[j], "pair_count": n,
                          "pearson_r": max(-1., min(1., float(r))) if measurable else None,
                          "status": ("measured" if measurable else
                                     "insufficient_data" if n < min_pair_observations else "zero_pairwise_variance")})
        pairs.sort(key=lambda p: (p["status"] != "measured", -(abs(p["pearson_r"]) if p["pearson_r"] is not None else -1), p["column_a"], p["column_b"]))
        return {**base, "status": "measured" if any(p["status"] == "measured" for p in pairs) else "insufficient_data",
                "row_count": row_count, "columns": details, "relationships": pairs,
                "execution": {"mode": "duckdb_exact_sql_aggregates", "sampled": False, "max_columns": max_columns,
                              "min_pair_observations": min_pair_observations}}

    if source_context is not None:
        source_context.assert_source(file_path)
        return run(source_context)
    with SourceExecutionContext(file_path) as owned:
        return run(owned)
