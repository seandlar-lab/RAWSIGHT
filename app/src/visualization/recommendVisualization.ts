import type {
    VisualizationReason,
    VisualizationRecommendation,
    VisualizationType,
} from "../types/visualization";

const chartTypeByReason: Record<
    VisualizationReason,
    VisualizationType
> = {
    numeric_distribution: "histogram",
    numeric_outliers: "boxplot",
    numeric_relationship: "scatter",
    temporal_series: "line",
    categorical_distribution: "bar",
    categorical_relationship: "heatmap",
    functional_dependency: "dependency_graph",
};

export function recommendVisualization(
    reason: VisualizationReason,
    title: string,
    xColumn?: string,
    yColumn?: string,
    groupByColumn?: string,
): VisualizationRecommendation {
    return {
        reason,

        recommended: {
            chartType: chartTypeByReason[reason],
            title,
            xColumn,
            yColumn,
            groupByColumn,
        },

        confidence: 1.0,
    };
}