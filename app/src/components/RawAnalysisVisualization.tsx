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

function formatShare(value: number) {
    if (value === 0) {
        return "0.0%";
    }

    if (value < 0.01) {
        return "<0.01%";
    }

    if (value < 0.1) {
        return `${value.toFixed(2)}%`;
    }

    return `${value.toFixed(1)}%`;
}

function formatTemporalValue(
    value: string | null,
) {
    if (!value) {
        return "—";
    }

    if (value.endsWith("T00:00:00")) {
        return value.slice(0, 10);
    }

    return value.replace("T", " ");
}

function formatDurationSeconds(
    value: number | null,
) {
    if (value === null) {
        return "—";
    }

    if (value % 86400 === 0) {
        const days = value / 86400;

        return `${days.toLocaleString()} ${days === 1 ? "day" : "days"
            }`;
    }

    if (value % 3600 === 0) {
        const hours = value / 3600;

        return `${hours.toLocaleString()} ${hours === 1 ? "hour" : "hours"
            }`;
    }

    if (value % 60 === 0) {
        const minutes = value / 60;

        return `${minutes.toLocaleString()} ${minutes === 1 ? "minute" : "minutes"
            }`;
    }

    return `${value.toLocaleString()} s`;
}

export function RawAnalysisVisualization({
    result,
}: RawAnalysisVisualizationProps) {
    if (
        result.routing !== "temporal" &&
        !result.distribution
    ) {
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
                    Share: item.percent_of_non_null,
                }),
            ),
        };

        const option = toEChartsOption(
            spec,
            data,
        );

        const dominantValue =
            distribution.dominant_value;
        const shownValueCount =
            distribution.top_values.length;

        const hasMoreValues =
            distribution.distinct_count >
            shownValueCount;

        return (
            <div>
                <div
                    style={{
                        display: "flex",
                        gap: "28px",
                        flexWrap: "wrap",
                        marginBottom: "20px",
                    }}
                >
                    <div>
                        <div>
                            <strong>Dominant value</strong>
                        </div>
                        <div>
                            {dominantValue
                                ? dominantValue.value
                                : "—"}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Share</strong>
                        </div>
                        <div>
                            {dominantValue
                                ? formatShare(
                                    dominantValue.percent_of_non_null,
                                )
                                : "—"}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Distinct values</strong>
                        </div>
                        <div>
                            {distribution.distinct_count.toLocaleString()}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Missing</strong>
                        </div>
                        <div>
                            {distribution.null_count.toLocaleString()}
                        </div>
                    </div>
                </div>

                {hasMoreValues && (
                    <p
                        style={{
                            marginTop: "0",
                            marginBottom: "16px",
                        }}
                    >
                        Showing the {shownValueCount} most frequent values
                        out of {distribution.distinct_count.toLocaleString()} distinct values.
                    </p>
                )}

                <RawsightChart
                    option={option}
                    height={420}
                />
            </div>
        );
    }

    if (
        result.routing === "temporal" &&
        result.temporal
    ) {
        const {
            axis,
            cadence,
            gaps,
        } = result.temporal;

        return (
            <div>
                <div
                    style={{
                        display: "flex",
                        gap: "28px",
                        flexWrap: "wrap",
                        marginBottom: "20px",
                    }}
                >
                    <div>
                        <div>
                            <strong>First observation</strong>
                        </div>
                        <div>
                            {formatTemporalValue(
                                axis.first_observation,
                            )}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Last observation</strong>
                        </div>
                        <div>
                            {formatTemporalValue(
                                axis.last_observation,
                            )}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Valid time values</strong>
                        </div>
                        <div>
                            {axis.valid_count.toLocaleString()}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Invalid time values</strong>
                        </div>
                        <div>
                            {axis.invalid_count.toLocaleString()}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Distinct time points</strong>
                        </div>
                        <div>
                            {axis.distinct_time_points.toLocaleString()}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Median cadence</strong>
                        </div>
                        <div>
                            {formatDurationSeconds(
                                cadence.median_interval_seconds,
                            )}
                        </div>
                    </div>

                    <div>
                        <div>
                            <strong>Detected gaps</strong>
                        </div>
                        <div>
                            {gaps.gap_count.toLocaleString()}
                        </div>
                    </div>
                </div>
                {gaps.gaps.length > 0 && (
                    <div
                        style={{
                            marginTop: "24px",
                        }}
                    >
                        <strong>Largest gaps</strong>

                        <ol>
                            {gaps.gaps
                                .slice(0, 5)
                                .map((gap) => (
                                    <li
                                        key={`${gap.from}-${gap.to}`}
                                    >
                                        {formatTemporalValue(gap.from)}
                                        {" → "}
                                        {formatTemporalValue(gap.to)}
                                        {" — "}
                                        {formatDurationSeconds(
                                            gap.interval_seconds,
                                        )}
                                        {" ("}
                                        {gap.multiple_of_median.toFixed(1)}
                                        {"× median cadence)"}
                                    </li>
                                ))}
                        </ol>
                    </div>
                )}
            </div>
        );
    }

    return null;
}
