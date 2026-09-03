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
    if (spec.chartType !== "scatter") {
        throw new Error(
            `Unsupported visualization type: ${spec.chartType}`,
        );
    }

    if (!spec.xColumn || !spec.yColumn) {
        throw new Error(
            "Scatter visualization requires both xColumn and yColumn.",
        );
    }

    const xColumn = spec.xColumn;
    const yColumn = spec.yColumn;

    const points = data.rows.flatMap((row) => {
        const x = row[xColumn];
        const y = row[yColumn];

        if (
            typeof x !== "number" ||
            typeof y !== "number"
        ) {
            return [];
        }

        return [[x, y]];
    });

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

        series: [
            {
                type: "scatter",
                data: points,
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