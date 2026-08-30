import duckdb

from rawsight.raw_analysis.distributions import quote_identifier


def analyze_functional_dependency(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    determinant_columns: list[str],
    dependent_column: str,
) -> dict:
    if not determinant_columns:
        raise ValueError(
            "At least one determinant column is required."
        )

    if len(set(determinant_columns)) != len(determinant_columns):
        raise ValueError(
            "Determinant columns must be unique."
        )

    for column_name in determinant_columns:
        if column_name not in relation.columns:
            raise ValueError(
                f"Column not found: {column_name}"
            )

    if dependent_column not in relation.columns:
        raise ValueError(
            f"Column not found: {dependent_column}"
        )

    if dependent_column in determinant_columns:
        raise ValueError(
            "Dependent column cannot also be a determinant column."
        )

    relation.create_view(
        "rawsight_structural_source",
        replace=True,
    )

    determinants = [
        quote_identifier(column_name)
        for column_name in determinant_columns
    ]

    dependent = quote_identifier(dependent_column)

    determinant_sql = ", ".join(determinants)

    not_null_conditions = [
        f"{column} IS NOT NULL"
        for column in determinants
    ]

    not_null_conditions.append(
        f"{dependent} IS NOT NULL"
    )

    where_sql = " AND ".join(not_null_conditions)

    result = connection.execute(
        f"""
        WITH grouped AS (
            SELECT
                {determinant_sql},

                COUNT(*) AS row_count,

                COUNT(
                    DISTINCT {dependent}
                ) AS dependent_count

            FROM rawsight_structural_source

            WHERE {where_sql}

            GROUP BY {determinant_sql}
        )

        SELECT
            SUM(row_count) AS usable_rows,

            COUNT(*) AS determinant_values,

            SUM(
                CASE
                    WHEN dependent_count > 1
                    THEN 1
                    ELSE 0
                END
            ) AS violating_determinant_values,

            SUM(
                CASE
                    WHEN dependent_count > 1
                    THEN row_count
                    ELSE 0
                END
            ) AS rows_in_violating_groups,

            MAX(dependent_count)
                AS maximum_dependents

        FROM grouped
        """
    ).fetchone()

    (
        usable_rows,
        determinant_values,
        violating_determinant_values,
        rows_in_violating_groups,
        maximum_dependents,
    ) = result

    if not determinant_values:
        return {
            "determinant_columns": determinant_columns,
            "dependent_column": dependent_column,
            "method": "functional dependency",
            "status": "no_data",
            "usable_rows": 0,
            "determinant_values": 0,
            "violating_determinant_values": 0,
            "rows_in_violating_groups": 0,
            "dependency_holds": None,
        }

    violating_determinant_values = (
        violating_determinant_values or 0
    )

    rows_in_violating_groups = (
        rows_in_violating_groups or 0
    )

    violation_percent = (
        violating_determinant_values
        / determinant_values
    ) * 100

    violating_row_percent = (
        rows_in_violating_groups
        / usable_rows
    ) * 100 if usable_rows else 0.0

    dependency_holds = (
        violating_determinant_values == 0
    )

    return {
        "determinant_columns": determinant_columns,
        "dependent_column": dependent_column,
        "method": "functional dependency",
        "status": "ok",
        "usable_rows": usable_rows,
        "determinant_values": determinant_values,
        "violating_determinant_values":
            violating_determinant_values,
        "violation_percent": round(
            violation_percent,
            4,
        ),
        "rows_in_violating_groups":
            rows_in_violating_groups,
        "violating_row_percent": round(
            violating_row_percent,
            4,
        ),
        "maximum_dependents": maximum_dependents,
        "dependency_holds": dependency_holds,
    }
def inspect_functional_dependency_violations(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    determinant_columns: list[str],
    dependent_column: str,
    limit: int = 100,
) -> dict:
    if not determinant_columns:
        raise ValueError(
            "At least one determinant column is required."
        )

    for column_name in determinant_columns:
        if column_name not in relation.columns:
            raise ValueError(
                f"Column not found: {column_name}"
            )

    if dependent_column not in relation.columns:
        raise ValueError(
            f"Column not found: {dependent_column}"
        )

    relation.create_view(
        "rawsight_structural_source",
        replace=True,
    )

    determinants = [
        quote_identifier(column_name)
        for column_name in determinant_columns
    ]

    dependent = quote_identifier(dependent_column)

    determinant_sql = ", ".join(determinants)

    not_null_conditions = [
        f"{column} IS NOT NULL"
        for column in determinants
    ]

    not_null_conditions.append(
        f"{dependent} IS NOT NULL"
    )

    where_sql = " AND ".join(not_null_conditions)

    determinant_output = ", ".join(
        f"CAST({column} AS VARCHAR)"
        for column in determinants
    )

    rows = connection.execute(
        f"""
        WITH grouped AS (
            SELECT
                {determinant_sql},
                {dependent} AS dependent_value,
                COUNT(*) AS row_count
            FROM rawsight_structural_source
            WHERE {where_sql}
            GROUP BY
                {determinant_sql},
                {dependent}
        ),
        scored AS (
            SELECT
                *,
                COUNT(*) OVER (
                    PARTITION BY {determinant_sql}
                ) AS dependent_count
            FROM grouped
        )
        SELECT
            {determinant_output},
            CAST(dependent_value AS VARCHAR),
            row_count
        FROM scored
        WHERE dependent_count > 1
        ORDER BY row_count DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()

    violations = []

    for row in rows:
        determinant_values = row[
            :len(determinant_columns)
        ]

        dependent_value = row[
            len(determinant_columns)
        ]

        row_count = row[
            len(determinant_columns) + 1
        ]

        violations.append(
            {
                "determinants": {
                    column_name: value
                    for column_name, value in zip(
                        determinant_columns,
                        determinant_values,
                    )
                },
                "dependent_value": dependent_value,
                "row_count": row_count,
            }
        )

    return {
        "determinant_columns": determinant_columns,
        "dependent_column": dependent_column,
        "violation_rows_returned": len(violations),
        "violations": violations,
    }
