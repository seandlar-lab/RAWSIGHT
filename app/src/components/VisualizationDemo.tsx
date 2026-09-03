import { useState } from "react";

import { RawsightChart } from "./RawsightChart";
import { toEChartsOption } from "../visualization/toEChartsOption";

import type {
    VisualizationData,
    VisualizationSpec,
} from "../types/visualization";

type SelectedPoint = {
    current: number;
    temperature: number;
};

export function VisualizationDemo() {
    const [selectedPoint, setSelectedPoint] =
        useState<SelectedPoint | null>(null);

    const spec: VisualizationSpec = {
        chartType: "scatter",
        title: "Current vs Temperature",
        xColumn: "Current",
        yColumn: "Temperature",
    };

    const data: VisualizationData = {
        rows: [
            { Current: 10.2, Temperature: 42.1 },
            { Current: 11.4, Temperature: 43.8 },
            { Current: 12.1, Temperature: 45.2 },
            { Current: 13.7, Temperature: 47.4 },
            { Current: 14.2, Temperature: 48.1 },
            { Current: 15.8, Temperature: 52.3 },
            { Current: 17.1, Temperature: 55.0 },
        ],
    };

    const option = toEChartsOption(
        spec,
        data,
    );

    function handlePointClick(
        clickedData: unknown,
        dataIndex: number,
    ) {
        if (
            !Array.isArray(clickedData) ||
            clickedData.length < 2 ||
            typeof clickedData[0] !== "number" ||
            typeof clickedData[1] !== "number"
        ) {
            return;
        }
        const sourceRow = data.rows[dataIndex];

        console.log(
            "RAWSIGHT selected source row:",
            sourceRow,
        );

        setSelectedPoint({
            current: clickedData[0],
            temperature: clickedData[1],
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
                        Current: {selectedPoint.current}
                    </div>

                    <div>
                        Temperature: {selectedPoint.temperature}
                    </div>
                </div>
            )}
        </div>
    );
}