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


export function VisualizationDemo() {
    const [selectedSourceRow, setSelectedSourceRow] =
        useState<VisualizationData["rows"][number] | null>(
            null,
        );

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

        console.log(
            "RAWSIGHT selected source row:",
            sourceRow,
        );

        setSelectedSourceRow(sourceRow);
    }
    return (
        <div>
            <RawsightChart
                option={option}
                height={420}
                onPointClick={handlePointClick}
            />

            {selectedSourceRow && (
                <div
                    style={{
                        marginTop: "12px",
                        fontSize: "14px",
                    }}
                >
                    <strong>Source row</strong>

                    {Object.entries(selectedSourceRow).map(
                        ([columnName, value]) => (
                            <div key={columnName}>
                                {columnName}: {String(value)}
                            </div>
                        ),
                    )}
                </div>
            )}
        </div>
    );
}