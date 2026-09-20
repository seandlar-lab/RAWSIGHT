import type {
  TimeSeriesChartProps,
  TimeSeriesMarker,
  TimeSeriesPoint,
} from "./types";

function numericValues(
  points: TimeSeriesPoint[],
): number[] {
  return points
    .map((point) => point.value)
    .filter(
      (value): value is number =>
        value !== null &&
        Number.isFinite(value),
    );
}

export function TimeSeriesChart({
  points,
  markers = [],
  title = "Time series",
  ariaLabel = "Time series chart",
  markerLegend,
}: TimeSeriesChartProps) {
  const width = 900;
  const height = 300;

  const padding = {
    left: 64,
    right: 24,
    top: 24,
    bottom: 44,
  };

  const plotWidth =
    width - padding.left - padding.right;
  const plotHeight =
    height - padding.top - padding.bottom;

  const values = numericValues(points);

  if (values.length === 0) {
    return (
      <div
        style={{
          padding: "16px",
          border: "1px solid currentColor",
          borderRadius: "8px",
          opacity: 0.7,
        }}
      >
        No numeric values available to plot.
      </div>
    );
  }

  const observedMin = Math.min(...values);
  const observedMax = Math.max(...values);

  const scalePadding =
    observedMax === observedMin
      ? Math.max(
          Math.abs(observedMax) * 0.05,
          1,
        )
      : 0;

  const scaleMin =
    observedMin - scalePadding;
  const scaleMax =
    observedMax + scalePadding;

  const valueRange =
    scaleMax - scaleMin || 1;

  const pointCount = points.length;

  const xForPosition = (
    position: number,
  ) =>
    padding.left +
    (pointCount <= 1
      ? plotWidth / 2
      : (position / (pointCount - 1)) *
        plotWidth);

  const yForValue = (
    value: number,
  ) =>
    padding.top +
    ((scaleMax - value) / valueRange) *
      plotHeight;

  const segments: string[] = [];
  let currentSegment: string[] = [];

  points.forEach(
    (point, position) => {
      if (
        point.value !== null &&
        Number.isFinite(point.value)
      ) {
        currentSegment.push(
          `${xForPosition(
            position,
          )},${yForValue(point.value)}`,
        );
        return;
      }

      if (currentSegment.length > 0) {
        segments.push(
          currentSegment.join(" "),
        );
        currentSegment = [];
      }
    },
  );

  if (currentSegment.length > 0) {
    segments.push(
      currentSegment.join(" "),
    );
  }

  const positionByIndex = new Map(
    points.map(
      (point, position) => [
        point.index,
        position,
      ],
    ),
  );

  const resolvedMarkers = markers
    .map((marker) => {
      const position =
        positionByIndex.get(
          marker.index,
        );

      if (position === undefined) {
        return null;
      }

      return {
        ...marker,
        x: xForPosition(position),
        y: yForValue(marker.value),
      };
    })
    .filter(
      (
        marker,
      ): marker is TimeSeriesMarker & {
        x: number;
        y: number;
      } => marker !== null,
    );

  const firstLabel =
    points[0]?.label ?? "";

  const lastLabel =
    points[
      points.length - 1
    ]?.label ?? "";

  return (
    <div
      style={{
        display: "grid",
        gap: "8px",
        width: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <strong>{title}</strong>

        <span>
          Min{" "}
          {observedMin.toLocaleString()}
          {" · "}
          Max{" "}
          {observedMax.toLocaleString()}
        </span>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={ariaLabel}
        style={{
          width: "100%",
          height: "auto",
          minHeight: "240px",
          overflow: "visible",
        }}
      >
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={
            height - padding.bottom
          }
          stroke="currentColor"
          opacity="0.25"
          vectorEffect="non-scaling-stroke"
        />

        <line
          x1={padding.left}
          y1={
            height - padding.bottom
          }
          x2={
            width - padding.right
          }
          y2={
            height - padding.bottom
          }
          stroke="currentColor"
          opacity="0.25"
          vectorEffect="non-scaling-stroke"
        />

        <line
          x1={padding.left}
          y1={padding.top}
          x2={
            width - padding.right
          }
          y2={padding.top}
          stroke="currentColor"
          opacity="0.08"
          vectorEffect="non-scaling-stroke"
        />

        <line
          x1={padding.left}
          y1={
            padding.top +
            plotHeight / 2
          }
          x2={
            width - padding.right
          }
          y2={
            padding.top +
            plotHeight / 2
          }
          stroke="currentColor"
          opacity="0.08"
          vectorEffect="non-scaling-stroke"
        />

        {segments.map(
          (segment, index) => (
            <polyline
              key={index}
              points={segment}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          ),
        )}

        {resolvedMarkers.map(
          (marker) => (
            <circle
              key={`${marker.index}-${marker.label ?? ""}`}
              cx={marker.x}
              cy={marker.y}
              r="5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            >
              {(marker.title ||
                marker.label) && (
                <title>
                  {marker.title ??
                    marker.label}
                </title>
              )}
            </circle>
          ),
        )}

        <text
          x={padding.left - 10}
          y={padding.top + 4}
          textAnchor="end"
          fontSize="14"
          fill="currentColor"
        >
          {observedMax.toLocaleString()}
        </text>

        <text
          x={padding.left - 10}
          y={
            height -
            padding.bottom +
            4
          }
          textAnchor="end"
          fontSize="14"
          fill="currentColor"
        >
          {observedMin.toLocaleString()}
        </text>
      </svg>

      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: "16px",
        }}
      >
        <span>{firstLabel}</span>
        <span>{lastLabel}</span>
      </div>

      {markerLegend &&
        resolvedMarkers.length > 0 && (
          <span>{markerLegend}</span>
        )}
    </div>
  );
}
