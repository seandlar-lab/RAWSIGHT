import json
import sys

from rawsight.datasets import (
    inspect_source,
    select_analysis_strategy,
)
from rawsight.light_analysis import (
    profile_dataset,
)
from rawsight.wide_temporal_execution import (
    execute_wide_temporal_series_detail,
    execute_wide_temporal_series_page,
)


def _print_result(result: dict) -> None:
    print(
        "RESULT\t"
        + json.dumps(
            result,
            ensure_ascii=False,
        ),
        flush=True,
    )


def _wide_temporal_axis(
    file_path: str,
) -> dict:
    """
    Detect and validate the structural route used by Explore.

    The bridge does not infer a new axis. It reuses the same structural
    detection and strategy routing as Light Analysis.
    """

    inspection = inspect_source(
        file_path
    )

    structural_model = inspection.get(
        "structural_model",
        {},
    )

    strategy = select_analysis_strategy(
        structural_model
    )

    if strategy.get("strategy") != "wide_temporal":
        raise ValueError(
            "Series Explorer requires a "
            "wide_temporal analysis strategy"
        )

    logical_structure = structural_model.get(
        "logical_structure",
        {},
    )

    temporal_axis = logical_structure.get(
        "temporal_axis"
    )

    if not isinstance(
        temporal_axis,
        dict,
    ):
        raise ValueError(
            "No promoted temporal axis is available"
        )

    if temporal_axis.get(
        "orientation"
    ) != "horizontal":
        raise ValueError(
            "Series Explorer requires a "
            "horizontal temporal axis"
        )

    return temporal_axis


def _run_profile(
    file_path: str,
) -> dict:
    return profile_dataset(
        file_path
    )


def _run_wide_temporal_series_page(
    arguments: list[str],
) -> dict:
    if len(arguments) != 5:
        raise ValueError(
            "wide-temporal-series-page requires: "
            "<path> <classification> <offset> <limit>"
        )

    file_path = arguments[1]

    classification = (
        arguments[2].strip()
        or None
    )

    offset = int(
        arguments[3]
    )
    limit = int(
        arguments[4]
    )

    temporal_axis = (
        _wide_temporal_axis(
            file_path
        )
    )

    return (
        execute_wide_temporal_series_page(
            file_path=file_path,
            temporal_axis=temporal_axis,
            classification=classification,
            offset=offset,
            limit=limit,
        )
    )


def _run_wide_temporal_series_detail(
    arguments: list[str],
) -> dict:
    if len(arguments) != 3:
        raise ValueError(
            "wide-temporal-series-detail requires: "
            "<path> <series_index>"
        )

    file_path = arguments[1]

    series_index = int(
        arguments[2]
    )

    temporal_axis = (
        _wide_temporal_axis(
            file_path
        )
    )

    return (
        execute_wide_temporal_series_detail(
            file_path=file_path,
            temporal_axis=temporal_axis,
            series_index=series_index,
        )
    )


def main(arguments: list[str]) -> int:
    """
    Backward-compatible engine entrypoint.

    Existing invocation:
        profile.py <path>

    Explore invocations:
        profile.py wide-temporal-series-page
            <path> <classification> <offset> <limit>

        profile.py wide-temporal-series-detail
            <path> <series_index>
    """

    if not arguments:
        raise ValueError(
            "Dataset path or engine command is required"
        )

    command = arguments[0]

    if command == "wide-temporal-series-page":
        result = (
            _run_wide_temporal_series_page(
                arguments
            )
        )
    elif command == "wide-temporal-series-detail":
        result = (
            _run_wide_temporal_series_detail(
                arguments
            )
        )
    else:
        if len(arguments) != 1:
            raise ValueError(
                "Profiling requires exactly one "
                "dataset path"
            )

        result = _run_profile(
            command
        )

    _print_result(
        result
    )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(
            main(
                sys.argv[1:]
            )
        )

    except Exception as error:
        print(
            f"ERROR\t{error}",
            flush=True,
        )
        sys.exit(1)
