import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

type RawsightChartProps = {
    option: EChartsOption;
    height?: number;

    onPointClick?: (
        data: unknown,
        dataIndex: number,
    ) => void;
};

export function RawsightChart({
    option,
    height = 360,
    onPointClick,
}: RawsightChartProps) {
    const containerRef =
        useRef<HTMLDivElement | null>(null);

    const chartRef =
        useRef<echarts.ECharts | null>(null);

    const onPointClickRef =
        useRef(onPointClick);

    useEffect(() => {
        onPointClickRef.current = onPointClick;
    }, [onPointClick]);

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
            onPointClickRef.current?.(
                params.data,
                params.dataIndex,
            );
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