import { useState } from "react";

import { RawsightChart } from "./RawsightChart";
import { toEChartsOption } from "../visualization/toEChartsOption";
import { VisualizationSelectionPanel } from "./VisualizationSelectionPanel";

import type {
    VisualizationData,
    VisualizationInteraction,
    VisualizationSpec,
} from "../types/visualization";


export function VisualizationDemo() {
    const [selectedSourceRow, setSelectedSourceRow] =
        useState<VisualizationData["rows"][number] | null>(
            null,

        );

    const [selectedRowCount, setSelectedRowCount] =
        useState<number | null>(null);

    const spec: VisualizationSpec = {
        chartType: "histogram",
        title: "Temperature distribution",
        xColumn: "Temperature",
    };

    const data: VisualizationData = {
        rows: [],
        histogramBins: [
            {
                label: "40–45",
                lowerBound: 40,
                upperBound: 45,
                count: 18,
                interactionId: "bin-0",
            },
            {
                label: "45–50",
                lowerBound: 45,
                upperBound: 50,
                count: 31,
                interactionId: "bin-1",
            },
            {
                label: "50–55",
                lowerBound: 50,
                upperBound: 55,
                count: 22,
                interactionId: "bin-2",
            },
            {
                label: "55–60",
                lowerBound: 55,
                upperBound: 60,
                count: 9,
                interactionId: "bin-3",
            },
        ],
        interactions: {
            "bin-0": {
                kind: "row_set",
                sourceRowIndices: Array.from(
                    { length: 18 },
                    (_, index) => index,
                ),
            },

            "bin-1": {
                kind: "row_set",
                sourceRowIndices: Array.from(
                    { length: 31 },
                    (_, index) => index + 18,
                ),
            },

            "bin-2": {
                kind: "row_set",
                sourceRowIndices: Array.from(
                    { length: 22 },
                    (_, index) => index + 49,
                ),
            },

            "bin-3": {
                kind: "row_set",
                sourceRowIndices: Array.from(
                    { length: 9 },
                    (_, index) => index + 71,
                ),
            },
        },
    };

    const option = toEChartsOption(
        spec,
        data,
    );

    function handleInteraction(
        interaction: VisualizationInteraction,
    ) {
        if (interaction.kind === "row_set") {
            setSelectedRowCount(
                interaction.sourceRowIndices.length,
            );
            setSelectedSourceRow(null);
            return;
        }

        if (interaction.kind !== "row") {
            return;
        }

        setSelectedRowCount(null);

        const sourceRow =
            data.rows[interaction.sourceRowIndex];

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
                interactions={data.interactions}
                onInteraction={handleInteraction}
            />

            <VisualizationSelectionPanel
                selectedRowCount={selectedRowCount}
                selectedSourceRow={selectedSourceRow}
            />
        </div>
    );
}