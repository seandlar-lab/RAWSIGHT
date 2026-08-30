from datetime import date, datetime

import duckdb

from rawsight.raw_analysis.distributions import (
    is_numeric_type,
    quote_identifier,
)


def json_safe_temporal(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def analyze_temporal_axis(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    format_hint: str | None = None,
    excluded_values: list[str] | None = None,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    excluded_values = excluded_values or []

    relation.create_view(
        "rawsight_temporal_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    if format_hint == "YYYYMMDD":
        parsed_expression = (
            f"TRY_STRPTIME("
            f"CAST({column} AS VARCHAR), "
            f"'%Y%m%d'"
            f")"
        )
    else:
        parsed_expression = (
            f"TRY_CAST({column} AS TIMESTAMP)"
        )

    exclusion_sql = ""

    if excluded_values:
        quoted_values = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in excluded_values
        )

        exclusion_sql = (
            f"AND CAST({column} AS VARCHAR) "
            f"NOT IN ({quoted_values})"
        )

    result = connection.execute(
        f"""
        WITH parsed AS (
            SELECT
                {column} AS raw_value,
                {parsed_expression} AS parsed_time
            FROM rawsight_temporal_source
            WHERE {column} IS NOT NULL
              {exclusion_sql}
        )
        SELECT
            COUNT(*) AS candidate_count,

            SUM(
                CASE
                    WHEN parsed_time IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS valid_count,

            SUM(
                CASE
                    WHEN parsed_time IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS invalid_count,

            COUNT(
                DISTINCT parsed_time
            ) AS distinct_time_points,

            MIN(parsed_time) AS first_observation,

            MAX(parsed_time) AS last_observation

        FROM parsed
        """
    ).fetchone()

    (
        candidate_count,
        valid_count,
        invalid_count,
        distinct_time_points,
        first_observation,
        last_observation,
    ) = result

    duplicate_timestamp_rows = (
        valid_count - distinct_time_points
        if valid_count is not None
        else 0
    )

    return {
        "column": column_name,
        "format_hint": format_hint,
        "excluded_values": excluded_values,
        "candidate_count": candidate_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "distinct_time_points": distinct_time_points,
        "duplicate_timestamp_rows": duplicate_timestamp_rows,
        "first_observation": json_safe_temporal(
            first_observation
        ),
        "last_observation": json_safe_temporal(
            last_observation
        ),
    }

def analyze_temporal_cadence(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    format_hint: str | None = None,
    excluded_values: list[str] | None = None,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    excluded_values = excluded_values or []

    relation.create_view(
        "rawsight_temporal_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    if format_hint == "YYYYMMDD":
        parsed_expression = (
            f"TRY_STRPTIME("
            f"CAST({column} AS VARCHAR), "
            f"'%Y%m%d'"
            f")"
        )
    else:
        parsed_expression = (
            f"TRY_CAST({column} AS TIMESTAMP)"
        )

    exclusion_sql = ""

    if excluded_values:
        quoted_values = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in excluded_values
        )

        exclusion_sql = (
            f"AND CAST({column} AS VARCHAR) "
            f"NOT IN ({quoted_values})"
        )

    result = connection.execute(
        f"""
        WITH parsed AS (
            SELECT
                {parsed_expression} AS parsed_time
            FROM rawsight_temporal_source
            WHERE {column} IS NOT NULL
              {exclusion_sql}
        ),
        distinct_times AS (
            SELECT DISTINCT parsed_time
            FROM parsed
            WHERE parsed_time IS NOT NULL
        ),
        ordered_times AS (
            SELECT
                parsed_time,
                LAG(parsed_time) OVER (
                    ORDER BY parsed_time
                ) AS previous_time
            FROM distinct_times
        ),
        intervals AS (
            SELECT
                DATE_DIFF(
                    'second',
                    previous_time,
                    parsed_time
                ) AS interval_seconds
            FROM ordered_times
            WHERE previous_time IS NOT NULL
        )
        SELECT
            COUNT(*) AS interval_count,
            MIN(interval_seconds),
            QUANTILE_CONT(interval_seconds, 0.50),
            AVG(interval_seconds),
            MAX(interval_seconds)
        FROM intervals
        """
    ).fetchone()

    (
        interval_count,
        minimum_interval_seconds,
        median_interval_seconds,
        mean_interval_seconds,
        maximum_interval_seconds,
    ) = result

    return {
        "column": column_name,
        "format_hint": format_hint,
        "interval_count": interval_count,
        "minimum_interval_seconds": minimum_interval_seconds,
        "median_interval_seconds": median_interval_seconds,
        "mean_interval_seconds": mean_interval_seconds,
        "maximum_interval_seconds": maximum_interval_seconds,
    }
def analyze_temporal_gaps(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    column_name: str,
    format_hint: str | None = None,
    excluded_values: list[str] | None = None,
    gap_factor: float = 3.0,
    top_n: int = 20,
) -> dict:
    if column_name not in relation.columns:
        raise ValueError(
            f"Column not found: {column_name}"
        )

    excluded_values = excluded_values or []

    relation.create_view(
        "rawsight_temporal_source",
        replace=True,
    )

    column = quote_identifier(column_name)

    if format_hint == "YYYYMMDD":
        parsed_expression = (
            f"TRY_STRPTIME("
            f"CAST({column} AS VARCHAR), "
            f"'%Y%m%d'"
            f")"
        )
    else:
        parsed_expression = (
            f"TRY_CAST({column} AS TIMESTAMP)"
        )

    exclusion_sql = ""

    if excluded_values:
        quoted_values = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in excluded_values
        )

        exclusion_sql = (
            f"AND CAST({column} AS VARCHAR) "
            f"NOT IN ({quoted_values})"
        )

    interval_rows = connection.execute(
        f"""
        WITH parsed AS (
            SELECT
                {parsed_expression} AS parsed_time
            FROM rawsight_temporal_source
            WHERE {column} IS NOT NULL
              {exclusion_sql}
        ),
        distinct_times AS (
            SELECT DISTINCT parsed_time
            FROM parsed
            WHERE parsed_time IS NOT NULL
        ),
        ordered_times AS (
            SELECT
                parsed_time,
                LAG(parsed_time) OVER (
                    ORDER BY parsed_time
                ) AS previous_time
            FROM distinct_times
        )
        SELECT
            previous_time,
            parsed_time,
            DATE_DIFF(
                'second',
                previous_time,
                parsed_time
            ) AS interval_seconds
        FROM ordered_times
        WHERE previous_time IS NOT NULL
        ORDER BY parsed_time
        """
    ).fetchall()

    if not interval_rows:
        return {
            "column": column_name,
            "status": "insufficient_data",
            "gap_factor": gap_factor,
            "median_interval_seconds": None,
            "gap_threshold_seconds": None,
            "gap_count": 0,
            "gaps": [],
        }

    interval_values = [
        row[2]
        for row in interval_rows
    ]

    sorted_intervals = sorted(interval_values)
    interval_count = len(sorted_intervals)

    middle = interval_count // 2

    if interval_count % 2 == 1:
        median_interval = sorted_intervals[middle]
    else:
        median_interval = (
            sorted_intervals[middle - 1]
            + sorted_intervals[middle]
        ) / 2.0

    gap_threshold = median_interval * gap_factor

    gaps = []

    for previous_time, current_time, interval_seconds in interval_rows:
        if interval_seconds > gap_threshold:
            gaps.append(
                {
                    "from": json_safe_temporal(previous_time),
                    "to": json_safe_temporal(current_time),
                    "interval_seconds": interval_seconds,
                    "multiple_of_median": round(
                        interval_seconds / median_interval,
                        4,
                    ),
                }
            )

    gaps.sort(
        key=lambda gap: gap["interval_seconds"],
        reverse=True,
    )

    return {
        "column": column_name,
        "status": "ok",
        "gap_factor": gap_factor,
        "median_interval_seconds": median_interval,
        "gap_threshold_seconds": gap_threshold,
        "gap_count": len(gaps),
        "gaps": gaps[:top_n],
    }
def analyze_numeric_temporal_trend(
    connection: duckdb.DuckDBPyConnection,
    relation: duckdb.DuckDBPyRelation,
    time_column: str,
    value_column: str,
    time_format_hint: str | None = None,
    excluded_time_values: list[str] | None = None,
    excluded_value_values: list[str] | None = None,
) -> dict:
    if time_column not in relation.columns:
        raise ValueError(
            f"Column not found: {time_column}"
        )

    if value_column not in relation.columns:
        raise ValueError(
            f"Column not found: {value_column}"
        )

    value_index = relation.columns.index(value_column)
    value_type = str(relation.types[value_index])

    if not is_numeric_type(value_type):
        raise ValueError(
            f"Column is not numeric: "
            f"{value_column} ({value_type})"
        )

    excluded_time_values = excluded_time_values or []
    excluded_value_values = excluded_value_values or []

    relation.create_view(
        "rawsight_temporal_source",
        replace=True,
    )

    time_identifier = quote_identifier(time_column)
    value_identifier = quote_identifier(value_column)

    if time_format_hint == "YYYYMMDD":
        parsed_time_expression = (
            f"TRY_STRPTIME("
            f"CAST({time_identifier} AS VARCHAR), "
            f"'%Y%m%d'"
            f")"
        )
    else:
        parsed_time_expression = (
            f"TRY_CAST({time_identifier} AS TIMESTAMP)"
        )

    time_exclusion_sql = ""

    if excluded_time_values:
        quoted_values = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in excluded_time_values
        )

        time_exclusion_sql = (
            f"AND CAST({time_identifier} AS VARCHAR) "
            f"NOT IN ({quoted_values})"
        )

    value_exclusion_sql = ""

    if excluded_value_values:
        quoted_values = ", ".join(
            "'" + value.replace("'", "''") + "'"
            for value in excluded_value_values
        )

        value_exclusion_sql = (
            f"AND CAST({value_identifier} AS VARCHAR) "
            f"NOT IN ({quoted_values})"
        )

    result = connection.execute(
        f"""
        WITH parsed AS (
            SELECT
                {parsed_time_expression} AS parsed_time,
                CAST({value_identifier} AS DOUBLE) AS value
            FROM rawsight_temporal_source
            WHERE {time_identifier} IS NOT NULL
              AND {value_identifier} IS NOT NULL
              {time_exclusion_sql}
              {value_exclusion_sql}
        ),
        valid AS (
            SELECT
                parsed_time,
                value
            FROM parsed
            WHERE parsed_time IS NOT NULL
              AND ISFINITE(value)
        ),
        prepared AS (
            SELECT
                parsed_time,
                value,
                DATE_DIFF(
                    'second',
                    MIN(parsed_time) OVER (),
                    parsed_time
                ) / 86400.0 AS time_days
            FROM valid
        )
        SELECT
            COUNT(*) AS usable_rows,
            COUNT(DISTINCT parsed_time) AS distinct_time_points,
            MIN(parsed_time) AS first_observation,
            MAX(parsed_time) AS last_observation,

            REGR_SLOPE(
                value,
                time_days
            ) AS slope_per_day,

            REGR_INTERCEPT(
                value,
                time_days
            ) AS intercept,

            CORR(
                value,
                time_days
            ) AS pearson_time_correlation,

            REGR_R2(
                value,
                time_days
            ) AS r_squared

        FROM prepared
        """
    ).fetchone()

    (
        usable_rows,
        distinct_time_points,
        first_observation,
        last_observation,
        slope_per_day,
        intercept,
        pearson_time_correlation,
        r_squared,
    ) = result

    return {
        "time_column": time_column,
        "value_column": value_column,
        "value_technical_type": value_type,
        "method": "linear temporal trend",
        "usable_rows": usable_rows,
        "distinct_time_points": distinct_time_points,
        "first_observation": json_safe_temporal(
            first_observation
        ),
        "last_observation": json_safe_temporal(
            last_observation
        ),
       "slope_per_day": (
        round(slope_per_day, 6)
        if slope_per_day is not None
        else None
       ),
       "intercept": (
        round(intercept, 6)
        if intercept is not None
        else None
       ),
       "pearson_time_correlation": (
        round(pearson_time_correlation, 6)
        if pearson_time_correlation is not None
        else None
       ),
       "r_squared": (
        round(r_squared, 6)
        if r_squared is not None
        else None
      ) ,
    }
