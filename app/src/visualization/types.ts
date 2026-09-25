import type { InspectionLinkProps } from "./inspectionTypes";

export type TimeSeriesPoint = {
  index: number;
  label: string;
  value: number | null;
};

export type TimeSeriesMarker = {
  index: number;
  value: number;
  label?: string;
  title?: string;
};

export type TimeSeriesChartProps = InspectionLinkProps & {
  points: TimeSeriesPoint[];
  markers?: TimeSeriesMarker[];
  title?: string;
  ariaLabel?: string;
  markerLegend?: string;
};
