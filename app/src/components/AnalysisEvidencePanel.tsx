import type { AnalysisEvidenceItem } from "../types/analysisEvidence";

type Props = {
  items: AnalysisEvidenceItem[];
  range?: { start: string; end: string } | null;
};

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "Unknown duration";
  const whole = Math.round(seconds);
  const days = Math.floor(whole / 86400);
  const hours = Math.floor((whole % 86400) / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const rem = whole % 60;
  return [days && `${days}d`, hours && `${hours}h`, minutes && `${minutes}m`, `${rem}s`]
    .filter(Boolean).join(" ");
}

/** A shared evidence surface. Method-specific visualizations can be added later. */
export function AnalysisEvidencePanel({ items, range }: Props) {
  if (items.length === 0) return null;
  const start = range ? Date.parse(range.start) : Number.NaN;
  const end = range ? Date.parse(range.end) : Number.NaN;
  const hasScale = Number.isFinite(start) && Number.isFinite(end) && end > start;
  const intervals = items.flatMap((item) => (item.intervals ?? []).map((interval) => ({
    id: item.id,
    interval,
  })));
  const segments = hasScale ? intervals.flatMap(({ id, interval }) => {
    const from = Date.parse(interval.start);
    const to = Date.parse(interval.end);
    if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) return [];
    const clippedStart = Math.max(start, from);
    const clippedEnd = Math.min(end, to);
    if (clippedEnd <= clippedStart) return [];
    return [{ id, start: ((clippedStart - start) / (end - start)) * 100,
      width: ((clippedEnd - clippedStart) / (end - start)) * 100 }];
  }) : [];
  const hasBounded = items.some((item) => item.provenance.bounded);
  const continuityOnly = items.every((item) => item.kind === "temporal_interval" && item.method === "temporal_continuity");

  return (
    <section aria-label="Analysis evidence" style={{ border: "1px solid #a5a5a5", borderRadius: 8, padding: 12, marginTop: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>{continuityOnly ? "Continuity evidence" : "Analysis evidence"}</div>
      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
        {hasBounded
          ? (continuityOnly
              ? "Retained observed intervals overlapping this selection (bounded sample, not a complete gap inventory)."
              : "Bounded source-derived evidence: the displayed results are not necessarily exhaustive.")
          : "Source-derived analytical evidence in the selected interval."}
      </div>
      {hasScale && segments.length > 0 && (
        <div aria-label="Position of observed intervals in selected time range"
          style={{ position: "relative", height: 18, borderRadius: 4, background: "#b1b1b130", overflow: "hidden", marginBottom: 10 }}>
          {segments.map((segment, index) => (
            <div key={`${segment.id}:${index}`} style={{ position: "absolute", left: `${segment.start}%`,
              width: `${segment.width}%`, height: "100%", background: "#bf7745" }} />
          ))}
        </div>
      )}
      <ul style={{ margin: 0, paddingLeft: 22, fontSize: 13 }}>
        {items.map((item) => (
          <li key={item.id} style={{ marginBottom: 5 }}>
            {(item.intervals ?? []).map((interval, index) => (
              <span key={`${item.id}:${index}`}>
                <strong>{formatDuration(interval.durationSeconds)}</strong>{" — "}
                <time>{interval.start}</time>{" → "}<time>{interval.end}</time>
                {typeof interval.relativeToDominantInterval === "number" &&
                  Number.isFinite(interval.relativeToDominantInterval) && (
                    <span>{` (${interval.relativeToDominantInterval.toFixed(1)}× dominant interval)`}</span>
                  )}
              </span>
            ))}
            <div style={{ fontSize: 11, opacity: 0.74 }}>
              {`Method: ${item.method} · Status: ${item.status}`}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
