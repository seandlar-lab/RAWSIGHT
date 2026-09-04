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
        spec.chartType !== "line"
    ) {
        throw new Error(
            `Unsupported visualization type: ${spec.chartType}`,
        );
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