import type { EChartsOption } from "echarts";
import { rawsightChartTheme } from "./rawsightChartTheme";

import type {
    VisualizationData,
    VisualizationSpec,
} from "../types/visualization";

export function toEChartsOption(
    spec: VisualizationSpec,
    data: VisualizationData,
): EChartsOption {
    if (
        spec.chartType !== "scatter" &&
        spec.chartType !== "line" &&
        spec.chartType !== "histogram" &&
        spec.chartType !== "bar"
    ) {
        throw new Error(
            `Unsupported visualization type: ${spec.chartType}`,
        );
    }

    if (spec.chartType === "histogram") {
        if (!spec.xColumn) {
            throw new Error(
                "Histogram visualization requires xColumn.",
            );
        }


        const xColumn = spec.xColumn;
        const bins = data.histogramBins ?? [];

        return {
            backgroundColor: rawsightChartTheme.background,

            title: {
                text: spec.title,
                left: 0,
                top: 0,
                textStyle: {
                    color: rawsightChartTheme.text,
                    fontSize: 16,
                    fontWeight: 600,
                },
            },

            tooltip: {
                trigger: "item",
                backgroundColor: "#ffffff",
                borderColor: rawsightChartTheme.axisLine,
                borderWidth: 1,
                textStyle: {
                    color: rawsightChartTheme.text,
                },
            },

            grid: {
                left: 64,
                right: 24,
                top: 58,
                bottom: 52,
                containLabel: true,
            },

            xAxis: {
                type: "category",
                name: xColumn,
                nameLocation: "middle",
                nameGap: 32,

                axisLine: {
                    lineStyle: {
                        color: rawsightChartTheme.axisLine,
                    },
                },

                axisTick: {
                    show: false,
                },

                axisLabel: {
                    color: rawsightChartTheme.mutedText,
                },

                splitLine: {
                    show: false,
                },

                nameTextStyle: {
                    color: rawsightChartTheme.mutedText,
                },
            },

            yAxis: {
                type: "value",
                name: "Count",
                nameLocation: "middle",
                nameGap: 42,

                axisLine: {
                    show: false,
                },

                axisTick: {
                    show: false,
                },

                axisLabel: {
                    color: rawsightChartTheme.mutedText,
                },

                splitLine: {
                    lineStyle: {
                        color: rawsightChartTheme.gridLine,
                    },
                },

                nameTextStyle: {
                    color: rawsightChartTheme.mutedText,
                },
            },

            series: [
                {
                    type: "bar",
                    name: "Count",

                    data: bins.map((bin) => [
                        bin.label,
                        bin.count,
                        bin.interactionId ?? "",
                    ]),

                    encode: {
                        x: 0,
                        y: 1,
                        tooltip: [1],
                    },

                    barCategoryGap: "2%",

                    itemStyle: {
                        color: rawsightChartTheme.primary,
                        opacity: 0.85,
                    },

                    emphasis: {
                        itemStyle: {
                            color: rawsightChartTheme.emphasis,
                        },
                    },
                },
            ],
        };
    }
    if (!spec.xColumn || !spec.yColumn) {
        throw new Error(
            `${spec.chartType} visualization requires both xColumn and yColumn.`,
        );
    }
    const xColumn = spec.xColumn;
    const yColumn = spec.yColumn;

    const commonOption: EChartsOption = {
        backgroundColor: rawsightChartTheme.background,

        title: {
            text: spec.title,
            left: 0,
            top: 0,
            textStyle: {
                color: rawsightChartTheme.text,
                fontSize: 16,
                fontWeight: 600,
            },
        },

        tooltip: {
            trigger: "item",
            backgroundColor: "#ffffff",
            borderColor: rawsightChartTheme.axisLine,
            borderWidth: 1,
            textStyle: {
                color: rawsightChartTheme.text,
            },
        },

        grid: {
            left: 64,
            right: 24,
            top: 58,
            bottom: 52,
            containLabel: true,
        },

        yAxis: {
            type: "value",
            name: yColumn,
            nameLocation: "middle",
            nameGap: 42,

            axisLine: {
                show: false,
            },

            axisTick: {
                show: false,
            },

            axisLabel: {
                color: rawsightChartTheme.mutedText,
            },

            splitLine: {
                lineStyle: {
                    color: rawsightChartTheme.gridLine,
                },
            },

            nameTextStyle: {
                color: rawsightChartTheme.mutedText,
            },
        },
    };
    if (spec.chartType === "bar") {
        const bars = data.rows.flatMap((row) => {
            const x = row[xColumn];
            const y = row[yColumn];
            const share = row["Share"];

            if (
                (typeof x !== "string" &&
                    typeof x !== "number") ||
                typeof y !== "number"
            ) {
                return [];
            }

            return [[
                String(x),
                y,
                "",
                typeof share === "number"
                    ? share
                    : null,
            ]];
        });

        const useHorizontalLayout =
            bars.length >= 7;

        const countAxis = {
            type: "value" as const,
            name: yColumn,
            nameLocation: "middle" as const,
            nameGap: 42,
            minInterval: 1,

            axisLine: {
                show: false,
            },

            axisTick: {
                show: false,
            },

            axisLabel: {
                color: rawsightChartTheme.mutedText,
            },

            splitLine: {
                lineStyle: {
                    color: rawsightChartTheme.gridLine,
                },
            },

            nameTextStyle: {
                color: rawsightChartTheme.mutedText,
            },
        };
        return {
            ...commonOption,

            tooltip: {
                ...commonOption.tooltip,
                trigger: "item",
                renderMode: "richText",

                formatter: (params) => {
                    const item = Array.isArray(params)
                        ? params[0]
                        : params;

                    const values =
                        item && Array.isArray(item.value)
                            ? item.value
                            : [];

                    const category =
                        String(values[0] ?? "");

                    const count = values[1];
                    const share = values[3];

                    const countText =
                        typeof count === "number"
                            ? count.toLocaleString()
                            : String(count ?? "—");

                    const shareText =
                        typeof share === "number"
                            ? share === 0
                                ? "0.0%"
                                : share < 0.01
                                    ? "<0.01%"
                                    : share < 0.1
                                        ? `${share.toFixed(2)}%`
                                        : `${share.toFixed(1)}%`
                            : "—";

                    return (
                        `${category}\n` +
                        `Count: ${countText}\n` +
                        `Share: ${shareText}`
                    );
                },
            },


            xAxis: useHorizontalLayout
                ? countAxis
                : {
                    type: "category",
                    name: xColumn,
                    inverse: true,
                    nameLocation: "middle",
                    nameGap: 36,

                    axisLine: {
                        lineStyle: {
                            color: rawsightChartTheme.axisLine,
                        },
                    },

                    axisTick: {
                        show: false,
                    },

                    axisLabel: {
                        color: rawsightChartTheme.mutedText,
                        interval: 0,
                    },

                    splitLine: {
                        show: false,
                    },

                    nameTextStyle: {
                        color: rawsightChartTheme.mutedText,
                    },
                },

            yAxis: useHorizontalLayout
                ? {
                    type: "category",
                    name: xColumn,
                    nameLocation: "middle",
                    nameGap: 72,

                    axisLine: {
                        lineStyle: {
                            color: rawsightChartTheme.axisLine,
                        },
                    },

                    axisTick: {
                        show: false,
                    },

                    axisLabel: {
                        color: rawsightChartTheme.mutedText,
                        interval: 0,
                    },

                    splitLine: {
                        show: false,
                    },

                    nameTextStyle: {
                        color: rawsightChartTheme.mutedText,
                    },
                }
                : countAxis,

            series: [
                {
                    type: "bar",
                    name: yColumn,
                    data: bars,

                    encode: useHorizontalLayout
                        ? {
                            x: 1,
                            y: 0,
                            tooltip: [1],
                        }
                        : {
                            x: 0,
                            y: 1,
                            tooltip: [1],
                        },

                    barMaxWidth: 56,

                    itemStyle: {
                        color: rawsightChartTheme.primary,
                        opacity: 0.85,
                    },

                    emphasis: {
                        itemStyle: {
                            color: rawsightChartTheme.emphasis,
                        },
                    },
                },
            ],
        };
    }

    if (spec.chartType === "scatter") {
        const points = data.rows.flatMap((row, sourceRowIndex) => {
            const x = row[xColumn];
            const y = row[yColumn];

            if (
                typeof x !== "number" ||
                typeof y !== "number"
            ) {
                return [];
            }

            return [[x, y, sourceRowIndex]];
        });

        return {
            ...commonOption,

            xAxis: {
                type: "value",
                name: xColumn,
                nameLocation: "middle",
                nameGap: 32,

                axisLine: {
                    lineStyle: {
                        color: rawsightChartTheme.axisLine,
                    },
                },

                axisTick: {
                    show: false,
                },

                axisLabel: {
                    color: rawsightChartTheme.mutedText,
                },

                splitLine: {
                    lineStyle: {
                        color: rawsightChartTheme.gridLine,
                    },
                },

                nameTextStyle: {
                    color: rawsightChartTheme.mutedText,
                },
            },

            series: [
                {
                    type: "scatter",
                    data: points,
                    encode: {
                        x: 0,
                        y: 1,
                        tooltip: [0, 1],
                    },
                    symbolSize: 10,

                    itemStyle: {
                        color: rawsightChartTheme.primary,
                        opacity: 0.85,
                    },

                    emphasis: {
                        scale: 1.2,
                        itemStyle: {
                            color: rawsightChartTheme.emphasis,
                        },
                    },
                },
            ],
        };
    }

    const lineRows = data.rows.flatMap((row, sourceRowIndex) => {
        const x = row[xColumn];
        const y = row[yColumn];

        if (
            (typeof x !== "string" &&
                typeof x !== "number") ||
            typeof y !== "number"
        ) {
            return [];
        }

        return [
            {
                x: String(x),
                y,
                sourceRowIndex,
            },
        ];
    });

    return {
        ...commonOption,

        tooltip: {
            ...commonOption.tooltip,
            trigger: "axis",
        },

        xAxis: {
            type: "time",
            name: xColumn,
            nameLocation: "middle",
            nameGap: 32,



            axisLine: {
                lineStyle: {
                    color: rawsightChartTheme.axisLine,
                },
            },

            axisTick: {
                show: false,
            },

            axisLabel: {
                color: rawsightChartTheme.mutedText,
            },

            splitLine: {
                show: false,
            },

            nameTextStyle: {
                color: rawsightChartTheme.mutedText,
            },
        },

        series: [
            {
                type: "line",
                data: lineRows.map((row) => [
                    row.x,
                    row.y,
                    row.sourceRowIndex,
                ]),

                encode: {
                    x: 0,
                    y: 1,
                    tooltip: [1],
                },
                name: yColumn,

                showSymbol: true,
                symbolSize: 7,
                smooth: false,

                lineStyle: {
                    color: rawsightChartTheme.primary,
                    width: 2,
                },

                itemStyle: {
                    color: rawsightChartTheme.primary,
                },

                emphasis: {
                    scale: 1.2,
                    itemStyle: {
                        color: rawsightChartTheme.emphasis,
                    },
                },
            },
        ],
    };
}