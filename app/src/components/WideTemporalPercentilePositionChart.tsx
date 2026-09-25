import type {
  WideTemporalReferenceComparisonExecution,
} from "../types/wideTemporalReferenceComparison";
import {
  PercentilePositionChart,
} from "../visualization/PercentilePositionChart";
import type {
  PercentilePositionPoint,
} from "../visualization/percentilePositionTypes";

type Props = {
  comparison: WideTemporalReferenceComparisonExecution;
  inspectionIndex: number | null;
  inspectionLocked: boolean;
  onInspectionHover: (index: number | null) => void;
  onInspectionToggle: (index: number) => void;
};

export function WideTemporalPercentilePositionChart({
  comparison,
  inspectionIndex,
  inspectionLocked,
  onInspectionHover,
  onInspectionToggle,
}: Props) {
  const points: PercentilePositionPoint[] =
    comparison.comparison.positions.map(
      (position) => ({
        index:
          position.axis_index,
        label:
          position.label,
        percentile:
          position.percentile_position,
        observedValue:
          position.selected_value,
        referenceMedian:
          position.reference_median,
        differenceFromMedian:
          position.difference_from_median,
        referenceNumericCount:
          position.reference_numeric_count,
      }),
    );

  return (
    <PercentilePositionChart
      points={points}
      title="Percentile position over time"
      ariaLabel={
        "Selected wide temporal series percentile position in the dataset reference population"
      }
      inspectionIndex={
        inspectionIndex
      }
      inspectionLocked={
        inspectionLocked
      }
      onInspectionHover={
        onInspectionHover
      }
      onInspectionToggle={
        onInspectionToggle
      }
    />
  );
}
