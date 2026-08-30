import json
import sys

from rawsight.row_inspection import inspect_rows


if __name__ == "__main__":
    try:
        file_path = sys.argv[1]
        column_name = sys.argv[2]
        value = sys.argv[3]

        limit = (
            int(sys.argv[4])
            if len(sys.argv) > 4
            else 100
        )

        result = inspect_rows(
            file_path,
            column_name,
            value,
            limit,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
            )
        )

    except Exception as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                },
                ensure_ascii=False,
            )
        )

        sys.exit(1)