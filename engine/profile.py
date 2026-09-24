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
from rawsight.wide_temporal_reference_execution import (
    execute_wide_temporal_reference,
)
from rawsight.wide_temporal_reference_comparison_execution import (
    execute_wide_temporal_reference_comparison,
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


def _validated_temporal_axis_from_json(
    temporal_axis_json: str,
) -> dict:
    """
    Validate a temporal axis already established by Light Analysis.

    This path deliberately does not run source detection again.
    The caller supplies normalized structural context produced by
    the existing Detect -> Normalize -> Analyze flow.
    """

    try:
        temporal_axis = json.loads(
            temporal_axis_json
        )
    except json.JSONDecodeError as error:
        raise ValueError(
            "Temporal axis context is not valid JSON"
        ) from error

    if not isinstance(
        temporal_axis,
        dict,
    ):
        raise ValueError(
            "Temporal axis context must be an object"
        )

    if temporal_axis.get(
        "orientation"
    ) != "horizontal":
        raise ValueError(
            "Series Explorer requires a "
            "horizontal temporal axis"
        )

    start_index = temporal_axis.get(
        "start_index"
    )
    end_index = temporal_axis.get(
        "end_index"
    )

    if not isinstance(
        start_index,
        int,
    ):
        raise ValueError(
            "Temporal axis start_index is missing or invalid"
        )

    if not isinstance(
        end_index,
        int,
    ):
        raise ValueError(
            "Temporal axis end_index is missing or invalid"
        )

    if (
        start_index < 0
        or end_index < start_index
    ):
        raise ValueError(
            "Temporal axis range is invalid"
        )

    return {
        **temporal_axis,
        "orientation": "horizontal",
        "start_index": start_index,
        "end_index": end_index,
    }


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


def _run_wide_temporal_series_page_context(
    arguments: list[str],
) -> dict:
    if len(arguments) != 6:
        raise ValueError(
            "wide-temporal-series-page-context requires: "
            "<path> <temporal_axis_json> "
            "<classification> <offset> <limit>"
        )

    file_path = arguments[1]
    temporal_axis = (
        _validated_temporal_axis_from_json(
            arguments[2]
        )
    )
    classification = (
        arguments[3].strip()
        or None
    )
    offset = int(arguments[4])
    limit = int(arguments[5])

    return (
        execute_wide_temporal_series_page(
            file_path=file_path,
            temporal_axis=temporal_axis,
            classification=classification,
            offset=offset,
            limit=limit,
        )
    )


def _run_wide_temporal_series_detail_context(
    arguments: list[str],
) -> dict:
    if len(arguments) != 4:
        raise ValueError(
            "wide-temporal-series-detail-context requires: "
            "<path> <temporal_axis_json> <series_index>"
        )

    file_path = arguments[1]
    temporal_axis = (
        _validated_temporal_axis_from_json(
            arguments[2]
        )
    )
    series_index = int(arguments[3])

    return (
        execute_wide_temporal_series_detail(
            file_path=file_path,
            temporal_axis=temporal_axis,
            series_index=series_index,
        )
    )


def _run_wide_temporal_reference_context(
    arguments: list[str],
) -> dict:
    """
    Build the dataset-wide reference population using temporal
    structural context already established by Light Analysis.

    This command deliberately does not re-run Detect/Normalize.
    """

    if len(arguments) != 3:
        raise ValueError(
            "wide-temporal-reference-context requires: "
            "<path> <temporal_axis_json>"
        )

    file_path = arguments[1]
    temporal_axis = (
        _validated_temporal_axis_from_json(
            arguments[2]
        )
    )

    return (
        execute_wide_temporal_reference(
            file_path=file_path,
            temporal_axis=temporal_axis,
        )
    )



def _run_wide_temporal_reference_comparison_context(
    arguments: list[str],
) -> dict:
    """
    Compare one selected series with the exact dataset reference using
    temporal structural context already established by Light Analysis.

    This command deliberately does not re-run Detect/Normalize.
    """

    if len(arguments) != 4:
        raise ValueError(
            "wide-temporal-reference-comparison-context requires: "
            "<path> <temporal_axis_json> <series_index>"
        )

    file_path = arguments[1]
    temporal_axis = (
        _validated_temporal_axis_from_json(
            arguments[2]
        )
    )
    series_index = int(
        arguments[3]
    )

    return (
        execute_wide_temporal_reference_comparison(
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

        profile.py wide-temporal-reference-context
            <path> <temporal_axis_json>

        profile.py wide-temporal-reference-comparison-context
            <path> <temporal_axis_json> <series_index>
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
    elif command == "wide-temporal-series-page-context":
        result = (
            _run_wide_temporal_series_page_context(
                arguments
            )
        )
    elif command == "wide-temporal-series-detail-context":
        result = (
            _run_wide_temporal_series_detail_context(
                arguments
            )
        )
    elif command == "wide-temporal-reference-context":
        result = (
            _run_wide_temporal_reference_context(
                arguments
            )
        )
    elif command == "wide-temporal-reference-comparison-context":
        result = (
            _run_wide_temporal_reference_comparison_context(
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
