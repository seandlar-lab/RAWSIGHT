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


function clampRatio(
  value: number,
): number {
  return Math.max(
    0,
    Math.min(
      1,
      value,
    ),
  );
}


function pointRatio(
  point: TimeSeriesPoint,
  position: number,
  pointCount: number,
): number {
  if (
    typeof point.xPosition === "number" &&
    Number.isFinite(point.xPosition)
  ) {
    return clampRatio(
      point.xPosition,
    );
  }

  if (pointCount <= 1) {
    return 0.5;
  }

  return (
    position
    / (pointCount - 1)
  );
}


function nearestPointPosition(
  points: TimeSeriesPoint[],
  requestedRatio: number,
  requireNumericValue: boolean,
): number | null {
  if (points.length === 0) {
    return null;
  }

  let bestPosition: number | null = null;
  let bestDistance =
    Number.POSITIVE_INFINITY;

  points.forEach(
    (point, position) => {
      if (
        requireNumericValue &&
        (
          point.value === null ||
          !Number.isFinite(
            point.value,
          )
        )
      ) {
        return;
      }

      const ratio = pointRatio(
        point,
        position,
        points.length,
      );

      const distance = Math.abs(
        ratio - requestedRatio,
      );

      if (
        distance < bestDistance
      ) {
        bestDistance = distance;
        bestPosition = position;
      }
    },
  );

  return bestPosition;
}


