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
            sys.argv[3]
            if len(sys.argv) > 3
            else None
        )

        connection = duckdb.connect()

        relation = open_dataset(
            connection,
            file_path,
        )

        result = analyze_column(
            connection,
            relation,
            column_name,
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
    