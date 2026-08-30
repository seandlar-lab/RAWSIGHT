import duckdb

from rawsight.raw_analysis.distributions import (
    analyze_categorical_distribution,
    analyze_numeric_distribution,
    is_categorical_type,
    is_numeric_type,
)
from rawsight.raw_analysis.outliers import (
    analyze_iqr_outliers,
)
from rawsight.raw_analysis.temporal import (
    analyze_temporal_axis,
    analyze_temporal_cadence,
    analyze_temporal_gaps,
)


def analyze_column(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    semantic_type: str | None = None,
    format_hint: str | None = None,
    excluded_values: list[str] | None = None,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    column_index = relation.columns.index(column_name)
    technical_type = str(relation.types[column_index])

    normalized_semantic_type = (
        semantic_type.strip().lower()
        if semantic_type
        else None
    )

    result = {
        "column": column_name,
        "technical_type": technical_type,
        "semantic_type": semantic_type,
        "routing": None,
        "distribution": None,
        "outliers": None,
        "temporal": None,
    }

    if normalized_semantic_type in {
        "date",
        "datetime",
        "timestamp",
    }:
        result["routing"] = "temporal"

        result["temporal"] = {
            "axis": analyze_temporal_axis(
                connection,
                relation,
                column_name,
                format_hint=format_hint,
                excluded_values=excluded_values,
            ),
            "cadence": analyze_temporal_cadence(
                connection,
                relation,
                column_name,
                format_hint=format_hint,
                excluded_values=excluded_values,
            ),
            "gaps": analyze_temporal_gaps(
                connection,
                relation,
                column_name,
                format_hint=format_hint,
                excluded_values=excluded_values,
            ),
        }

        return result

    if is_numeric_type(technical_type):
        result["routing"] = "numeric"

        result["distribution"] = analyze_numeric_distribution(
            connection,
            relation,
            column_name,
        )

        result["outliers"] = analyze_iqr_outliers(
            connection,
            relation,
            column_name,
        )

    elif is_categorical_type(technical_type):
        result["routing"] = "categorical"

        result["distribution"] = analyze_categorical_distribution(
            connection,
            relation,
            column_name,
        )

    else:
        result["routing"] = "unsupported"

    return result