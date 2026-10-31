import type { AnalysisEvidenceItem } from "../types/analysisEvidence";
import type { EpisodeBoundary, EpisodeDiscoveryResult } from "../types/episodeDiscovery";

type Props = {
  result: EpisodeDiscoveryResult;
  evidence: AnalysisEvidenceItem[];
};

const border = "1px solid #d9dce1";

function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "Unknown";
  const rounded = Math.round(seconds);
  const days = Math.floor(rounded / 86400);
  const hours = Math.floor((rounded % 86400) / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const remainder = rounded % 60;
  return [days && `${days}d`, hours && `${hours}h`, minutes && `${minutes}m`,
    `${remainder}s`].filter(Boolean).join(" ");
}

function boundaryDescription(boundary: EpisodeBoundary): string {
  if (boundary.reason === "temporal_gap") {
    return `Observation gap · ${formatSeconds(boundary.gap_seconds)} between consecutive observations`;
  }
  if (boundary.reason === "concurrent_change") {
    return "Concurrent change between consecutive observations";
  }
  return "Unclassified segment boundary";
}

/** Presentation only. The source-derived segments must not be described as anomalies or motifs. */
export function EpisodeDiscoveryDetails({ result, evidence }: Props) {
  if (result.status !== "measured") return null;
  const evidenceById = new Map(evidence.map((item) => [item.id, item]));

  return (
    <section aria-label="Episode discovery details" style={{ marginTop: 12 }}>
      <div style={{ fontSize: 13, marginBottom: 10, opacity: 0.85 }}>
        {result.episode_count} observation segment(s), {result.boundaries.length} boundary/boundaries.
        These are candidate segments, not anomalies, motifs, or operating states.
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {result.episodes.map((segment, index) => {
          const item = evidenceById.get(`episode:${segment.id}`);
          const columns = item?.scope.columns ?? result.columns_considered;
          const boundary = segment.start_boundary;
          return (
            <article key={segment.id} style={{ border, borderRadius: 8, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                <strong>Segment {index + 1}</strong>
                <span style={{ fontSize: 12, opacity: 0.75 }}>
                  {segment.status === "too_short" ? "Too short for reliable evaluation" : "Candidate"}
                </span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8, marginTop: 10, fontSize: 13 }}>
                <div><div style={{ opacity: 0.7 }}>First observed</div><time>{segment.start_time}</time></div>
                <div><div style={{ opacity: 0.7 }}>Last observed</div><time>{segment.end_time}</time></div>
                <div><div style={{ opacity: 0.7 }}>Source observations</div><strong>{segment.observation_count.toLocaleString()}</strong></div>
              </div>
              {boundary ? (
                <div style={{ borderLeft: "3px solid #bd7e4d", paddingLeft: 9, marginTop: 12, fontSize: 13 }}>
                  <strong>Why this segment starts here</strong>
                  <div>{boundaryDescription(boundary)}</div>
                  {boundary.signals.length > 0 && <div>Contributing signals: {boundary.signals.join(", ")}</div>}
                </div>
              ) : (
                <div style={{ marginTop: 10, fontSize: 12, opacity: 0.72 }}>
                  First segment in the selected interval; no preceding boundary within this result.
                </div>
              )}
              {columns.length > 0 && (
                <details style={{ marginTop: 12, fontSize: 12 }}>
                  <summary style={{ cursor: "pointer" }}>Signal coverage ({columns.length})</summary>
                  <div style={{ marginTop: 6, display: "grid", gap: 4 }}>
                    {columns.map((name) => {
                      const coverage = segment.coverage[name];
                      const valid = segment.valid_counts[name];
                      return <div key={name}>
                        <strong>{name}</strong>: {Number.isFinite(coverage) ? `${(coverage * 100).toFixed(1)}%` : "Unavailable"}
                        {Number.isFinite(valid) ? ` (${valid}/${segment.observation_count} observations)` : ""}
                      </div>;
                    })}
                  </div>
                </details>
              )}
            </article>
          );
        })}
      </div>
      {result.limitations.length > 0 && (
        <details style={{ marginTop: 12, fontSize: 12 }}>
          <summary style={{ cursor: "pointer" }}>Method and limitations</summary>
          <p>Method: {result.method}</p>
          <ul>{result.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>
        </details>
      )}
    </section>
  );
}
