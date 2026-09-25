import {
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import type {
  PercentilePositionChartProps,
  PercentilePositionPoint,
} from "./percentilePositionTypes";

function finiteNumber(
  value: number | null | undefined,
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value)
  );
}

function formatValue(
  value: number | null | undefined,
): string {
  if (!finiteNumber(value)) {
    return "—";
  }

  if (Number.isInteger(value)) {
    return value.toLocaleString();
  }

  return Number(
    value.toFixed(2),
  ).toLocaleString();
}

function formatPercentile(
  value: number | null | undefined,
): string {
  if (!finiteNumber(value)) {
    return "—";
  }

  return `P${Number(
    value.toFixed(1),
  ).toLocaleString()}`;
}

function buildSegments(
  points: PercentilePositionPoint[],
  xForPosition: (position: number) => number,
  yForPercentile: (value: number) => number,
): string[] {
  const segments: string[] = [];
  let current: string[] = [];

  points.forEach(
    (point, position) => {
      if (finiteNumber(point.percentile)) {
        current.push(
          `${xForPosition(position)},${yForPercentile(
            point.percentile,
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

export function PercentilePositionChart({
  points,
  title = "Percentile position over time",
  ariaLabel = "Selected series percentile position over time",
  inspectionIndex,
  inspectionLocked = false,
  onInspectionHover,
  onInspectionToggle,
}: PercentilePositionChartProps) {
  const width = 720;
  const height = 340;

  const padding = {
    left: 66,
    right: 24,
    top: 24,
    bottom: 48,
  };

  const plotWidth =
    width -
    padding.left -
    padding.right;

  const plotHeight =
    height -
    padding.top -
    padding.bottom;

  const [
    hoverPosition,
    setHoverPosition,
  ] = useState<number | null>(
    null,
  );

  if (points.length === 0) {
    return (
      <div
        style={{
          padding: "16px",
          border: "1px solid currentColor",
          borderRadius: "8px",
          opacity: 0.75,
        }}
      >
        No percentile positions available to plot.
      </div>
    );
  }

  const xForPosition = (
    position: number,
  ) =>
    padding.left +
    (
      points.length <= 1
        ? plotWidth / 2
        : (
            position /
            (points.length - 1)
          ) * plotWidth
    );

  const yForPercentile = (
    value: number,
  ) =>
    padding.top +
    ((100 - value) / 100) *
      plotHeight;

  const segments = buildSegments(
    points,
    xForPosition,
    yForPercentile,
  );

  const yTicks = [
    100,
    75,
    50,
    25,
    0,
  ];

  const onPointerMove = (
    event: ReactPointerEvent<SVGSVGElement>,
  ) => {
    const bounds =
      event.currentTarget
        .getBoundingClientRect();

    if (
      bounds.width <= 0 ||
      points.length === 0
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
      points.length <= 1
        ? 0
        : Math.round(
            ratio *
              (
                points.length - 1
              ),
          );

    const boundedPosition =
      Math.max(
        0,
        Math.min(
          points.length - 1,
          position,
        ),
      );

    setHoverPosition(
      boundedPosition,
    );

    onInspectionHover?.(
      points[
        boundedPosition
      ].index,
    );
  };

  const positionByIndex = new Map(
    points.map(
      (point, position) => [
        point.index,
        position,
      ],
    ),
  );

  const linkedPosition =
    inspectionIndex === undefined ||
    inspectionIndex === null
      ? null
      : positionByIndex.get(
          inspectionIndex,
        ) ?? null;

  const activePosition =
    linkedPosition ??
    hoverPosition;

  const hovered =
    activePosition === null
      ? null
      : points[
          activePosition
        ];

  const hoverX =
    activePosition === null
      ? null
      : xForPosition(
          activePosition,
        );

  const handlePointerLeave = () => {
    setHoverPosition(null);
    onInspectionHover?.(null);
  };

  const handleClick = () => {
    if (
      hoverPosition === null
    ) {
      return;
    }

    onInspectionToggle?.(
      points[
        hoverPosition
      ].index,
    );
  };

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
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <strong>{title}</strong>

        <span
          style={{
            opacity: 0.75,
          }}
        >
          Fixed scale P0–P100
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
        {hovered ? (
          <>
            <strong>
              {inspectionLocked
                ? "Locked "
                : "Inspecting "}
              {hovered.label}
            </strong>

            <span>
              Position{" "}
              <strong>
                {formatPercentile(
                  hovered.percentile,
                )}
              </strong>
            </span>

            {hovered.observedValue !== undefined && (
              <span>
                Selected{" "}
                <strong>
                  {formatValue(
                    hovered.observedValue,
                  )}
                </strong>
              </span>
            )}

            {hovered.referenceMedian !== undefined && (
              <span>
                Median{" "}
                <strong>
                  {formatValue(
                    hovered.referenceMedian,
                  )}
                </strong>
              </span>
            )}

            {hovered.differenceFromMedian !== undefined && (
              <span>
                Difference{" "}
                <strong>
                  {formatValue(
                    hovered.differenceFromMedian,
                  )}
                </strong>
              </span>
            )}

            {hovered.referenceNumericCount !== undefined && (
              <span>
                Reference n{" "}
                <strong>
                  {hovered.referenceNumericCount?.toLocaleString() ??
                    "—"}
                </strong>
              </span>
            )}
          </>
        ) : (
          <span>
            Hover over the plot to inspect relative position.
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
        onPointerLeave={
          handlePointerLeave
        }
        onClick={handleClick}
        style={{
          width: "100%",
          height: "auto",
          display: "block",
          touchAction: "none",
        }}
        shapeRendering="geometricPrecision"
      >
        {yTicks.map(
          (tick) => {
            const y =
              yForPercentile(
                tick,
              );

            return (
              <g key={tick}>
                <line
                  x1={padding.left}
                  x2={
                    width -
                    padding.right
                  }
                  y1={y}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity={
                    tick === 50
                      ? 0.32
                      : 0.14
                  }
                  strokeWidth={
                    tick === 50
                      ? 1.5
                      : 1
                  }
                  strokeDasharray={
                    tick === 50
                      ? "6 5"
                      : undefined
                  }
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
                  P{tick}
                </text>
              </g>
            );
          },
        )}

        {segments.map(
          (segment, index) => (
            <polyline
              key={index}
              points={segment}
              fill="none"
              stroke="currentColor"
              strokeWidth={3}
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
            strokeOpacity={0.7}
            strokeWidth={
              inspectionLocked
                ? 2
                : 1.2
            }
            strokeDasharray={
              inspectionLocked
                ? undefined
                : "6 5"
            }
            vectorEffect="non-scaling-stroke"
          />
        )}

        {hovered &&
          activePosition !== null &&
          finiteNumber(
            hovered.percentile,
          ) && (
            <circle
              cx={hoverX ?? 0}
              cy={yForPercentile(
                hovered.percentile,
              )}
              r={5}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
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
          justifyContent: "space-between",
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

      <span
        style={{
          opacity: 0.75,
          fontSize: "0.92em",
        }}
      >
        Percentile position is a relative position in the dataset
        reference population, not a quality or error score.
      </span>
    </div>
  );
}
