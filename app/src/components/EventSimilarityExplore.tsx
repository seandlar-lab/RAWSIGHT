import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type SignalEvidence = {
  column: string;
  pearson_r: number;
  shape_similarity: number;
  coverage: number;
  paired_bins: number;
  target_delta: number;
  candidate_delta: number;
  level_difference: number;
};
type Side = {
  status: string;
  shape_similarity: number | null;
  measured_signal_count: number;
  requested_signal_count: number;
  signals: SignalEvidence[];
  excluded_signals: { column: string; reason: string }[];
};
type Candidate = {
  candidate_id: string;
  status: string;
  full_context_similarity: number | null;
  sides: { before: Side; after: Side };
  temporal_comparability?: Record<"before" | "after", {
    warning: string | null;
    target_elapsed_seconds: number | null;
    candidate_elapsed_seconds: number | null;
  }>;
};
type Event = {
  id: string;
  gap_seconds: number;
  anchor: { before_time: string; after_time: string };
  context_observation_counts?: { before: number; after: number };
};
type Execution = {
  status: string;
  target_event_id?: string;
  events: Event[];
  comparison: null | {
    selected_columns: string[];
    candidates: Candidate[];
  };
  gap_scan_scope?: { start: string | null; end: string | null };
  limitations?: string[];
};

const score = (value: number | null | undefined) => value == null ? "Insufficient evidence" : value.toFixed(4);
const time = (value: string) => value.replace("T", " ");
const eventLabel = (item?: Event) => item ? `${time(item.anchor.before_time)} → ${time(item.anchor.after_time)}` : "Unknown event";

export function EventSimilarityExplore({path, temporalAxis, interval, expectedIntervalSeconds, numericColumns}: {
  path: string;
  temporalAxis: object;
  interval: {start: string; end: string};
  expectedIntervalSeconds: number | null | undefined;
  numericColumns: string[];
}) {
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [result, setResult] = useState<Execution | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);
  const [reference, setReference] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  useEffect(() => {
    requestId.current++;
    setResult(null); setSelectedCandidate(null); setReference(null); setError(null); setLoading(false);
    setSelectedColumns(numericColumns.slice(0, 5));
  }, [path, interval.start, interval.end, expectedIntervalSeconds, numericColumns.join("\u0000")]);

  async function run(target: string | null = reference) {
    if (!expectedIntervalSeconds || expectedIntervalSeconds <= 0 || selectedColumns.length === 0) return;
    const id = ++requestId.current;
    setLoading(true); setError(null);
    try {
      const response = await invoke<string>("explore_event_context_similarity", {
        path, temporalAxisJson: JSON.stringify(temporalAxis),
        startTime: interval.start, endTime: interval.end,
        expectedIntervalSeconds,
        selectedColumns, targetEventId: target,
      });
      const parsed = JSON.parse(response) as Execution;
      if (id !== requestId.current) return;
      setResult(parsed);
      setReference(parsed.target_event_id ?? null);
      setSelectedCandidate(null);
    } catch (e) {
      if (id === requestId.current) setError(String(e));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }
  const eventById = (id: string) => result?.events.find(e => e.id === id);
  const candidate = result?.comparison?.candidates.find(c => c.candidate_id === selectedCandidate);
  return <div className="analysis-group" aria-label="Event similarity discoveries">
    <div className="analysis-group-header"><strong>Event similarity · Discover → Investigate</strong><span>Original observations · source-backed</span></div>
    <div className="analysis-group-content">
      <span>Find and compare temporal gaps inside the selected interval. Side windows may extend outside the scan interval. Shape scores are not probabilities or causal explanations.</span>
      <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
        {numericColumns.map(col => <label key={col} style={{display:"inline-flex",gap:4,alignItems:"center"}}>
          <input type="checkbox" checked={selectedColumns.includes(col)} disabled={loading} onChange={e => {
            setResult(null); setReference(null); setSelectedCandidate(null);
            setSelectedColumns(previous => e.target.checked ? [...previous,col] : previous.filter(x => x !== col));
          }}/>{col}
        </label>)}
      </div>
      <button type="button" disabled={loading || selectedColumns.length === 0 || !expectedIntervalSeconds || expectedIntervalSeconds <= 0} onClick={() => void run(null)}>{loading ? "Analyzing…" : "Discover similar event contexts"}</button>
      {error && <span role="alert">Analysis stopped: {error}. Narrow the selected interval if the event limit was exceeded.</span>}
      {result && <>
        <span role="status">{result.events.length} verified gaps in the selected interval · {result.comparison?.candidates.length ?? 0} comparison candidates · reference {eventLabel(eventById(result.target_event_id ?? ""))}</span>
        {result.status === "insufficient_events" && <span>At least two gaps are needed in the selected interval.</span>}
        {!candidate && (result.comparison?.candidates ?? []).map(item => <button key={item.candidate_id} type="button" style={{display:"block",width:"100%",textAlign:"left",padding:10,marginTop:8}} onClick={()=>setSelectedCandidate(item.candidate_id)}>
          <strong>{eventLabel(eventById(item.candidate_id))}</strong><br/>
          Before: {score(item.sides.before.shape_similarity)} · After: {score(item.sides.after.shape_similarity)} · Combined: {score(item.full_context_similarity)} · Investigate →
        </button>)}
        {candidate && <div style={{display:"grid",gap:12}}>
          <button type="button" onClick={()=>setSelectedCandidate(null)}>← Back to discoveries</button>
          <strong>Investigate: {eventLabel(eventById(candidate.candidate_id))}</strong>
          {(["before","after"] as const).map(sideName => {
            const side = candidate.sides[sideName];
            const duration = candidate.temporal_comparability?.[sideName];
            return <section key={sideName} style={{border:"1px solid var(--border-color, #8885)",padding:12,borderRadius:8}}>
              <strong>{sideName === "before" ? "Before" : "After"}: {score(side.shape_similarity)}</strong>
              <p>{side.measured_signal_count}/{side.requested_signal_count} comparable series · Alignment by observation index</p>
              {duration && <p>Elapsed seconds: reference {duration.target_elapsed_seconds ?? "n/a"}, candidate {duration.candidate_elapsed_seconds ?? "n/a"}{duration.warning ? ` · ${duration.warning}` : ""}</p>}
              {side.signals.length > 0 && <table><thead><tr><th>Series</th><th>Shape</th><th>Paired bins</th><th>Reference Δ</th><th>Candidate Δ</th></tr></thead><tbody>
                {side.signals.map(s => <tr key={s.column}><td>{s.column}</td><td>{score(s.shape_similarity)}</td><td>{s.paired_bins}</td><td>{s.target_delta.toFixed(3)}</td><td>{s.candidate_delta.toFixed(3)}</td></tr>)}
              </tbody></table>}
              {side.excluded_signals.map(s => <div key={s.column}>{s.column}: excluded ({s.reason})</div>)}
            </section>;
          })}
          <button type="button" disabled={loading} onClick={()=>void run(candidate.candidate_id)}>Use as reference · rerun analysis</button>
        </div>}
        <small>Scores compare curve shape only. Equal observation counts do not guarantee equal elapsed time. No sampling, interpolation, significance or causal interpretation.</small>
      </>}
    </div>
  </div>;
}
