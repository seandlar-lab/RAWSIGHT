import { useEffect, useRef, useState, type PointerEvent } from "react";
import type { LongTemporalSeriesRequestedRange, LongTemporalSeriesResult } from "../types/longTemporalSeries";

type Props = {
  result: LongTemporalSeriesResult;
  selectedRange: LongTemporalSeriesRequestedRange | null;
  loading: boolean;
  onApply: (start: string, end: string) => void;
};

// Source timestamps are local wall-clock timestamps, not UTC instants.
// datetime-local is deliberately used without toISOString() / timezone conversion.
function inputTime(value: string): string {
  return value.replace(" ", "T").slice(0, 19);
}
function ms(value: string): number {
  return new Date(inputTime(value)).getTime();
}
function wallTime(value: number): string {
  const date = new Date(value);
  const two = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}T${two(date.getHours())}:${two(date.getMinutes())}:${two(date.getSeconds())}`;
}

export function TemporalSelection({ result, selectedRange, loading, onApply }: Props) {
  const minTime = inputTime(result.source.first_observation ?? "");
  const maxTime = inputTime(result.source.last_observation ?? "");
  const lower = ms(minTime);
  const upper = ms(maxTime);
  const validDomain = Number.isFinite(lower) && Number.isFinite(upper) && upper > lower;
  const [start, setStart] = useState(selectedRange?.start ? inputTime(selectedRange.start) : minTime);
  const [end, setEnd] = useState(selectedRange?.end ? inputTime(selectedRange.end) : maxTime);
  const anchorRef = useRef<number | null>(null);

  useEffect(() => {
    setStart(selectedRange?.start ? inputTime(selectedRange.start) : minTime);
    setEnd(selectedRange?.end ? inputTime(selectedRange.end) : maxTime);
  }, [selectedRange?.start, selectedRange?.end, minTime, maxTime]);

  const startMs = ms(start);
  const endMs = ms(end);
  const validSelection = validDomain && Number.isFinite(startMs) && Number.isFinite(endMs)
    && startMs >= lower && endMs <= upper && startMs < endMs;
  const plotLeft = 24;
  const plotRight = 752;
  const plotWidth = plotRight - plotLeft;
  const atX = (t: number) => plotLeft + Math.max(0, Math.min(1, (t - lower) / (upper - lower))) * plotWidth;
  const fromPointer = (event: PointerEvent<SVGSVGElement>) => {
    const r = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - r.left) * 776 / r.width;
    return lower + Math.max(0, Math.min(1, (x - plotLeft) / plotWidth)) * (upper - lower);
  };
  const points = result.display_projection.buckets ?? [];
  const values = points.map(p => p.mean).filter((v): v is number => typeof v === "number" && Number.isFinite(v));
  const minValue = values.length ? Math.min(...values) : 0;
  const maxValue = values.length ? Math.max(...values) : 1;
  const valueSpan = maxValue > minValue ? maxValue - minValue : 1;
  const linePoints = points.flatMap(p => {
    const time = ms(p.bucket_start);
    return validDomain && Number.isFinite(time) && typeof p.mean === "number" && Number.isFinite(p.mean)
      ? [`${atX(time)},${92 - ((p.mean - minValue) / valueSpan) * 64}`]
      : [];
  }).join(" ");

  if (!validDomain) return <p>Temporal selection unavailable: invalid source time range.</p>;

  return (
    <section aria-label="Temporal analysis selection" style={{ border: "1px solid #cad2d9", borderRadius: 8, padding: 14, display: "grid", gap: 10 }}>
      <strong>Analysis interval</strong>
      <span style={{ fontSize: 12, opacity: 0.75 }}>Drag across the overview to select an interval, or enter exact local timestamps below. The shaded range is the analysis selection.</span>
      <svg viewBox="0 0 776 118" aria-label="Drag to select a temporal interval" role="img"
        style={{ width: "100%", height: "auto", minHeight: 90, cursor: "crosshair", touchAction: "none", userSelect: "none", borderRadius: 4, background: "rgba(128,128,128,0.06)" }}
        onPointerDown={event => {
          if (event.button !== 0) return;
          const t = fromPointer(event);
          anchorRef.current = t;
          setStart(wallTime(t));
          setEnd(wallTime(Math.min(upper, t + 1000)));
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={event => {
          if (anchorRef.current === null) return;
          const t = fromPointer(event);
          setStart(wallTime(Math.min(anchorRef.current, t)));
          setEnd(wallTime(Math.max(anchorRef.current, t)));
        }}
        onPointerUp={event => {
          if (anchorRef.current === null) return;
          const t = fromPointer(event);
          const a = Math.min(anchorRef.current, t);
          const b = Math.max(anchorRef.current, t);
          if (b > a) { setStart(wallTime(a)); setEnd(wallTime(b)); }
          anchorRef.current = null;
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => { anchorRef.current = null; }}>
        <line x1="24" y1="94" x2="752" y2="94" stroke="currentColor" strokeOpacity={0.3}/>
        {linePoints && <polyline points={linePoints} fill="none" stroke="#347c9a" strokeWidth="1.6" pointerEvents="none" />}
        {Number.isFinite(startMs) && Number.isFinite(endMs) && (
          <rect x={atX(Math.min(startMs, endMs))} y="10" width={Math.max(1, Math.abs(atX(endMs) - atX(startMs)))} height="84" fill="#b9863d" fillOpacity="0.22" stroke="#b9863d" strokeWidth="1.5" pointerEvents="none"/>
        )}
        <text x="24" y="111" fill="currentColor" fontSize="11">{minTime.slice(0,10)}</text>
        <text x="752" y="111" textAnchor="end" fill="currentColor" fontSize="11">{maxTime.slice(0,10)}</text>
      </svg>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }}>
        <label style={{ display: "grid", gap: 4 }}>From
          <input type="datetime-local" step="1" value={start} min={minTime} max={maxTime} onChange={e => setStart(e.target.value)} />
        </label>
        <label style={{ display: "grid", gap: 4 }}>To (exclusive)
          <input type="datetime-local" step="1" value={end} min={minTime} max={maxTime} onChange={e => setEnd(e.target.value)} />
        </label>
        <button type="button" disabled={loading || !validSelection} onClick={() => onApply(start, end)}>
          {loading ? "Loading…" : "Apply interval"}
        </button>
        <button type="button" onClick={() => { setStart(minTime); setEnd(maxTime); }}>Full range</button>
      </div>
      {!validSelection && <span role="alert" style={{ color: "#a35d20" }}>Choose a valid interval within the observed time range, with start before end.</span>}
      <span style={{ fontSize: 12, opacity: 0.75 }}>This selection loads temporal detail and supplies the same interval to Event Similarity and Episode Discovery. The overview curve is display-only; the analyses read source observations.</span>
    </section>
  );
}
