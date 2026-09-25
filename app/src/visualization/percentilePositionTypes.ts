import type { InspectionLinkProps } from "./inspectionTypes";

export type PercentilePositionPoint = {
  index: number;
  label: string;
  percentile: number | null;
  observedValue?: number | null;
  referenceMedian?: number | null;
  differenceFromMedian?: number | null;
  referenceNumericCount?: number | null;
};

export type PercentilePositionChartProps = InspectionLinkProps & {
  points: PercentilePositionPoint[];
  title?: string;
  ariaLabel?: string;
};
