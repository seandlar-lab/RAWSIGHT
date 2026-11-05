/** Pure presentational evidence components for Explore visualization.
 * No data access, analysis execution, navigation or local dataset state.
 */
export interface TemporalContinuityView {
  temporal_column_name: string | null;
  continuity?: {
    observed_order: string | null;
    dominant_positive_interval_seconds: number | null;
    positive_interval_consistency: number | null;
    distinct_positive_interval_count: number | null;
    interval_frequency_complete: boolean;
    largest_positive_intervals: Array<{
      from_index: number;
      to_index: number;
      from_value: string;
      to_value: string;
      interval_seconds: number;
    }>;
  } | null;
  execution?: {
    observed_order_basis: string | null;
    canonical_order_established: boolean | null;
  } | null;
}

export function ExploreStructureSummary({
  strategy,
  orientation,
  horizontalCandidateCount,
  verticalCandidateCount,
}: {
  strategy: string;
  orientation: string;
  horizontalCandidateCount: number;
  verticalCandidateCount: number;
}) {
  return (
<div className="analysis-group">
                              <div className="analysis-group-header">
                                <strong>Detected structure</strong>
                                <span>{strategy}</span>
                              </div>

                              <div className="analysis-group-content">
                                <span>
                                  Temporal orientation{" "}
                                  <strong>{orientation}</strong>
                                </span>

                                <span>
                                  Horizontal candidates{" "}
                                  <strong>
                                    {horizontalCandidateCount.toLocaleString()}
                                  </strong>
                                </span>

                                <span>
                                  Vertical candidates{" "}
                                  <strong>
                                    {verticalCandidateCount.toLocaleString()}
                                  </strong>
                                </span>
                              </div>
                            </div>
  );
}

export function TemporalContinuitySummary({ longTemporal }: { longTemporal: TemporalContinuityView }) {
  // Only render evidence when a continuity assessment is actually available.
  const continuity = longTemporal.continuity;
  if (!continuity) return null;
  return (
                                <div className="analysis-group">
                                  <div className="analysis-group-header">
                                    <strong>Temporal continuity</strong>
                                    <span>Observed sequence</span>
                                  </div>

                                  <div className="analysis-group-content">
                                    <span>
                                      Time field{" "}
                                      <strong>
                                        {longTemporal.temporal_column_name ??
                                          "Unknown"}
                                      </strong>
                                    </span>

                                    <span>
                                      Observed order{" "}
                                      <strong>
                                        {continuity.observed_order ??
                                          "Not established"}
                                      </strong>
                                    </span>

                                    <span>
                                      Dominant positive interval{" "}
                                      <strong>
                                        {continuity
                                          .dominant_positive_interval_seconds !== null
                                          ? `${continuity
                                            .dominant_positive_interval_seconds.toLocaleString()} s`
                                          : "Not established"}
                                      </strong>
                                    </span>

                                    <span>
                                      Share at dominant interval{" "}
                                      <strong>
                                        {continuity
                                          .positive_interval_consistency !== null
                                          ? `${(
                                            continuity
                                              .positive_interval_consistency * 100
                                          ).toFixed(1)}%`
                                          : "Not evaluated"}
                                      </strong>
                                    </span>

                                    <span>
                                      Distinct positive intervals{" "}
                                      <strong>
                                        {continuity
                                          .distinct_positive_interval_count !== null
                                          ? continuity
                                            .distinct_positive_interval_count.toLocaleString()
                                          : "Not fully retained"}
                                      </strong>
                                    </span>

                                    <span>
                                      Interval frequency analysis{" "}
                                      <strong>
                                        {continuity
                                          .interval_frequency_complete
                                          ? "Complete"
                                          : "Bounded"}
                                      </strong>
                                    </span>

                                    {longTemporal.execution && (
                                      <>
                                        <span>
                                          Observed order basis{" "}
                                          <strong>
                                            {longTemporal.execution
                                              .observed_order_basis ?? "Unknown"}
                                          </strong>
                                        </span>

                                        <span>
                                          Canonical order established{" "}
                                          <strong>
                                            {longTemporal.execution
                                              .canonical_order_established === true
                                              ? "Yes"
                                              : longTemporal.execution
                                                .canonical_order_established === false
                                                ? "No"
                                                : "Not evaluated"}
                                          </strong>
                                        </span>
                                      </>
                                    )}

                                    {continuity
                                      .largest_positive_intervals.length > 0 && (
                                        <>
                                          <span>
                                            <strong>
                                              Largest observed positive intervals
                                            </strong>
                                          </span>

                                          {continuity
                                            .largest_positive_intervals.map(
                                              (interval) => (
                                                <span
                                                  key={`${interval.from_index}-${interval.to_index}`}
                                                >
                                                  <strong>
                                                    {interval.interval_seconds >= 3600
                                                      ? `${(
                                                        interval.interval_seconds / 3600
                                                      ).toFixed(1)} h`
                                                      : `${interval.interval_seconds.toLocaleString()} s`}
                                                  </strong>{" "}
                                                  {interval.from_value} → {interval.to_value}
                                                </span>
                                              ),
                                            )}
                                        </>
                                      )}
                                  </div>
                                </div>
  );
}
