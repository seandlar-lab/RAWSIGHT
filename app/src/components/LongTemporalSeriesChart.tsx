import {
    useState,
    type PointerEvent as ReactPointerEvent,
} from "react";

import type {
    LongTemporalSeriesBucket,
    LongTemporalSeriesResult,
} from "../types/longTemporalSeries";

import {
    TimeSeriesChart,
} from "../visualization";

import type {
    TimeSeriesPoint,
} from "../visualization";


type Props = {
    result: LongTemporalSeriesResult;
};


const MEAN_COLOR = "#17202a";
const MIN_COLOR = "#2563A6";
const MAX_COLOR = "#7048A0";


function finiteOrNull(
    value: number | null,
): number | null {
    return (
        typeof value === "number" &&
        Number.isFinite(value)
    )
        ? value
        : null;
}


function formatValue(
    value: number | null,
): string {
    return value === null
        ? "n/a"
        : value.toLocaleString();
}


function shortDate(
    value: string | null,
): string {
    if (!value) {
        return "";
    }

    return value.slice(0, 10);
}


function bucketMidpoint(
    bucket: LongTemporalSeriesBucket,
): number | null {
    const start =
        Date.parse(bucket.bucket_start);

    const end =
        Date.parse(bucket.bucket_end);

    if (
        !Number.isFinite(start) ||
        !Number.isFinite(end)
    ) {
        return null;
    }

    return start + (end - start) / 2;
}


export function LongTemporalSeriesChart({
    result,
}: Props) {
    const buckets =
        result.display_projection.buckets ?? [];

    if (buckets.length === 0) {
        const points: TimeSeriesPoint[] =
            result.display_projection.points.map(
                (point) => ({
                    index:
                        point.projection_index,
                    label:
                        point.time,
                    axisLabel:
                        point.time.slice(0, 10),
                    value:
                        finiteOrNull(point.value),
                    xPosition:
                        Number.isFinite(point.position)
                            ? Math.max(
                                0,
                                Math.min(
                                    1,
                                    point.position,
                                ),
                            )
                            : undefined,
                    breakBefore:
                        point.break_before,
                }),
            );

        return (
            <TimeSeriesChart
                points={points}
                title="Temporal series"
                ariaLabel={
                    `Temporal series for ` +
                    `${result.value_column_name}`
                }
                seriesStrokeWidth={1.5}
            />
        );
    }

    return (
        <BucketOverview
            result={result}
            buckets={buckets}
        />
    );
}


