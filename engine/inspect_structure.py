import json
import sys

from rawsight.structure import inspect_structure


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "ERROR\tUsage: inspect_structure.py <dataset_path>",
            flush=True,
        )
        sys.exit(1)

    try:
        result = inspect_structure(sys.argv[1])

        print(
            "RESULT\t" + json.dumps(result, ensure_ascii=False),
            flush=True,
        )

    except Exception as exc:
        print(
            f"ERROR\t{exc}",
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()