export function TimeSeriesChart({
  points,
  markers = [],
  title = "Time series",
  ariaLabel = "Time series chart",
  markerLegend,
  seriesStrokeWidth = 3.8,
  inspectionIndex,
  inspectionLocked = false,
  onInspectionHover,
  onInspectionToggle,
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
    width
    - padding.left
    - padding.right;

  const plotHeight =
    height
    - padding.top
    - padding.bottom;

  const values =
    numericValues(points);

  const [
    hoverPosition,
    setHoverPosition,
  ] = useState<number | null>(
    null,
  );

  if (values.length === 0) {
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
        No numeric values available to plot.
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
        Math.abs(
          observedMax,
        ) * 0.05,
        1,
      )
      : 0;

  const scaleMin =
    observedMin
    - scalePadding;

  const scaleMax =
    observedMax
    + scalePadding;

  const valueRange =
    scaleMax
    - scaleMin
    || 1;

  const pointCount =
    points.length;

  const xForPoint = (
    point: TimeSeriesPoint,
    position: number,
  ) =>
    padding.left
    + pointRatio(
      point,
      position,
      pointCount,
    )
    * plotWidth;

  const yForValue = (
    value: number,
  ) =>
    padding.top
    + (
      (
        scaleMax - value
      )
      / valueRange
    )
    * plotHeight;

  const segments: string[] = [];

  let currentSegment:
    string[] = [];

  function flushSegment() {
    if (
      currentSegment.length > 0
    ) {
      segments.push(
        currentSegment.join(" "),
      );

      currentSegment = [];
    }
  }

  points.forEach(
    (point, position) => {
      if (
        point.breakBefore
      ) {
        flushSegment();
      }

      if (
        point.value !== null &&
        Number.isFinite(
          point.value,
        )
      ) {
        currentSegment.push(
          `${xForPoint(
            point,
            position,
          )},${yForValue(
            point.value,
          )}`,
        );

        return;
      }

      flushSegment();
    },
  );

  flushSegment();

  const positionByIndex =
    new Map(
      points.map(
        (
          point,
          position,
        ) => [
            point.index,
            position,
          ],
      ),
    );

  const linkedPosition =
    inspectionIndex === undefined ||
      inspectionIndex === null
      ? null
      : (
        positionByIndex.get(
          inspectionIndex,
        )
        ?? null
      );

  const activePosition =
    linkedPosition
    ?? hoverPosition;

  const resolvedMarkers =
    markers
      .map((marker) => {
        const position =
          positionByIndex.get(
            marker.index,
          );

        if (
          position === undefined
        ) {
          return null;
        }

        const point =
          points[position];

        return {
          ...marker,
          position,
          x: xForPoint(
            point,
            position,
          ),
          y: yForValue(
            marker.value,
          ),
        };
      })
      .filter(
        (
          marker,
        ): marker is
          TimeSeriesMarker & {
            position: number;
            x: number;
            y: number;
          } =>
          marker !== null,
      );

  const firstLabel =
    points[0]?.axisLabel
    ?? points[0]?.label
    ?? "";

  const lastLabel =
    points[
      points.length - 1
    ]?.axisLabel
    ?? points[
      points.length - 1
    ]?.label
    ?? "";

  const yTicks =
    Array.from(
      {
        length: 5,
      },
      (_, index) => {
        const ratio =
          index / 4;

        const value =
          scaleMax
          - valueRange
          * ratio;

        return {
          value,
          y:
            padding.top
            + plotHeight
            * ratio,
        };
      },
    );

  const hoveredPoint =
    activePosition === null
      ? null
      : (
        points[
        activePosition
        ]
        ?? null
      );

  const hoveredX =
    activePosition === null ||
      !hoveredPoint
      ? null
      : xForPoint(
        hoveredPoint,
        activePosition,
      );

  const hoveredY =
    hoveredPoint?.value === null ||
      hoveredPoint?.value === undefined
      ? null
      : yForValue(
        hoveredPoint.value,
      );

  function handlePointerMove(
    event:
      ReactPointerEvent<
        SVGSVGElement
      >,
  ) {
    const bounds =
      event.currentTarget
        .getBoundingClientRect();

    if (
      bounds.width <= 0 ||
      pointCount === 0
    ) {
      return;
    }

    const viewBoxX =
      (
        (
          event.clientX
          - bounds.left
        )
        / bounds.width
      )
      * width;

    const clampedX =
      Math.max(
        padding.left,
        Math.min(
          width
          - padding.right,
          viewBoxX,
        ),
      );

    const requestedRatio =
      clampRatio(
        (
          clampedX
          - padding.left
        )
        / plotWidth,
      );

    /*
     * Linked inspection must preserve
     * displayed position even if a
     * linked point lacks a numeric value.
     *
     * Standalone inspection instead
     * chooses the nearest numeric point.
     */
    const localPosition =
      nearestPointPosition(
        points,
        requestedRatio,
        !onInspectionHover,
      );

    setHoverPosition(
      localPosition,
    );

    if (
      onInspectionHover &&
      localPosition !== null
    ) {
      onInspectionHover(
        points[
          localPosition
        ].index,
      );
    }
  }

  function handlePointerLeave() {
    setHoverPosition(
      null,
    );

    onInspectionHover?.(
      null,
    );
  }

  function handleClick() {
    if (
      hoverPosition === null ||
      !onInspectionToggle
    ) {
      return;
    }

    onInspectionToggle(
      points[
        hoverPosition
      ].index,
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
        <strong>
          {title}
        </strong>

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
            <strong>
              {inspectionLocked
                ? "Locked"
                : "Inspecting"}
            </strong>

            <span>
              {hoveredPoint.label}
            </span>

            <span>
              Value{" "}
              <strong>
                {hoveredPoint.value
                  === null
                  ? "—"
                  : hoveredPoint.value
                    .toLocaleString()}
              </strong>
            </span>

            <span>
              Position{" "}
              <strong>
                {
                  hoveredPoint.index
                }
              </strong>
            </span>
          </>
        ) : (
          <span
            style={{
              opacity: 0.7,
            }}
          >
            Hover over the plot to inspect
            the nearest displayed point.
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
          viewBox={
            `0 0 ${width} ${height}`
          }
          role="img"
          aria-label={
            ariaLabel
          }
          onPointerMove={
            handlePointerMove
          }
          onPointerLeave={
            handlePointerLeave
          }
          onClick={
            handleClick
          }
          shapeRendering={
            "geometricPrecision"
          }
          style={{
            width: "100%",
            height: "auto",
            minHeight: "280px",
            overflow: "visible",
            cursor: "crosshair",
          }}
        >
          <line
            x1={
              padding.left
            }
            y1={
              padding.top
            }
            x2={
              padding.left
            }
            y2={
              height
              - padding.bottom
            }
            stroke={
              "CanvasText"
            }
            opacity="0.85"
            strokeWidth="2"
            vectorEffect={
              "non-scaling-stroke"
            }
          />

          <line
            x1={
              padding.left
            }
            y1={
              height
              - padding.bottom
            }
            x2={
              width
              - padding.right
            }
            y2={
              height
              - padding.bottom
            }
            stroke={
              "CanvasText"
            }
            opacity="0.85"
            strokeWidth="2"
            vectorEffect={
              "non-scaling-stroke"
            }
          />

          {segments.map(
            (
              segment,
              index,
            ) => (
              <polyline
                key={
                  index
                }
                points={
                  segment
                }
                fill="none"
                stroke={
                  "CanvasText"
                }
                strokeWidth={
                  seriesStrokeWidth
                }
                strokeLinejoin={
                  "round"
                }
                strokeLinecap={
                  "round"
                }
                vectorEffect={
                  "non-scaling-stroke"
                }
              />
            ),
          )}

          {resolvedMarkers.map(
            (marker) => (
              <circle
                key={
                  `${marker.index}-` +
                  `${marker.label ?? ""}`
                }
                cx={
                  marker.x
                }
                cy={
                  marker.y
                }
                r="6"
                fill="Canvas"
                stroke={
                  "CanvasText"
                }
                strokeWidth="3"
                vectorEffect={
                  "non-scaling-stroke"
                }
              >
                {(marker.title ||
                  marker.label) && (
                    <title>
                      {
                        marker.title
                        ?? marker.label
                      }
                    </title>
                  )}
              </circle>
            ),
          )}

          {hoveredX !== null &&
            hoveredPoint && (
              <>
                <line
                  x1={
                    hoveredX
                  }
                  y1={
                    padding.top
                  }
                  x2={
                    hoveredX
                  }
                  y2={
                    height
                    - padding.bottom
                  }
                  stroke={
                    "CanvasText"
                  }
                  opacity="0.85"
                  strokeWidth="2.4"
                  strokeDasharray={
                    inspectionLocked
                      ? undefined
                      : "7 5"
                  }
                  vectorEffect={
                    "non-scaling-stroke"
                  }
                />

                {hoveredY !== null && (
                  <>
                    <circle
                      cx={
                        hoveredX
                      }
                      cy={
                        hoveredY
                      }
                      r="10"
                      fill="none"
                      stroke={
                        "CanvasText"
                      }
                      strokeWidth="2"
                      opacity="0.65"
                      vectorEffect={
                        "non-scaling-stroke"
                      }
                    />

                    <circle
                      cx={
                        hoveredX
                      }
                      cy={
                        hoveredY
                      }
                      r="5.5"
                      fill={
                        "CanvasText"
                      }
                      stroke="Canvas"
                      strokeWidth="2.5"
                      vectorEffect={
                        "non-scaling-stroke"
                      }
                    />
                  </>
                )}
              </>
            )}

          {yTicks.map(
            (
              tick,
              index,
            ) => (
              <g
                key={
                  `y-tick-${index}`
                }
              >
                <line
                  x1={
                    padding.left
                  }
                  y1={
                    tick.y
                  }
                  x2={
                    width
                    - padding.right
                  }
                  y2={
                    tick.y
                  }
                  stroke={
                    "CanvasText"
                  }
                  opacity={
                    index === 0 ||
                      index ===
                      yTicks.length - 1
                      ? 0.22
                      : 0.14
                  }
                  strokeWidth="1.2"
                  vectorEffect={
                    "non-scaling-stroke"
                  }
                />

                <line
                  x1={
                    padding.left - 7
                  }
                  y1={
                    tick.y
                  }
                  x2={
                    padding.left
                  }
                  y2={
                    tick.y
                  }
                  stroke={
                    "CanvasText"
                  }
                  opacity="0.85"
                  strokeWidth="2"
                  vectorEffect={
                    "non-scaling-stroke"
                  }
                />

                <text
                  x={
                    padding.left - 14
                  }
                  y={
                    tick.y + 7
                  }
                  textAnchor="end"
                  fontSize="22"
                  fontWeight="600"
                  fill={
                    "CanvasText"
                  }
                  opacity="0.95"
                >
                  {Number(
                    tick.value.toFixed(
                      Math.abs(
                        tick.value,
                      ) < 10 &&
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
        <span>
          {firstLabel}
        </span>

        <span>
          {lastLabel}
        </span>
      </div>

      {markerLegend &&
        resolvedMarkers.length > 0 && (
          <span>
            {markerLegend}
          </span>
        )}
    </div>
  );
}