function BucketOverview({
    result,
    buckets,
}: {
    result: LongTemporalSeriesResult;
    buckets: LongTemporalSeriesBucket[];
}) {
    const width = 1440;
    const height = 520;

    const padding = {
        left: 92,
        right: 32,
        top: 34,
        bottom: 58,
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
        hoverIndex,
        setHoverIndex,
    ] = useState<number | null>(null);

    const usableBuckets =
        buckets
            .map((bucket) => ({
                bucket,
                midpoint:
                    bucketMidpoint(bucket),
                minimum:
                    finiteOrNull(
                        bucket.minimum,
                    ),
                mean:
                    finiteOrNull(
                        bucket.mean,
                    ),
                maximum:
                    finiteOrNull(
                        bucket.maximum,
                    ),
            }))
            .filter(
                (item) =>
                    item.midpoint !== null &&
                    (
                        item.minimum !== null ||
                        item.mean !== null ||
                        item.maximum !== null
                    ),
            );

    if (usableBuckets.length === 0) {
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
                No bucket statistics available
                to plot.
            </div>
        );
    }

    const allValues =
        usableBuckets.flatMap(
            (item) =>
                [
                    item.minimum,
                    item.mean,
                    item.maximum,
                ].filter(
                    (
                        value,
                    ): value is number =>
                        value !== null &&
                        Number.isFinite(value),
                ),
        );

    const observedMin =
        Math.min(...allValues);

    const observedMax =
        Math.max(...allValues);

    const scalePadding =
        observedMin === observedMax
            ? Math.max(
                Math.abs(
                    observedMax,
                ) * 0.05,
                1,
            )
            : 0;

    const scaleMin =
        observedMin -
        scalePadding;

    const scaleMax =
        observedMax +
        scalePadding;

    const valueRange =
        scaleMax -
        scaleMin ||
        1;

    const firstTime =
        usableBuckets[0]
            .midpoint as number;

    const lastTime =
        usableBuckets[
            usableBuckets.length - 1
        ].midpoint as number;

    const timeRange =
        lastTime -
        firstTime;

    function xForTime(
        value: number,
    ): number {
        if (timeRange <= 0) {
            return (
                padding.left +
                plotWidth / 2
            );
        }

        return (
            padding.left +
            (
                (
                    value - firstTime
                ) / timeRange
            ) *
            plotWidth
        );
    }

    function yForValue(
        value: number,
    ): number {
        return (
            padding.top +
            (
                (
                    scaleMax - value
                ) / valueRange
            ) *
            plotHeight
        );
    }

    function buildSegments(
        selector: (
            item:
                (typeof usableBuckets)[number],
        ) => number | null,
    ): string[] {
        const segments: string[] = [];

        let current: string[] = [];

        let previousBucketIndex:
            number | null = null;

        function flush() {
            if (current.length > 0) {
                segments.push(
                    current.join(" "),
                );

                current = [];
            }
        }

        usableBuckets.forEach(
            (item) => {
                const value =
                    selector(item);

                const bucketIndex =
                    item.bucket.bucket_index;

                if (
                    previousBucketIndex !== null &&
                    bucketIndex >
                    previousBucketIndex + 1
                ) {
                    flush();
                }

                if (value === null) {
                    flush();

                    previousBucketIndex =
                        bucketIndex;

                    return;
                }

                current.push(
                    `${xForTime(
                        item.midpoint as number,
                    )},${yForValue(value)}`,
                );

                previousBucketIndex =
                    bucketIndex;
            },
        );

        flush();

        return segments;
    }

    const minimumSegments =
        buildSegments(
            (item) =>
                item.minimum,
        );

    const meanSegments =
        buildSegments(
            (item) =>
                item.mean,
        );

    const maximumSegments =
        buildSegments(
            (item) =>
                item.maximum,
        );

    const yTicks =
        Array.from(
            {
                length: 5,
            },
            (_, index) => {
                const ratio =
                    index / 4;

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

    const hovered =
        hoverIndex === null
            ? null
            : usableBuckets[
            hoverIndex
            ] ?? null;

    const hoveredX =
        hovered
            ? xForTime(
                hovered.midpoint as number,
            )
            : null;

    function handlePointerMove(
        event:
            ReactPointerEvent<
                SVGSVGElement
            >,
    ) {
        const bounds =
            event.currentTarget
                .getBoundingClientRect();

        if (bounds.width <= 0) {
            return;
        }

        const viewBoxX =
            (
                (
                    event.clientX -
                    bounds.left
                ) /
                bounds.width
            ) *
            width;

        const boundedX =
            Math.max(
                padding.left,
                Math.min(
                    width -
                    padding.right,
                    viewBoxX,
                ),
            );

        let nearestIndex = 0;

        let nearestDistance =
            Number.POSITIVE_INFINITY;

        usableBuckets.forEach(
            (item, index) => {
                const x =
                    xForTime(
                        item.midpoint as number,
                    );

                const distance =
                    Math.abs(
                        x - boundedX,
                    );

                if (
                    distance <
                    nearestDistance
                ) {
                    nearestDistance =
                        distance;

                    nearestIndex =
                        index;
                }
            },
        );

        setHoverIndex(
            nearestIndex,
        );
    }

    const firstLabel =
        shortDate(
            result.source
                .first_observation,
        );

    const lastLabel =
        shortDate(
            result.source
                .last_observation,
        );

    return (
        <div
            style={{
                display: "grid",
                gap: "10px",
                width: "100%",
            }}
        >
            <div
                style={{
                    display: "flex",
                    justifyContent:
                        "space-between",
                    alignItems:
                        "baseline",
                    gap: "20px",
                    flexWrap: "wrap",
                }}
            >
                <strong>
                    Temporal overview
                </strong>

                <span>
                    Observed Min{" "}
                    {observedMin.toLocaleString()}
                    {" / "}
                    Observed Max{" "}
                    {observedMax.toLocaleString()}
                </span>
            </div>

            <div
                style={{
                    minHeight: "52px",
                    display: "flex",
                    alignItems: "center",
                    gap: "18px",
                    flexWrap: "wrap",
                    padding: "8px 10px",
                    border: hovered
                        ? "1px solid CanvasText"
                        : "1px solid transparent",
                    borderRadius: "6px",
                    background: hovered
                        ? "Canvas"
                        : "transparent",
                }}
            >
                {hovered ? (
                    <>
                        <strong>
                            Bucket{" "}
                            {
                                hovered.bucket
                                    .bucket_index
                            }
                        </strong>

                        <span>
                            {
                                shortDate(
                                    hovered.bucket
                                        .bucket_start,
                                )
                            }
                            {" -> "}
                            {
                                shortDate(
                                    hovered.bucket
                                        .bucket_end,
                                )
                            }
                        </span>

                        <span>
                            Count{" "}
                            <strong>
                                {
                                    hovered.bucket
                                        .count
                                        .toLocaleString()
                                }
                            </strong>
                        </span>

                        <span>
                            Min{" "}
                            <strong>
                                {
                                    formatValue(
                                        hovered.minimum,
                                    )
                                }
                            </strong>
                        </span>

                        <span>
                            Mean{" "}
                            <strong>
                                {
                                    formatValue(
                                        hovered.mean,
                                    )
                                }
                            </strong>
                        </span>

                        <span>
                            Max{" "}
                            <strong>
                                {
                                    formatValue(
                                        hovered.maximum,
                                    )
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
                        the nearest time bucket.
                    </span>
                )}
            </div>

            <svg
                viewBox={
                    `0 0 ${width} ${height}`
                }
                role="img"
                aria-label={
                    `Temporal min mean max ` +
                    `overview for ` +
                    `${result.value_column_name}`
                }
                onPointerMove={
                    handlePointerMove
                }
                onPointerLeave={
                    () =>
                        setHoverIndex(null)
                }
                shapeRendering={
                    "geometricPrecision"
                }
                style={{
                    width: "100%",
                    height: "auto",
                    minHeight: "360px",
                    overflow: "visible",
                    cursor: "crosshair",
                }}
            >
                <line
                    x1={padding.left}
                    y1={padding.top}
                    x2={padding.left}
                    y2={
                        height -
                        padding.bottom
                    }
                    stroke="CanvasText"
                    opacity="0.85"
                    strokeWidth="2"
                    vectorEffect={
                        "non-scaling-stroke"
                    }
                />

                <line
                    x1={padding.left}
                    y1={
                        height -
                        padding.bottom
                    }
                    x2={
                        width -
                        padding.right
                    }
                    y2={
                        height -
                        padding.bottom
                    }
                    stroke="CanvasText"
                    opacity="0.85"
                    strokeWidth="2"
                    vectorEffect={
                        "non-scaling-stroke"
                    }
                />

                {yTicks.map(
                    (tick, index) => (
                        <g
                            key={
                                `y-${index}`
                            }
                        >
                            <line
                                x1={padding.left}
                                y1={tick.y}
                                x2={
                                    width -
                                    padding.right
                                }
                                y2={tick.y}
                                stroke="CanvasText"
                                opacity="0.14"
                                strokeWidth="1"
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
                                fill="CanvasText"
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

                {minimumSegments.map(
                    (segment, index) => (
                        <polyline
                            key={
                                `min-${index}`
                            }
                            points={segment}
                            fill="none"
                            stroke={MIN_COLOR}
                            strokeWidth="2.2"
                            opacity="0.9"
                            strokeLinejoin="round"
                            strokeLinecap="round"
                            vectorEffect={
                                "non-scaling-stroke"
                            }
                        />
                    ),
                )}

                {maximumSegments.map(
                    (segment, index) => (
                        <polyline
                            key={
                                `max-${index}`
                            }
                            points={segment}
                            fill="none"
                            stroke={MAX_COLOR}
                            strokeWidth="2.2"
                            opacity="0.9"
                            strokeLinejoin="round"
                            strokeLinecap="round"
                            vectorEffect={
                                "non-scaling-stroke"
                            }
                        />
                    ),
                )}

                {meanSegments.map(
                    (segment, index) => (
                        <polyline
                            key={
                                `mean-${index}`
                            }
                            points={segment}
                            fill="none"
                            stroke={MEAN_COLOR}
                            strokeWidth="3.0"
                            strokeLinejoin="round"
                            strokeLinecap="round"
                            vectorEffect={
                                "non-scaling-stroke"
                            }
                        />
                    ),
                )}

                {hoveredX !== null && (
                    <line
                        x1={hoveredX}
                        y1={padding.top}
                        x2={hoveredX}
                        y2={
                            height -
                            padding.bottom
                        }
                        stroke="CanvasText"
                        opacity="0.55"
                        strokeWidth="1.3"
                        strokeDasharray="5 5"
                        vectorEffect={
                            "non-scaling-stroke"
                        }
                    />
                )}
            </svg>

            <div
                style={{
                    display: "flex",
                    justifyContent:
                        "space-between",
                    fontWeight: 600,
                }}
            >
                <span>
                    {firstLabel}
                </span>

                <span>
                    {lastLabel}
                </span>
            </div>

            <div
                style={{
                    display: "flex",
                    gap: "24px",
                    flexWrap: "wrap",
                    fontSize: "14px",
                    alignItems: "center",
                }}
            >
                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "7px",
                    }}
                >
                    <span
                        style={{
                            width: "40px",
                            borderTop:
                                `4px solid ${MEAN_COLOR}`,
                        }}
                    />
                    <strong>
                        Mean
                    </strong>
                </span>

                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "7px",
                    }}
                >
                    <span
                        style={{
                            width: "40px",
                            borderTop:
                                `4px solid ${MIN_COLOR}`,
                        }}
                    />
                    <strong>
                        Min
                    </strong>
                </span>

                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "7px",
                    }}
                >
                    <span
                        style={{
                            width: "40px",
                            borderTop:
                                `4px solid ${MAX_COLOR}`,
                        }}
                    />
                    <strong>
                        Max
                    </strong>
                </span>
            </div>
        </div>
    );
}
