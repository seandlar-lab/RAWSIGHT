import type { LongTemporalContinuityEvidence } from "../types/longTemporalSeries";
import type { AnalysisEvidenceItem } from "../types/analysisEvidence";

type Range = { start: string; end: string } | null | undefined;

/**
 * Converts an already measured backend fact to a generic UI evidence item.
 * Does not infer unreturned gaps, impute values or assign anomaly status.
 */
export function continuityToAnalysisEvidence(
  evidence: LongTemporalContinuityEvidence | null | undefined,
  range?: Range,
): AnalysisEvidenceItem[] {
  if (!evidence?.intervals?.length) return [];
  const items = evidence.intervals
    .filter((item) =>
      Number.isFinite(item.interval_seconds) && item.interval_seconds > 0 &&
      Number.isFinite(Date.parse(item.from_value)) &&
      Number.isFinite(Date.parse(item.to_value)) &&
      Date.parse(item.to_value) > Date.parse(item.from_value))
    .map((interval, index): AnalysisEvidenceItem => ({
      id: `continuity:${interval.from_index}:${interval.to_index}:${index}`,
      kind: "temporal_interval",
      method: "temporal_continuity",
      status: "measured",
      title: "Observed interval without intermediate rows",
      summary: "No source observations occur strictly between these two recorded timestamps.",
      scope: {
        ...(range ? { start: range.start, end: range.end } : {}),
        columns: [],
      },
      provenance: {
        source: evidence.source || "long_temporal_detail",
        bounded: evidence.bounded,
        limitations: evidence.bounded
          ? ["Retained largest intervals only; not a complete inventory of all gaps."]
          : [],
      },
      intervals: [{
        start: interval.from_value,
        end: interval.to_value,
        durationSeconds: interval.interval_seconds,
        relativeToDominantInterval: interval.multiple_of_dominant_interval,
      }],
    }));
  return items;
}
