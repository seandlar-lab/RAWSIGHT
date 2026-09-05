import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";
import type {
    VisualizationInteraction,
    VisualizationInteractionMap,
} from "../types/visualization";

type RawsightChartProps = {
    option: EChartsOption;
    height?: number;
    interactions?: VisualizationInteractionMap;

    onInteraction?: (
        interaction: VisualizationInteraction,
    ) => void;
};

export function RawsightChart({
    option,
    height = 360,
    interactions,
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

    const interactionsRef =
        useRef(interactions);

    useEffect(() => {
        interactionsRef.current = interactions;
    }, [interactions]);

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
                chartData.length < 3
            ) {
                return;
            }

            const sourceReference = chartData[2];

            if (typeof sourceReference === "string") {
                const interaction =
                    interactionsRef.current?.[sourceReference];

                if (interaction) {
                    onInteractionRef.current?.(interaction);
                }

                return;
            }

            if (
                typeof sourceReference === "number" &&
                Number.isInteger(sourceReference) &&
                sourceReference >= 0
            ) {
                onInteractionRef.current?.({
                    kind: "row",
                    sourceRowIndex: sourceReference,
                });

                return;
            }

            if (
                Array.isArray(sourceReference) &&
                sourceReference.every(
                    (value) =>
                        typeof value === "number" &&
                        Number.isInteger(value) &&
                        value >= 0,
                )
            ) {
                onInteractionRef.current?.({
                    kind: "row_set",
                    sourceRowIndices: sourceReference,
                });
            }
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