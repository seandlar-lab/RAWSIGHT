from decimal import Decimal

import duckdb


NUMERIC_TYPES = {
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "FLOAT",
    "DOUBLE",
    "REAL",
}

CATEGORICAL_TYPES = {
    "VARCHAR",
    "CHAR",
    "BOOLEAN",
}

def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)

    return value


def is_numeric_type(technical_type: str) -> bool:
    normalized = technical_type.upper()

    return (
        normalized in NUMERIC_TYPES
        or normalized.startswith("DECIMAL")
    )

def is_categorical_type(technical_type: str) -> bool:
    normalized = technical_type.upper()

    return (
        normalized in CATEGORICAL_TYPES
        or normalized.startswith("VARCHAR")
        or normalized.startswith("CHAR")
        or normalized.startswith("ENUM")
    )

def analyze_numeric_histogram(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    bin_count: int = 20,
) -> list[dict]:
    if bin_count < 1:
        raise ValueError(
            "bin_count must be at least 1"
        )

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
        "rawsight_histogram_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    minimum, maximum = connection.execute(
        f"""
        SELECT
            MIN({column}),
            MAX({column})
        FROM rawsight_histogram_source
        WHERE {column} IS NOT NULL
        """
    ).fetchone()

    if minimum is None or maximum is None:
        return []

    minimum = float(minimum)
    maximum = float(maximum)

    if minimum == maximum:
        count = connection.execute(
            f"""
            SELECT COUNT({column})
            FROM rawsight_histogram_source
            """
        ).fetchone()[0]

        return [
            {
                "lower_bound": minimum,
                "upper_bound": maximum,
                "count": count,
            }
        ]

    bin_width = (
        maximum - minimum
    ) / bin_count

    rows = connection.execute(
        f"""
        SELECT
            LEAST(
                ? - 1,
                CAST(
                    FLOOR(
                        (
                            CAST({column} AS DOUBLE) - ?
                        ) / ?
                    )
                    AS INTEGER
                )
            ) AS bin_index,
            COUNT(*) AS count
        FROM rawsight_histogram_source
        WHERE {column} IS NOT NULL
        GROUP BY bin_index
        ORDER BY bin_index
        """,
        [
            bin_count,
            minimum,
            bin_width,
        ],
    ).fetchall()

    counts = {
        bin_index: count
        for bin_index, count in rows
    }

    bins = []

    for bin_index in range(bin_count):
        lower_bound = (
            minimum
            + bin_index * bin_width
        )

        upper_bound = (
            minimum
            + (bin_index + 1) * bin_width
        )

        if bin_index == bin_count - 1:
            upper_bound = maximum

        bins.append(
            {
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "count": counts.get(
                    bin_index,
                    0,
                ),
            }
        )

    return bins

def analyze_numeric_distribution(
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
            f"Column is not numeric: {column_name} ({technical_type})"
        )

    relation.create_view(
        "rawsight_distribution_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    result = connection.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT({column}) AS non_null_count,
            COUNT(*) - COUNT({column}) AS null_count,
            COUNT(DISTINCT {column}) AS distinct_count,

            MIN({column}) AS minimum,
            QUANTILE_CONT({column}, 0.05) AS p05,
            QUANTILE_CONT({column}, 0.25) AS q1,
            QUANTILE_CONT({column}, 0.50) AS median,
            QUANTILE_CONT({column}, 0.75) AS q3,
            QUANTILE_CONT({column}, 0.95) AS p95,
            MAX({column}) AS maximum,

            AVG({column}) AS mean,
            STDDEV_SAMP({column}) AS standard_deviation,

            SUM(
                CASE WHEN {column} = 0 THEN 1 ELSE 0 END
            ) AS zero_count,

            SUM(
                CASE WHEN {column} < 0 THEN 1 ELSE 0 END
            ) AS negative_count

        FROM rawsight_distribution_source
        """
    ).fetchone()

    (
        total_rows,
        non_null_count,
        null_count,
        distinct_count,
        minimum,
        p05,
        q1,
        median,
        q3,
        p95,
        maximum,
        mean,
        standard_deviation,
        zero_count,
        negative_count,
    ) = result

    iqr = (
        q3 - q1
        if q1 is not None and q3 is not None
        else None
    )
    histogram_bins = analyze_numeric_histogram(
        connection,
        relation,
        column_name,
    )
    return {
        "column": column_name,
        "technical_type": technical_type,
        "total_rows": total_rows,
        "non_null_count": non_null_count,
        "null_count": null_count,
        "distinct_count": distinct_count,
        "minimum": json_safe(minimum),
        "p05": json_safe(p05),
        "q1": json_safe(q1),
        "median": json_safe(median),
        "q3": json_safe(q3),
        "p95": json_safe(p95),
        "maximum": json_safe(maximum),
        "mean": json_safe(mean),
        "standard_deviation": json_safe(standard_deviation),
        "iqr": json_safe(iqr),
        "zero_count": zero_count,
        "negative_count": negative_count,
        "histogram_bins": histogram_bins,
    }
def analyze_categorical_distribution(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    top_n: int = 20,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    column_index = relation.columns.index(column_name)
    technical_type = str(relation.types[column_index])

    if not is_categorical_type(technical_type):
        raise ValueError(
            f"Column is not categorical: "
            f"{column_name} ({technical_type})"
        )

    relation.create_view(
        "rawsight_distribution_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    summary = connection.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT({column}) AS non_null_count,
            COUNT(*) - COUNT({column}) AS null_count,
            COUNT(DISTINCT {column}) AS distinct_count
        FROM rawsight_distribution_source
        """
    ).fetchone()

    (
        total_rows,
        non_null_count,
        null_count,
        distinct_count,
    ) = summary

    value_rows = connection.execute(
        f"""
        SELECT
            CAST({column} AS VARCHAR) AS value,
            COUNT(*) AS count
        FROM rawsight_distribution_source
        WHERE {column} IS NOT NULL
        GROUP BY {column}
        ORDER BY count DESC, value
        LIMIT ?
        """,
        [top_n],
    ).fetchall()

    top_values = []

    for value, count in value_rows:
        percent_of_non_null = (
            (count / non_null_count) * 100
            if non_null_count
            else 0.0
        )

        top_values.append(
            {
                "value": value,
                "count": count,
                "percent_of_non_null": round(
                    percent_of_non_null,
                    4,
                ),
            }
        )

    dominant_value = (
        top_values[0]
        if top_values
        else None
    )
    return {
        "column": column_name,
        "technical_type": technical_type,
        "total_rows": total_rows,
        "non_null_count": non_null_count,
        "null_count": null_count,
        "distinct_count": distinct_count,
        "dominant_value": dominant_value,
        "top_values": top_values,
    }    