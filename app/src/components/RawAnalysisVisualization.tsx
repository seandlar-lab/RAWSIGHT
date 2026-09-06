import { RawsightChart } from "./RawsightChart";
import { toEChartsOption } from "../visualization/toEChartsOption";

import type {
    CategoricalDistribution,
    NumericDistribution,
    RawAnalysisColumnResult,
} from "../types/rawAnalysis";

import type {
    VisualizationData,
    VisualizationSpec,
} from "../types/visualization";

type RawAnalysisVisualizationProps = {
    result: RawAnalysisColumnResult;
};

function formatBinBound(value: number) {
    return new Intl.NumberFormat(undefined, {
        maximumFractionDigits: 4,
    }).format(value);
}

export function RawAnalysisVisualization({
    result,
}: RawAnalysisVisualizationProps) {
    if (!result.distribution) {
        return null;
    }

    if (result.routing === "numeric") {
        const distribution =
            result.distribution as NumericDistribution;

        const spec: VisualizationSpec = {
            chartType: "histogram",
            title: `${result.column} distribution`,
            xColumn: result.column,
        };

        const data: VisualizationData = {
            rows: [],
            histogramBins:
                distribution.histogram_bins.map(
                    (bin) => ({
                        label:
                            `${formatBinBound(bin.lower_bound)}` +
                            `–${formatBinBound(bin.upper_bound)}`,
                        lowerBound: bin.lower_bound,
                        upperBound: bin.upper_bound,
                        count: bin.count,
                    }),
                ),
        };

        const option = toEChartsOption(
            spec,
            data,
        );

        return (
            <RawsightChart
                option={option}
                height={420}
            />
        );
    }

    if (result.routing === "categorical") {
        const distribution =
            result.distribution as CategoricalDistribution;

        const spec: VisualizationSpec = {
            chartType: "bar",
            title: `${result.column} distribution`,
            xColumn: result.column,
            yColumn: "Count",
        };

        const data: VisualizationData = {
            rows: distribution.top_values.map(
                (item) => ({
                    [result.column]: item.value,
                    Count: item.count,
                }),
            ),
        };

        const option = toEChartsOption(
            spec,
            data,
        );

        return (
            <RawsightChart
                option={option}
                height={420}
            />
        );
    }

    return null;
}