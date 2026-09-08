import json
import sys

import duckdb

from rawsight.datasets import open_dataset
from rawsight.raw_analysis.runner import analyze_column


if __name__ == "__main__":
    try:
        file_path = sys.argv[1]
        column_name = sys.argv[2]

        role = (
            sys.argv[3].strip()
            if len(sys.argv) > 3
            and sys.argv[3].strip()
            else None
        )

        semantic_type = (
            sys.argv[4].strip()
            if len(sys.argv) > 4
            and sys.argv[4].strip()
            else None
        )

        format_hint = (
            sys.argv[5].strip()
            if len(sys.argv) > 5
            and sys.argv[5].strip()
            else None
        )

        excluded_values = (
            json.loads(sys.argv[6])
            if len(sys.argv) > 6
            and sys.argv[6].strip()
            else None
        )

        if (
            excluded_values is not None
            and not isinstance(excluded_values, list)
        ):
            raise ValueError(
                "excluded_values must be a JSON array"
            )
        if excluded_values is not None:
            excluded_values = [
            str(value)
            for value in excluded_values
    ]

        connection = duckdb.connect()

        relation = open_dataset(
            connection,
            file_path,
        )

        result = analyze_column(
            connection,
            relation,
            column_name,
            semantic_type=semantic_type,
            format_hint=format_hint,
            excluded_values=excluded_values,
            role=role,
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