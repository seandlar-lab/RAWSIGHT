from decimal import Decimal

import duckdb

from rawsight.raw_analysis.distributions import (
    is_numeric_type,
    json_safe,
    quote_identifier,
)


def analyze_iqr_outliers(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    column_index = relation.columns.index(column_name)
    technical_type = str(relation.types[column_index])

    if not is_numeric_type(technical_type):
        raise ValueError(
            f"Column is not numeric: "
            f"{column_name} ({technical_type})"
        )

    relation.create_view(
        "rawsight_outlier_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    q1, q3 = connection.execute(
        f"""
        SELECT
            QUANTILE_CONT({column}, 0.25),
            QUANTILE_CONT({column}, 0.75)
        FROM rawsight_outlier_source
        WHERE {column} IS NOT NULL
        """
    ).fetchone()

    if q1 is None or q3 is None:
        return {
            "column": column_name,
            "technical_type": technical_type,
            "method": "IQR",
            "outlier_count": 0,
            "lower_bound": None,
            "upper_bound": None,
        }

    iqr = q3 - q1

    multiplier = (
        Decimal("1.5")
        if isinstance(iqr, Decimal)
        else 1.5
    )

    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)
    (
        non_null_count,
        outlier_count,
        below_lower_bound,
        above_upper_bound,
    ) = connection.execute(
        f"""
        SELECT
            COUNT({column}),

            SUM(
                CASE
                    WHEN {column} < ?
                      OR {column} > ?
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN {column} < ?
                    THEN 1
                    ELSE 0
                END
            ),

            SUM(
                CASE
                    WHEN {column} > ?
                    THEN 1
                    ELSE 0
                END
            )

        FROM rawsight_outlier_source
        """,
        [
            lower_bound,
            upper_bound,
            lower_bound,
            upper_bound,
        ],
    ).fetchone()

    outlier_percent = (
        (outlier_count / non_null_count) * 100
        if non_null_count
        else 0.0
    )

    return {
        "column": column_name,
        "technical_type": technical_type,
        "method": "IQR",
        "q1": json_safe(q1),
        "q3": json_safe(q3),
        "iqr": json_safe(iqr),
        "lower_bound": json_safe(lower_bound),
        "upper_bound": json_safe(upper_bound),
        "non_null_count": non_null_count,
        "outlier_count": outlier_count,
        "outlier_percent": round(outlier_percent, 4),
        "below_lower_bound": below_lower_bound,
        "above_upper_bound": above_upper_bound,
    }