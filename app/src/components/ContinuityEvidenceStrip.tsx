import type { LongTemporalContinuityEvidence } from "../types/longTemporalSeries";

type Props = {
  evidence?: LongTemporalContinuityEvidence | null;
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
    .filter(Boolean)
    .join(" ");
}

/**
 * Shows retained, source-derived continuity evidence. It does NOT infer all
 * gaps in the interval, nor label an interval as missing measurements.
 */
export function ContinuityEvidenceStrip({ evidence, range }: Props) {
  if (!evidence || !evidence.intervals.length) return null;

  const start = range ? Date.parse(range.start) : Number.NaN;
  const end = range ? Date.parse(range.end) : Number.NaN;
  const hasScale = Number.isFinite(start) && Number.isFinite(end) && end > start;

  const intervals = evidence.intervals.map((interval, index) => {
    const fromMs = Date.parse(interval.from_value);
    const toMs = Date.parse(interval.to_value);
    const valid = hasScale && Number.isFinite(fromMs) && Number.isFinite(toMs) && toMs > fromMs;
    const left = valid ? Math.max(0, Math.min(100, ((fromMs - start) / (end - start)) * 100)) : 0;
    const right = valid ? Math.max(0, Math.min(100, ((toMs - start) / (end - start)) * 100)) : 0;
    return { interval, index, valid, left, width: Math.max(0, right - left) };
  });

  return (
    <section aria-label="Temporal continuity evidence" style={{ border: "1px solid #a5a5a5", borderRadius: 8, padding: 12, marginTop: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>Continuity evidence</div>
      <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 8 }}>
        Retained largest observed intervals overlapping this selection (bounded sample, not a complete gap inventory).
      </div>
      {hasScale && (
        <div aria-label="Position of retained intervals in selected time range" style={{ position: "relative", height: 18, borderRadius: 4, background: "#b1b1b130", overflow: "hidden", marginBottom: 10 }}>
          {intervals.filter((item) => item.valid && item.width > 0).map(({ interval, index, left, width }) => (
            <div
              key={`${interval.from_value}-${interval.to_value}-${index}`}
              title={`${interval.from_value} → ${interval.to_value} (${formatDuration(interval.interval_seconds)})`}
              style={{ position: "absolute", left: `${left}%`, width: `${Math.max(width, 0.4)}%`, height: "100%", background: "#bf7745" }}
            />
          ))}
        </div>
      )}
      <ul style={{ margin: 0, paddingLeft: 22, fontSize: 13 }}>
        {intervals.map(({ interval, index }) => (
          <li key={`${interval.from_value}-${interval.to_value}-${index}`} style={{ marginBottom: 4 }}>
            <strong>{formatDuration(interval.interval_seconds)}</strong>{" — "}
            <time>{interval.from_value}</time>{" → "}<time>{interval.to_value}</time>
            {typeof interval.multiple_of_dominant_interval === "number" && Number.isFinite(interval.multiple_of_dominant_interval) && (
              <span>{` (${interval.multiple_of_dominant_interval.toFixed(1)}× dominant interval)`}</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
