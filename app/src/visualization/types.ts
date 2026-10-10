import type { InspectionLinkProps } from "./inspectionTypes";

export type TimeSeriesPoint = {
  index: number;
  label: string;
  axisLabel?: string;
  value: number | null;

  /**
   * Optional normalized horizontal position in the displayed
   * temporal span.
   *
   * 0 = start of span
   * 1 = end of span
   *
   * If omitted, the chart uses ordinal array position.
   */
  xPosition?: number;

  /**
   * Prevent drawing a line from the previous displayed point
   * to this point.
   */
  breakBefore?: boolean;
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
  seriesStrokeWidth?: number;
};