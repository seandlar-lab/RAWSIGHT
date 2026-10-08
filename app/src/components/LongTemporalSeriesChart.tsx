import type {
  LongTemporalSeriesResult,
} from "../types/longTemporalSeries";

import {
  TimeSeriesChart,
} from "../visualization";

import type {
  TimeSeriesPoint,
} from "../visualization";

type Props = {
  result: LongTemporalSeriesResult;
};

export function LongTemporalSeriesChart({
  result,
}: Props) {
  const points: TimeSeriesPoint[] =
    result.display_projection.points.map(
      (point) => ({
        index: point.projection_index,
        label: point.time,
        value:
          typeof point.mean === "number" &&
          Number.isFinite(point.mean)
            ? point.mean
            : null,
      }),
    );

  return (
    <TimeSeriesChart
      points={points}
      title="Temporal series projection"
      ariaLabel={
        `Temporal series projection for ` +
        `${result.value_column_name}`
      }
    />
  );
}
