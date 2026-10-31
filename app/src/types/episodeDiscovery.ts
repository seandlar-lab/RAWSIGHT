/** Backend result contract for the existing Python episode_discovery v0.1. */
export type EpisodeBoundary = {
  index: number;
  reason: "temporal_gap" | "concurrent_change";
  gap_seconds: number;
  signals: string[];
};

export type EpisodeCandidate = {
  id: string;
  start_index: number;
  end_index: number;
  start_time: string;
  end_time: string;
  observation_count: number;
  status: "candidate" | "too_short";
  valid_counts: Record<string, number>;
  coverage: Record<string, number>;
  start_boundary: EpisodeBoundary | null;
};

export type EpisodeDiscoveryResult = {
  analysis_kind: "automatic_episode_discovery";
  status: "measured" | "insufficient_data" | "resource_limit";
  method: string;
  columns_considered: string[];
  observation_count: number;
  episode_count: number;
  boundaries: EpisodeBoundary[];
  episodes: EpisodeCandidate[];
  limitations: string[];
};
