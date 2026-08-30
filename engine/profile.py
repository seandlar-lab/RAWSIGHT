import json
import sys

from rawsight.light_analysis import profile_dataset


if __name__ == "__main__":
    try:
        result = profile_dataset(sys.argv[1])

        print(
            "RESULT\t"
            + json.dumps(
                result,
                ensure_ascii=False,
            ),
            flush=True,
        )

    except Exception as error:
        print(
            f"ERROR\t{error}",
            flush=True,
        )
        sys.exit(1)