/** Cross-method presentation contract: evidence is not a causal interpretation. */
export type AnalysisEvidenceStatus = "measured" | "candidate" | "unavailable";
export type AnalysisEvidenceKind =
  | "temporal_interval"
  | "numeric_outlier"
  | "multivariate_observation"
  | "sequence_pattern"
  | "variable_relation";

export type AnalysisEvidenceInterval = {
  start: string;
  end: string;
  durationSeconds: number;
  relativeToDominantInterval?: number | null;
};

export type AnalysisEvidenceItem = {
  id: string;
  kind: AnalysisEvidenceKind;
  method: string;
  status: AnalysisEvidenceStatus;
  title: string;
  summary: string;
  scope: {
    start?: string;
    end?: string;
    columns: string[];
  };
  provenance: {
    source: string;
    bounded: boolean;
    limitations: string[];
  };
  intervals?: AnalysisEvidenceInterval[];
};
