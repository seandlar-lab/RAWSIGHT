import math

import duckdb

from rawsight.raw_analysis.distributions import (
    is_numeric_type,
    quote_identifier,
)

def analyze_categorical_relationship(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_a: str,
    column_b: str,
    max_categories: int = 100,
) -> dict:
        if column_a not in relation.columns:
            raise ValueError(f"Column not found: {column_a}")

        if column_b not in relation.columns:
            raise ValueError(f"Column not found: {column_b}")

        if column_a == column_b:
            raise ValueError(
                "Relationship analysis requires two different columns."
            )

        relation.create_view(
            "rawsight_relationship_source",
            replace=True,
        )

        a = quote_identifier(column_a)
        b = quote_identifier(column_b)

        (
            usable_rows,
            distinct_a,
            distinct_b,
        ) = connection.execute(
            f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT {a}),
                COUNT(DISTINCT {b})
            FROM rawsight_relationship_source
            WHERE {a} IS NOT NULL
            AND {b} IS NOT NULL
            """
        ).fetchone()

        if usable_rows == 0:
            return {
                "column_a": column_a,
                "column_b": column_b,
                "method": "Cramer's V",
                "usable_rows": 0,
                "cramers_v": None,
                "status": "no_data",
            }

        if distinct_a < 2 or distinct_b < 2:
            return {
                "column_a": column_a,
                "column_b": column_b,
                "method": "Cramer's V",
                "usable_rows": usable_rows,
                "distinct_a": distinct_a,
                "distinct_b": distinct_b,
                "cramers_v": None,
                "status": "insufficient_variation",
            }

        if distinct_a > max_categories or distinct_b > max_categories:
            return {
                "column_a": column_a,
                "column_b": column_b,
                "method": "Cramer's V",
                "usable_rows": usable_rows,
                "distinct_a": distinct_a,
                "distinct_b": distinct_b,
                "cramers_v": None,
                "status": "high_cardinality",
            }

        rows = connection.execute(
            f"""
            SELECT
                CAST({a} AS VARCHAR),
                CAST({b} AS VARCHAR),
                COUNT(*)
            FROM rawsight_relationship_source
            WHERE {a} IS NOT NULL
            AND {b} IS NOT NULL
            GROUP BY {a}, {b}
            """
        ).fetchall()

        observed = {}
        row_totals = {}
        column_totals = {}

        for value_a, value_b, count in rows:
            observed[(value_a, value_b)] = count

            row_totals[value_a] = (
                row_totals.get(value_a, 0) + count
            )

            column_totals[value_b] = (
                column_totals.get(value_b, 0) + count
            )

        chi_square = 0.0

        for value_a, row_total in row_totals.items():
            for value_b, column_total in column_totals.items():
                expected = (
                    row_total * column_total
                ) / usable_rows

                actual = observed.get(
                    (value_a, value_b),
                    0,
                )

                if expected > 0:
                    chi_square += (
                        (actual - expected) ** 2
                    ) / expected

        denominator = usable_rows * min(
            distinct_a - 1,
            distinct_b - 1,
        )

        cramers_v = (
            math.sqrt(chi_square / denominator)
            if denominator > 0
            else None
        )

        return {
            "column_a": column_a,
            "column_b": column_b,
            "method": "Cramer's V",
            "usable_rows": usable_rows,
            "distinct_a": distinct_a,
            "distinct_b": distinct_b,
            "chi_square": round(chi_square, 6),
            "cramers_v": (
                round(cramers_v, 6)
                if cramers_v is not None
                else None
            ),
            "status": "ok",
        }

def analyze_numeric_relationship(
connection: duckdb.DuckDBPyConnection,
relation: duckdb.DuckDBPyRelation,
column_a: str,
column_b: str,
) -> dict:
    if column_a not in relation.columns:
        raise ValueError(
            f"Column not found: {column_a}"
        )

    if column_b not in relation.columns:
        raise ValueError(
            f"Column not found: {column_b}"
        )

    if column_a == column_b:
        raise ValueError(
            "Relationship analysis requires two different columns."
        )

    index_a = relation.columns.index(column_a)
    index_b = relation.columns.index(column_b)

    type_a = str(relation.types[index_a])
    type_b = str(relation.types[index_b])

    if not is_numeric_type(type_a):
        raise ValueError(
            f"Column is not numeric: {column_a} ({type_a})"
        )

    if not is_numeric_type(type_b):
        raise ValueError(
            f"Column is not numeric: {column_b} ({type_b})"
        )
    relation.create_view(
        "rawsight_relationship_source",
        replace=True,
    )

    a = quote_identifier(column_a)
    b = quote_identifier(column_b)

    (
        usable_rows,
        distinct_a,
        distinct_b,
    ) = connection.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT(DISTINCT {a}),
            COUNT(DISTINCT {b})
        FROM rawsight_relationship_source
        WHERE {a} IS NOT NULL
        AND {b} IS NOT NULL
        AND ISFINITE(CAST({a} AS DOUBLE))
        AND ISFINITE(CAST({b} AS DOUBLE))
        """
    ).fetchone()

    if usable_rows < 3:
        return {
            "column_a": column_a,
            "column_b": column_b,
            "method": "Pearson + Spearman",
            "usable_rows": usable_rows,
            "pearson": None,
            "spearman": None,
            "status": "insufficient_data",
        }

    if distinct_a < 2 or distinct_b < 2:
        return {
            "column_a": column_a,
            "column_b": column_b,
            "method": "Pearson + Spearman",
            "usable_rows": usable_rows,
            "distinct_a": distinct_a,
            "distinct_b": distinct_b,
            "pearson": None,
            "spearman": None,
            "status": "insufficient_variation",
        }

    pearson = connection.execute(
        f"""
        SELECT
            CORR(
                CAST({a} AS DOUBLE),
                CAST({b} AS DOUBLE)
            )
        FROM rawsight_relationship_source
        WHERE {a} IS NOT NULL
        AND {b} IS NOT NULL
        AND ISFINITE(CAST({a} AS DOUBLE))
        AND ISFINITE(CAST({b} AS DOUBLE))
        """
    ).fetchone()[0]

    spearman = connection.execute(
        f"""
        WITH paired AS (
            SELECT
                CAST({a} AS DOUBLE) AS value_a,
                CAST({b} AS DOUBLE) AS value_b
            FROM rawsight_relationship_source
            WHERE {a} IS NOT NULL
            AND {b} IS NOT NULL
            AND ISFINITE(CAST({a} AS DOUBLE))
            AND ISFINITE(CAST({b} AS DOUBLE))
        ),
        ranked_base AS (
            SELECT
                value_a,
                value_b,

                RANK() OVER (
                    ORDER BY value_a
                ) AS rank_a_start,

                COUNT(*) OVER (
                    PARTITION BY value_a
                ) AS tie_a,

                RANK() OVER (
                    ORDER BY value_b
                ) AS rank_b_start,

                COUNT(*) OVER (
                    PARTITION BY value_b
                ) AS tie_b

            FROM paired
        ),
        ranked AS (
            SELECT
                rank_a_start
                    + (tie_a - 1) / 2.0
                    AS rank_a,

                rank_b_start
                    + (tie_b - 1) / 2.0
                    AS rank_b

            FROM ranked_base
        )

        SELECT CORR(rank_a, rank_b)
        FROM ranked
        """
    ).fetchone()[0]

    return {
        "column_a": column_a,
        "column_b": column_b,
        "technical_type_a": type_a,
        "technical_type_b": type_b,
        "method": "Pearson + Spearman",
        "usable_rows": usable_rows,
        "distinct_a": distinct_a,
        "distinct_b": distinct_b,
        "pearson": (
            round(pearson, 6)
            if pearson is not None
            else None
        ),
        "spearman": (
            round(spearman, 6)
            if spearman is not None
            else None
        ),
        "status": "ok",
    }