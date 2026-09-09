import json
import sys

import duckdb

from rawsight.datasets import open_dataset
from rawsight.raw_analysis.runner import (
    analyze_numeric_temporal_pair,
)


if __name__ == "__main__":
    try:
        file_path = sys.argv[1]
        time_column = sys.argv[2]
        value_column = sys.argv[3]

        time_format_hint = (
            sys.argv[4].strip()
            if len(sys.argv) > 4
            and sys.argv[4].strip()
            else None
        )

        excluded_time_values = (
            json.loads(sys.argv[5])
            if len(sys.argv) > 5
            and sys.argv[5].strip()
            else None
        )

        excluded_value_values = (
            json.loads(sys.argv[6])
            if len(sys.argv) > 6
            and sys.argv[6].strip()
            else None
        )

        max_points = (
            int(sys.argv[7])
            if len(sys.argv) > 7
            and sys.argv[7].strip()
            else 1000
        )

        if (
            excluded_time_values is not None
            and not isinstance(
                excluded_time_values,
                list,
            )
        ):
            raise ValueError(
                "excluded_time_values must be a JSON array"
            )

        if (
            excluded_value_values is not None
            and not isinstance(
                excluded_value_values,
                list,
            )
        ):
            raise ValueError(
                "excluded_value_values must be a JSON array"
            )

        if excluded_time_values is not None:
            excluded_time_values = [
                str(value)
                for value in excluded_time_values
            ]

        if excluded_value_values is not None:
            excluded_value_values = [
                str(value)
                for value in excluded_value_values
            ]

        connection = duckdb.connect()

        relation = open_dataset(
            connection,
            file_path,
        )

        result = analyze_numeric_temporal_pair(
            connection,
            relation,
            time_column,
            value_column,
            time_format_hint=time_format_hint,
            excluded_time_values=excluded_time_values,
            excluded_value_values=excluded_value_values,
            max_points=max_points,
        )

        print(
            "RESULT\t"
            + json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            ),
            flush=True,
        )

    except Exception as error:
        print(
            f"ERROR\t{error}",
            flush=True,
        )
        sys.exit(1)