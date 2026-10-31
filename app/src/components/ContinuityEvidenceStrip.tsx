import type { LongTemporalContinuityEvidence } from "../types/longTemporalSeries";
import { continuityToAnalysisEvidence } from "../analysis/continuityEvidenceAdapter";
import { AnalysisEvidencePanel } from "./AnalysisEvidencePanel";

type Props = {
  evidence?: LongTemporalContinuityEvidence | null;
  range?: { start: string; end: string } | null;
};

/** Backward-compatible adapter for the existing Explore detail chart. */
export function ContinuityEvidenceStrip({ evidence, range }: Props) {
  return <AnalysisEvidencePanel items={continuityToAnalysisEvidence(evidence, range)} range={range} />;
}
