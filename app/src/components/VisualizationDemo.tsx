import { useState } from "react";

import {
    RawsightChart,
    type RawsightChartPointClick,
} from "./RawsightChart";
import { toEChartsOption } from "../visualization/toEChartsOption";

import type {
    VisualizationData,
    VisualizationSpec,
} from "../types/visualization";

type SelectedPoint = {
    timestamp: string;
    temperature: number;
};

export function VisualizationDemo() {
    const [selectedPoint, setSelectedPoint] =
        useState<SelectedPoint | null>(null);

    const spec: VisualizationSpec = {
        chartType: "line",
        title: "Temperature over time",
        xColumn: "Timestamp",
        yColumn: "Temperature",
    };

    const data: VisualizationData = {
        rows: [
            { Timestamp: "2026-09-03T08:00:00", Temperature: 42.1 },
            { Timestamp: "2026-09-03T08:15:00", Temperature: 42.8 },
            { Timestamp: "2026-09-03T09:00:00", Temperature: 43.2 },
            { Timestamp: "2026-09-03T10:30:00", Temperature: 44.7 },
            { Timestamp: "2026-09-03T12:00:00", Temperature: 46.1 },
            { Timestamp: "2026-09-03T12:20:00", Temperature: 49.3 },
            { Timestamp: "2026-09-03T14:00:00", Temperature: 52.7 },
        ],
    };

    const option = toEChartsOption(
        spec,
        data,
    );

    function handlePointClick(
        event: RawsightChartPointClick,
    ) {
        const sourceRow =
            data.rows[event.sourceRowIndex];

        if (!sourceRow) {
            return;
        }

        const timestamp = sourceRow.Timestamp;
        const temperature = sourceRow.Temperature;

        if (
            typeof timestamp !== "string" ||
            typeof temperature !== "number"
        ) {
            return;
        }

        console.log(
            "RAWSIGHT selected source row:",
            sourceRow,
        );

        setSelectedPoint({
            timestamp,
            temperature,
        });
    }
    return (
        <div>
            <RawsightChart
                option={option}
                height={420}
                onPointClick={handlePointClick}
            />

            {selectedPoint && (
                <div
                    style={{
                        marginTop: "12px",
                        fontSize: "14px",
                    }}
                >
                    <strong>Selected point</strong>

                    <div>
                        Timestamp: {selectedPoint.timestamp}
                    </div>

                    <div>
                        Temperature: {selectedPoint.temperature}
                    </div>
                </div>
            )}
        </div>
    );
}