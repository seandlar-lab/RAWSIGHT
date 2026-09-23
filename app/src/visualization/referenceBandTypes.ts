export type ReferenceBandPoint = {
  index: number;
  label: string;
  selectedValue: number | null;
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  populationCount: number;
  numericCount: number;
};

export type ReferenceBandChartProps = {
  points: ReferenceBandPoint[];
  title?: string;
  ariaLabel?: string;
};
