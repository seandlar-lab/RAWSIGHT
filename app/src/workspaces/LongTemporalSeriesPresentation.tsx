import type { ReactNode } from "react";
import { TemporalSelection } from "../components/TemporalSelection";
import { LongTemporalSeriesChart } from "../components/LongTemporalSeriesChart";
import type {
  LongTemporalSeriesDetailResult,
  LongTemporalSeriesResult,
} from "../types/longTemporalSeries";

/** Presentation only: dataset loading and Tauri execution remain in App. */
export interface LongTemporalSeriesPresentationProps {
  sourcePath: string;
  series: LongTemporalSeriesResult | null;
  detail: LongTemporalSeriesDetailResult | null;
  detailLoading: boolean;
  onSelectInterval: (column: string, start: string, end: string) => void;
  /** Existing discovery panels are supplied by the analysis-owning parent. */
  children?: ReactNode;
}

export function LongTemporalSeriesPresentation({
  sourcePath,
  series,
  detail,
  detailLoading,
  onSelectInterval,
  children,
}: LongTemporalSeriesPresentationProps) {
  if (!series) return null;

  return (
    <div style={{ marginTop: "24px", display: "grid", gap: "16px" }}>
      <div className="analysis-group-content">
        <span>Value field <strong>{series.value_column_name}</strong></span>
        <span>
          Usable observations <strong>{series.source.usable_observation_count.toLocaleString()}</strong>
        </span>
        <span>Projection <strong>{series.display_projection.mode}</strong></span>
        <span>
          Display points <strong>{series.display_projection.point_count.toLocaleString()}</strong>
        </span>
      </div>

      {series.execution.limitations.length > 0 && (
        <div className="analysis-group-content">
          {series.execution.limitations.map((limitation) => (
            <span key={limitation}>{limitation}</span>
          ))}
        </div>
      )}

      <TemporalSelection
        key={`${sourcePath}:${series.value_column_name}`}
        result={series}
        selectedRange={detail?.requested_range ?? null}
        loading={detailLoading}
        onApply={(start, end) => onSelectInterval(series.value_column_name, start, end)}
      />

      <LongTemporalSeriesChart
        result={series}
        selectedRange={detail?.requested_range ?? null}
        onSelectBucket={(bucket) => onSelectInterval(
          series.value_column_name, bucket.bucket_start, bucket.bucket_end,
        )}
      />

      {detailLoading && (
        <div className="analysis-group-content">
          <span>Loading selected temporal interval...</span>
        </div>
      )}

      {detail && (
        <div style={{ display: "grid", gap: "12px" }}>
          <div className="analysis-group-content">
            <span>
              Selected interval <strong>{detail.requested_range.start}{" -> "}{detail.requested_range.end}</strong>
            </span>
            <span>
              Matching observations <strong>{detail.source.matching_observation_count.toLocaleString()}</strong>
            </span>
          </div>
          <LongTemporalSeriesChart
            result={detail}
            onSelectBucket={(bucket) => onSelectInterval(
              detail.value_column_name, bucket.bucket_start, bucket.bucket_end,
            )}
          />
          {children}
        </div>
      )}
    </div>
  );
}
