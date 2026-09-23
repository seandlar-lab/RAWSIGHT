import {
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type {
  ReferenceBandChartProps,
  ReferenceBandPoint,
} from "./referenceBandTypes";

function isFiniteNumber(
  value: number | null,
): value is number {
  return (
    value !== null &&
    Number.isFinite(value)
  );
}

function numericValues(
  points: ReferenceBandPoint[],
): number[] {
  const values: number[] = [];

  for (const point of points) {
    for (const value of [
      point.selectedValue,
      point.p10,
      point.p90,
    ]) {
      if (isFiniteNumber(value)) {
        values.push(value);
      }
    }
  }

  return values;
}

function formatValue(
  value: number | null,
): string {
  if (!isFiniteNumber(value)) {
    return "—";
  }

  const absolute = Math.abs(value);

  if (
    absolute >= 1000 ||
    Number.isInteger(value)
  ) {
    return value.toLocaleString();
  }

  return Number(
    value.toFixed(2),
  ).toLocaleString();
}

function formatAxisValue(
  value: number,
): string {
  const absolute = Math.abs(value);

  const formatScaled = (
    divisor: number,
    suffix: string,
  ) => {
    const scaled = value / divisor;

    const decimals =
      Math.abs(scaled) >= 100
        ? 0
        : Math.abs(scaled) >= 10
          ? 1
          : 2;

    return `${Number(
      scaled.toFixed(decimals),
    )}${suffix}`;
  };

  if (absolute >= 1_000_000_000) {
    return formatScaled(
      1_000_000_000,
      "B",
    );
  }

  if (absolute >= 1_000_000) {
    return formatScaled(
      1_000_000,
      "M",
    );
  }

  if (absolute >= 1_000) {
    return formatScaled(
      1_000,
      "K",
    );
  }

  if (absolute >= 100) {
    return String(
      Math.round(value),
    );
  }

  if (absolute >= 10) {
    return String(
      Number(value.toFixed(1)),
    );
  }

  return String(
    Number(value.toFixed(2)),
  );
}

function buildLineSegments(
  points: ReferenceBandPoint[],
  valueForPoint: (
    point: ReferenceBandPoint,
  ) => number | null,
  xForPosition: (
    position: number,
  ) => number,
  yForValue: (
    value: number,
  ) => number,
): string[] {
  const segments: string[] = [];
  let current: string[] = [];

  points.forEach(
    (point, position) => {
      const value =
        valueForPoint(point);

      if (isFiniteNumber(value)) {
        current.push(
          `${xForPosition(position)},${yForValue(
            value,
          )}`,
        );
        return;
      }

      if (current.length > 0) {
        segments.push(
          current.join(" "),
        );
        current = [];
      }
    },
  );

  if (current.length > 0) {
    segments.push(
      current.join(" "),
    );
  }

  return segments;
}

function buildBandPolygons(
  points: ReferenceBandPoint[],
  lowerForPoint: (
    point: ReferenceBandPoint,
  ) => number | null,
  upperForPoint: (
    point: ReferenceBandPoint,
  ) => number | null,
  xForPosition: (
    position: number,
  ) => number,
  yForValue: (
    value: number,
  ) => number,
): string[] {
  const polygons: string[] = [];
  let current: {
    position: number;
    lower: number;
    upper: number;
  }[] = [];

  const flush = () => {
    if (current.length === 0) {
      return;
    }

    const upperPoints =
      current.map(
        ({ position, upper }) =>
          `${xForPosition(position)},${yForValue(
            upper,
          )}`,
      );

    const lowerPoints =
      [...current]
        .reverse()
        .map(
          ({ position, lower }) =>
            `${xForPosition(position)},${yForValue(
              lower,
            )}`,
        );

    polygons.push(
      [
        ...upperPoints,
        ...lowerPoints,
      ].join(" "),
    );

    current = [];
  };

  points.forEach(
    (point, position) => {
      const lower =
        lowerForPoint(point);
      const upper =
        upperForPoint(point);

      if (
        isFiniteNumber(lower) &&
        isFiniteNumber(upper)
      ) {
        current.push({
          position,
          lower,
          upper,
        });
        return;
      }

      flush();
    },
  );

  flush();

  return polygons;
}

export function ReferenceBandChart({
  points,
  title = "Compared with dataset reference",
  ariaLabel = "Selected time series compared with dataset reference percentiles",
}: ReferenceBandChartProps) {
  const width = 720;
  const height = 360;

  const padding = {
    left: 72,
    right: 24,
    top: 28,
    bottom: 52,
  };

  const plotWidth =
    width -
    padding.left -
    padding.right;

  const plotHeight =
    height -
    padding.top -
    padding.bottom;

  const values =
    numericValues(points);

  const [
    hoverPosition,
    setHoverPosition,
  ] = useState<number | null>(
    null,
  );

  if (
    points.length === 0 ||
    values.length === 0
  ) {
    return (
      <div
        style={{
          padding: "16px",
          border:
            "1px solid currentColor",
          borderRadius: "8px",
          opacity: 0.75,
        }}
      >
        No numeric reference values
        available to plot.
      </div>
    );
  }

  const observedMin =
    Math.min(...values);
  const observedMax =
    Math.max(...values);

  const scalePadding =
    observedMax === observedMin
      ? Math.max(
          Math.abs(observedMax) *
            0.05,
          1,
        )
      : (
          observedMax -
          observedMin
        ) * 0.04;

  const paddedMin =
    observedMin - scalePadding;
  const paddedMax =
    observedMax + scalePadding;

  const scaleMin =
    observedMin >= 0 &&
    paddedMin < 0
      ? 0
      : paddedMin;

  const scaleMax =
    observedMax <= 0 &&
    paddedMax > 0
      ? 0
      : paddedMax;

  const valueRange =
    scaleMax - scaleMin || 1;

  const pointCount =
    points.length;

  const xForPosition = (
    position: number,
  ) =>
    padding.left +
    (
      pointCount <= 1
        ? plotWidth / 2
        : (
            position /
            (pointCount - 1)
          ) * plotWidth
    );

  const yForValue = (
    value: number,
  ) =>
    padding.top +
    (
      (
        scaleMax -
        value
      ) /
      valueRange
    ) *
      plotHeight;

  const outerBand =
    buildBandPolygons(
      points,
      (point) => point.p10,
      (point) => point.p90,
      xForPosition,
      yForValue,
    );

  const innerBand =
    buildBandPolygons(
      points,
      (point) => point.p25,
      (point) => point.p75,
      xForPosition,
      yForValue,
    );

  const medianSegments =
    buildLineSegments(
      points,
      (point) => point.p50,
      xForPosition,
      yForValue,
    );

  const selectedSegments =
    buildLineSegments(
      points,
      (point) =>
        point.selectedValue,
      xForPosition,
      yForValue,
    );

  const yTicks = Array.from(
    { length: 5 },
    (_, index) =>
      scaleMin +
      (
        (
          4 - index
        ) /
        4
      ) *
        valueRange,
  );

  const onPointerMove = (
    event: ReactPointerEvent<
      SVGSVGElement
    >,
  ) => {
    const bounds =
      event.currentTarget
        .getBoundingClientRect();

    if (
      bounds.width <= 0 ||
      pointCount === 0
    ) {
      return;
    }

    const svgX =
      (
        (
          event.clientX -
          bounds.left
        ) /
        bounds.width
      ) * width;

    const boundedX =
      Math.max(
        padding.left,
        Math.min(
          width -
            padding.right,
          svgX,
        ),
      );

    const ratio =
      plotWidth <= 0
        ? 0
        : (
            boundedX -
            padding.left
          ) /
          plotWidth;

    const position =
      pointCount <= 1
        ? 0
        : Math.round(
            ratio *
              (
                pointCount - 1
              ),
          );

    setHoverPosition(
      Math.max(
        0,
        Math.min(
          pointCount - 1,
          position,
        ),
      ),
    );
  };

  const hoveredPoint =
    hoverPosition === null
      ? null
      : points[
          hoverPosition
        ];

  const hoverX =
    hoverPosition === null
      ? null
      : xForPosition(
          hoverPosition,
        );

  const firstPoint =
    points[0];
  const lastPoint =
    points[
      points.length - 1
    ];

  return (
    <div
      style={{
        display: "grid",
        gap: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        <strong>{title}</strong>

        <span
          style={{
            opacity: 0.75,
          }}
        >
          P10–P90 · P25–P75 ·
          P50
        </span>
      </div>

      <div
        style={{
          minHeight: "42px",
          display: "flex",
          alignItems: "center",
          gap: "14px",
          flexWrap: "wrap",
          opacity: 0.9,
        }}
      >
        {hoveredPoint ? (
          <>
            <strong>
              Inspecting{" "}
              {hoveredPoint.label}
            </strong>

            <span>
              Selected{" "}
              <strong>
                {formatValue(
                  hoveredPoint
                    .selectedValue,
                )}
              </strong>
            </span>

            <span>
              P50{" "}
              <strong>
                {formatValue(
                  hoveredPoint.p50,
                )}
              </strong>
            </span>

            <span>
              P25–P75{" "}
              <strong>
                {formatValue(
                  hoveredPoint.p25,
                )}
                {" – "}
                {formatValue(
                  hoveredPoint.p75,
                )}
              </strong>
            </span>

            <span>
              P10–P90{" "}
              <strong>
                {formatValue(
                  hoveredPoint.p10,
                )}
                {" – "}
                {formatValue(
                  hoveredPoint.p90,
                )}
              </strong>
            </span>

            <span>
              Numeric population{" "}
              <strong>
                {hoveredPoint.numericCount.toLocaleString()}
              </strong>
              {" / "}
              {hoveredPoint.populationCount.toLocaleString()}
            </span>
          </>
        ) : (
          <span>
            Hover over the plot to
            inspect the selected series
            against the reference
            population.
          </span>
        )}
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={ariaLabel}
        onPointerMove={
          onPointerMove
        }
        onPointerLeave={() =>
          setHoverPosition(null)
        }
        style={{
          width: "100%",
          height: "auto",
          display: "block",
          touchAction: "none",
        }}
        shapeRendering="geometricPrecision"
      >
        {yTicks.map(
          (tick, index) => {
            const y =
              yForValue(tick);

            return (
              <g key={index}>
                <line
                  x1={padding.left}
                  x2={
                    width -
                    padding.right
                  }
                  y1={y}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity={0.16}
                  strokeWidth={1}
                />

                <text
                  x={
                    padding.left -
                    10
                  }
                  y={y + 6}
                  textAnchor="end"
                  fontSize={17}
                  fontWeight={600}
                  fill="currentColor"
                >
                  {formatAxisValue(
                    tick,
                  )}
                </text>
              </g>
            );
          },
        )}

        {outerBand.map(
          (polygon, index) => (
            <polygon
              key={`outer-${index}`}
              points={polygon}
              fill="currentColor"
              fillOpacity={0.09}
              stroke="none"
            />
          ),
        )}

        {innerBand.map(
          (polygon, index) => (
            <polygon
              key={`inner-${index}`}
              points={polygon}
              fill="currentColor"
              fillOpacity={0.17}
              stroke="none"
            />
          ),
        )}

        {medianSegments.map(
          (segment, index) => (
            <polyline
              key={`median-${index}`}
              points={segment}
              fill="none"
              stroke="currentColor"
              strokeOpacity={0.62}
              strokeWidth={2}
              strokeDasharray="7 5"
              vectorEffect="non-scaling-stroke"
            />
          ),
        )}

        {selectedSegments.map(
          (segment, index) => (
            <polyline
              key={`selected-${index}`}
              points={segment}
              fill="none"
              stroke="currentColor"
              strokeWidth={3.2}
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          ),
        )}

        {hoverX !== null && (
          <line
            x1={hoverX}
            x2={hoverX}
            y1={padding.top}
            y2={
              height -
              padding.bottom
            }
            stroke="currentColor"
            strokeOpacity={0.55}
            strokeWidth={1.2}
            vectorEffect="non-scaling-stroke"
          />
        )}

        <line
          x1={padding.left}
          x2={padding.left}
          y1={padding.top}
          y2={
            height -
            padding.bottom
          }
          stroke="currentColor"
          strokeWidth={1.5}
          vectorEffect="non-scaling-stroke"
        />

        <line
          x1={padding.left}
          x2={
            width -
            padding.right
          }
          y1={
            height -
            padding.bottom
          }
          y2={
            height -
            padding.bottom
          }
          stroke="currentColor"
          strokeWidth={1.5}
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      <div
        style={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: "12px",
          fontWeight: 600,
        }}
      >
        <span>
          {firstPoint?.label ??
            "—"}
        </span>
        <span>
          {lastPoint?.label ??
            "—"}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          fontSize: "0.92em",
          opacity: 0.82,
        }}
      >
        <span>
          <strong>Solid line</strong>
          {" = selected series"}
        </span>
        <span>
          <strong>Dashed line</strong>
          {" = P50 median"}
        </span>
        <span>
          <strong>Darker band</strong>
          {" = P25–P75"}
        </span>
        <span>
          <strong>Lighter band</strong>
          {" = P10–P90"}
        </span>
      </div>
    </div>
  );
}
