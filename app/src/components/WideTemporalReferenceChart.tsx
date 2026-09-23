import type {
  WideTemporalSeriesDetail,
} from "../types/wideTemporalExplore";
import type {
  WideTemporalReferenceProfile,
} from "../types/wideTemporalReference";
import {
  ReferenceBandChart,
} from "../visualization/ReferenceBandChart";
import type {
  ReferenceBandPoint,
} from "../visualization/referenceBandTypes";

type Props = {
  detail: WideTemporalSeriesDetail;
  reference: WideTemporalReferenceProfile;
};

function finiteNumericValue(
  value: string | number | boolean | null,
): number | null {
  if (
    typeof value === "number" &&
    Number.isFinite(value)
  ) {
    return value;
  }

  return null;
}

export function WideTemporalReferenceChart({
  detail,
  reference,
}: Props) {
  const selectedByAxisIndex =
    new Map(
      detail.temporal_points.map(
        (point) => [
          point.axis_index,
          finiteNumericValue(
            point.value,
          ),
        ],
      ),
    );

  const points: ReferenceBandPoint[] =
    reference.positions.map(
      (position) => ({
        index:
          position.axis_index,
        label:
          position.label,
        selectedValue:
          selectedByAxisIndex.get(
            position.axis_index,
          ) ?? null,
        p10: position.p10,
        p25: position.p25,
        p50: position.p50,
        p75: position.p75,
        p90: position.p90,
        populationCount:
          position.population_count,
        numericCount:
          position.numeric_count,
      }),
    );

  return (
    <ReferenceBandChart
      points={points}
      title="Compared with dataset reference"
      ariaLabel={
        "Selected wide temporal series compared with the dataset reference population"
      }
    />
  );
}
