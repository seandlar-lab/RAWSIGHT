import type {
  WideTemporalSeriesDetail,
} from "../types/wideTemporalExplore";
import {
  TimeSeriesChart,
} from "../visualization";
import type {
  TimeSeriesMarker,
  TimeSeriesPoint,
} from "../visualization";

type Props = {
  detail: WideTemporalSeriesDetail;
};

export function WideTemporalSeriesChart({
  detail,
}: Props) {
  const points: TimeSeriesPoint[] =
    detail.temporal_points.map(
      (point) => ({
        index: point.axis_index,
        label: point.label,
        value:
          typeof point.value ===
            "number" &&
          Number.isFinite(point.value)
            ? point.value
            : null,
      }),
    );

  const markers: TimeSeriesMarker[] =
    detail.negative_transitions.map(
      (transition) => ({
        index: transition.to_index,
        value:
          transition.current_value,
        label:
          `${transition.from_label} → ` +
          `${transition.to_label}`,
        title:
          `${transition.from_label} → ` +
          `${transition.to_label}` +
          ` · change ${transition.change}`,
      }),
    );

  return (
    <TimeSeriesChart
      points={points}
      markers={markers}
      title="Observed time series"
      ariaLabel={
        `Observed time series for series ` +
        `${detail.series_index}`
      }
      markerLegend={
        "Hollow markers show observed " +
        "negative adjacent transitions."
      }
    />
  );
}
