import {
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

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

function nearestNumericPosition(
  points: TimeSeriesPoint[],
  requestedPosition: number,
): number | null {
  if (points.length === 0) {
    return null;
  }

  const boundedPosition = Math.max(
    0,
    Math.min(
      points.length - 1,
      requestedPosition,
    ),
  );

  const directPoint =
    points[boundedPosition];

  if (
    directPoint.value !== null &&
    Number.isFinite(
      directPoint.value,
    )
  ) {
    return boundedPosition;
  }

  for (
    let distance = 1;
    distance < points.length;
    distance += 1
  ) {
    const left =
      boundedPosition - distance;
    const right =
      boundedPosition + distance;

    if (left >= 0) {
      const point = points[left];

      if (
        point.value !== null &&
        Number.isFinite(
          point.value,
        )
      ) {
        return left;
      }
    }

    if (right < points.length) {
      const point = points[right];

      if (
        point.value !== null &&
        Number.isFinite(
          point.value,
        )
      ) {
        return right;
      }
    }
  }

  return null;
}

export function TimeSeriesChart({
  points,
  markers = [],
  title = "Time series",
  ariaLabel = "Time series chart",
  markerLegend,
}: TimeSeriesChartProps) {
  const width = 720;
  const height = 340;

  const padding = {
    left: 84,
    right: 24,
    top: 28,
    bottom: 52,
  };

  const plotWidth =
    width - padding.left - padding.right;
  const plotHeight =
    height - padding.top - padding.bottom;

  const values = numericValues(points);

  const [
    hoverPosition,
    setHoverPosition,
  ] = useState<number | null>(null);

  if (values.length === 0) {
    return (
      <div
        style={{
          padding: "16px",
          border: "1px solid currentColor",
          borderRadius: "8px",
          opacity: 0.75,
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
        position,
        x: xForPosition(position),
        y: yForValue(marker.value),
      };
    })
    .filter(
      (
        marker,
      ): marker is TimeSeriesMarker & {
        position: number;
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

  const yTicks = Array.from(
    { length: 5 },
    (_, index) => {
      const ratio = index / 4;
      const value =
        scaleMax -
        valueRange * ratio;

      return {
        value,
        y:
          padding.top +
          plotHeight * ratio,
      };
    },
  );

  const hoveredPoint =
    hoverPosition === null
      ? null
      : points[hoverPosition] ?? null;

  const hoveredX =
    hoverPosition === null
      ? null
      : xForPosition(hoverPosition);

  const hoveredY =
    hoveredPoint?.value === null ||
    hoveredPoint?.value === undefined
      ? null
      : yForValue(
          hoveredPoint.value,
        );

  function handlePointerMove(
    event: ReactPointerEvent<SVGSVGElement>,
  ) {
    const bounds =
      event.currentTarget.getBoundingClientRect();

    if (
      bounds.width <= 0 ||
      pointCount === 0
    ) {
      return;
    }

    const viewBoxX =
      ((event.clientX - bounds.left) /
        bounds.width) *
      width;

    const clampedX = Math.max(
      padding.left,
      Math.min(
        width - padding.right,
        viewBoxX,
      ),
    );

    const requestedPosition =
      pointCount <= 1
        ? 0
        : Math.round(
            ((clampedX - padding.left) /
              plotWidth) *
              (pointCount - 1),
          );

    setHoverPosition(
      nearestNumericPosition(
        points,
        requestedPosition,
      ),
    );
  }

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

      <div
        style={{
          minHeight: "44px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          padding: "8px 10px",
          border: hoveredPoint
            ? "1px solid CanvasText"
            : "1px solid transparent",
          borderRadius: "6px",
          background: hoveredPoint
            ? "Canvas"
            : "transparent",
        }}
      >
        {hoveredPoint ? (
          <>
            <strong>Inspecting</strong>
            <span>
              {hoveredPoint.label}
            </span>
            <span>
              Value{" "}
              <strong>
                {hoveredPoint.value?.toLocaleString()}
              </strong>
            </span>
            <span>
              Position{" "}
              <strong>
                {hoveredPoint.index}
              </strong>
            </span>
          </>
        ) : (
          <span
            style={{
              opacity: 0.7,
            }}
          >
            Hover over the plot to inspect the nearest observed point.
          </span>
        )}
      </div>

      <div
        style={{
          position: "relative",
          width: "100%",
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={ariaLabel}
          onPointerMove={
            handlePointerMove
          }
          onPointerLeave={() =>
            setHoverPosition(null)
          }
          shapeRendering="geometricPrecision"
          style={{
            width: "100%",
            height: "auto",
            minHeight: "280px",
            overflow: "visible",
            cursor: "crosshair",
          }}
        >
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={
              height - padding.bottom
            }
            stroke="CanvasText"
            opacity="0.85"
            strokeWidth="2"
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
            stroke="CanvasText"
            opacity="0.85"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />


          {segments.map(
            (segment, index) => (
              <polyline
                key={index}
                points={segment}
                fill="none"
                stroke="CanvasText"
                strokeWidth="3.8"
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
                r="6"
                fill="Canvas"
                stroke="CanvasText"
                strokeWidth="3"
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

          {hoveredX !== null &&
            hoveredY !== null &&
            hoveredPoint && (
              <>
                <line
                  x1={hoveredX}
                  y1={padding.top}
                  x2={hoveredX}
                  y2={
                    height -
                    padding.bottom
                  }
                  stroke="CanvasText"
                  opacity="0.85"
                  strokeWidth="2.4"
                  strokeDasharray="7 5"
                  vectorEffect="non-scaling-stroke"
                />

                <circle
                  cx={hoveredX}
                  cy={hoveredY}
                  r="10"
                  fill="none"
                  stroke="CanvasText"
                  strokeWidth="2"
                  opacity="0.65"
                  vectorEffect="non-scaling-stroke"
                />

                <circle
                  cx={hoveredX}
                  cy={hoveredY}
                  r="5.5"
                  fill="CanvasText"
                  stroke="Canvas"
                  strokeWidth="2.5"
                  vectorEffect="non-scaling-stroke"
                />
              </>
            )}

          {yTicks.map(
            (tick, index) => (
              <g key={`y-tick-${index}`}>
                <line
                  x1={padding.left}
                  y1={tick.y}
                  x2={width - padding.right}
                  y2={tick.y}
                  stroke="CanvasText"
                  opacity={
                    index === 0 ||
                    index === yTicks.length - 1
                      ? 0.22
                      : 0.14
                  }
                  strokeWidth="1.2"
                  vectorEffect="non-scaling-stroke"
                />

                <line
                  x1={padding.left - 7}
                  y1={tick.y}
                  x2={padding.left}
                  y2={tick.y}
                  stroke="CanvasText"
                  opacity="0.85"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                />

                <text
                  x={padding.left - 14}
                  y={tick.y + 7}
                  textAnchor="end"
                  fontSize="22"
                  fontWeight="600"
                  fill="CanvasText"
                  opacity="0.95"
                >
                  {Number(
                    tick.value.toFixed(
                      Math.abs(tick.value) < 10 &&
                      tick.value % 1 !== 0
                        ? 1
                        : 0,
                    ),
                  ).toLocaleString()}
                </text>
              </g>
            ),
          )}
        </svg>

      </div>

      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: "16px",
          fontWeight: 600,
          color: "CanvasText",
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
