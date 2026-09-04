import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import type { VisualizationInteraction } from "../types/visualization";

type RawsightChartProps = {
    option: EChartsOption;
    height?: number;

    onInteraction?: (
        interaction: VisualizationInteraction,
    ) => void;
};

export function RawsightChart({
    option,
    height = 360,
    onInteraction,
}: RawsightChartProps) {
    const containerRef =
        useRef<HTMLDivElement | null>(null);

    const chartRef =
        useRef<echarts.ECharts | null>(null);

    const onInteractionRef =
        useRef(onInteraction);

    useEffect(() => {
        onInteractionRef.current = onInteraction;
    }, [onInteraction]);

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

        const chart =
            echarts.init(containerRef.current);

        chartRef.current = chart;

        const handleClick = (
            params: echarts.ECElementEvent,
        ) => {
            const chartData = params.data;

            if (
                !Array.isArray(chartData) ||
                chartData.length < 3 ||
                typeof chartData[2] !== "number"
            ) {
                return;
            }

            onInteractionRef.current?.({
                kind: "row",
                sourceRowIndex: chartData[2],
            });
        };

        chart.on(
            "click",
            handleClick,
        );

        const resizeObserver =
            new ResizeObserver(() => {
                chart.resize();
            });

        resizeObserver.observe(
            containerRef.current,
        );

        return () => {
            resizeObserver.disconnect();

            chart.off(
                "click",
                handleClick,
            );

            chart.dispose();
            chartRef.current = null;
        };
    }, []);

    useEffect(() => {
        if (!chartRef.current) {
            return;
        }

        chartRef.current.setOption(
            option,
            {
                notMerge: true,
            },
        );
    }, [option]);

    return (
        <div
            ref={containerRef}
            style={{
                width: "100%",
                height,
            }}
        />
    );
}