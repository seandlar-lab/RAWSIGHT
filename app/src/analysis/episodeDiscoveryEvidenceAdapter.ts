import type { AnalysisEvidenceItem } from "../types/analysisEvidence";
import type { EpisodeDiscoveryResult, EpisodeCandidate } from "../types/episodeDiscovery";

/** Maps verified backend segment candidates into UI evidence. Does not run detection.
 *  Time gaps are intentionally omitted: the existing continuity adapter owns them.
 *  A segment is not an anomaly or a motif, so it has no `intervals` overlay.
 */
export function episodeDiscoveryToAnalysisEvidence(
  result: EpisodeDiscoveryResult | null | undefined,
): AnalysisEvidenceItem[] {
  if (!result || result.analysis_kind !== "automatic_episode_discovery") return [];
  if (result.status !== "measured") return [];
  const byId = new Set<string>();
  const items: AnalysisEvidenceItem[] = [];
  for (const segment of result.episodes) {
    if (!isValidSegment(segment) || byId.has(segment.id)) continue;
    byId.add(segment.id);
    const columns = result.columns_considered.filter((name) =>
      Number.isFinite(segment.coverage[name]) && segment.coverage[name] > 0);
    const boundary = segment.start_boundary;
    const isTransition = boundary?.reason === "concurrent_change";
    const coverage = columns.map((name) =>
      `${name}: ${(segment.coverage[name] * 100).toFixed(0)}%`).join(", ");
    items.push({
      id: `episode:${segment.id}`,
      kind: "temporal_segment",
      method: result.method,
      status: "candidate",
      title: "Candidate observation segment",
      summary: `${segment.observation_count} observations between ${segment.start_time} and ${segment.end_time}.` +
        (isTransition ? ` Boundary signals: ${boundary.signals.join(", ") || "none"}.` : "") +
        (coverage ? ` Coverage: ${coverage}.` : ""),
      scope: { start: segment.start_time, end: segment.end_time, columns },
      provenance: {
        source: "episode_discovery_v0_1",
        bounded: true,
        limitations: [
          ...result.limitations,
          "Candidate segmentation, not a detected anomaly, motif, or operating state.",
          "No timeline overlay: segment intervals must not be confused with missing observations.",
        ],
      },
    });
  }
  return items;
}

function isValidSegment(value: EpisodeCandidate): boolean {
  return Boolean(value && typeof value.id === "string" && value.id.length > 0 &&
    typeof value.start_time === "string" && typeof value.end_time === "string" &&
    Number.isFinite(Date.parse(value.start_time)) &&
    Number.isFinite(Date.parse(value.end_time)) &&
    Date.parse(value.start_time) <= Date.parse(value.end_time) &&
    Number.isInteger(value.observation_count) && value.observation_count > 0 &&
    (value.status === "candidate" || value.status === "too_short") &&
    value.coverage && typeof value.coverage === "object");
}
