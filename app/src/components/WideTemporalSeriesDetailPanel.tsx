import type {
  WideTemporalSeriesDetail,
} from "../types/wideTemporalExplore";
import type {
  WideTemporalReferenceProfile,
} from "../types/wideTemporalReference";
import {
  WideTemporalSeriesChart,
} from "./WideTemporalSeriesChart";
import {
  WideTemporalReferenceChart,
} from "./WideTemporalReferenceChart";

type Props = {
  detail: WideTemporalSeriesDetail;
  reference: WideTemporalReferenceProfile | null;
  isReferenceLoading: boolean;
  onClose: () => void;
};

function formatScalar(
  value: string | number | boolean | null,
): string {
  if (value === null) {
    return "∅";
  }

  return String(value);
}

export function WideTemporalSeriesDetailPanel({
  detail,
  reference,
  isReferenceLoading,
  onClose,
}: Props) {
  const firstPoint =
    detail.temporal_points[0];

  const lastPoint =
    detail.temporal_points[
      detail.temporal_points.length - 1
    ];

  return (
    <div
      style={{
        display: "grid",
        gap: "16px",
        padding: "16px",
        border: "1px solid currentColor",
        borderRadius: "8px",
        opacity: 0.96,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "12px",
        }}
      >
        <div
          style={{
            display: "grid",
            gap: "4px",
          }}
        >
          <strong>
            Series {detail.series_index}
          </strong>
          <span>{detail.classification}</span>
        </div>

        <button
          type="button"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gap: "6px",
        }}
      >
        <strong>Descriptor fields</strong>

        {detail.descriptors.map(
          (descriptor) => (
            <span
              key={descriptor.column_index}
            >
              <strong>
                {descriptor.column_name}
              </strong>
              {" = "}
              {formatScalar(
                descriptor.value,
              )}
            </span>
          ),
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <span>
          Time points{" "}
          <strong>
            {detail.temporal_points.length.toLocaleString()}
          </strong>
        </span>

        {firstPoint && lastPoint && (
          <span>
            Observed range{" "}
            <strong>
              {firstPoint.label}
            </strong>
            {" → "}
            <strong>
              {lastPoint.label}
            </strong>
          </span>
        )}

        <span>
          Negative transitions{" "}
          <strong>
            {detail.negative_transition_count.toLocaleString()}
          </strong>
        </span>

        <span>
          Largest negative change{" "}
          <strong>
            {detail.largest_negative_change ??
              "—"}
          </strong>
        </span>
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "16px",
          padding: "10px 12px",
          border: "1px solid currentColor",
          borderRadius: "6px",
          opacity: 0.9,
        }}
      >
        <strong>Dataset reference profile</strong>

        {reference ? (
          <>
            <span>
              Population{" "}
              <strong>
                {reference.population_count.toLocaleString()}
              </strong>
            </span>

            <span>
              Time positions{" "}
              <strong>
                {reference.temporal_position_count.toLocaleString()}
              </strong>
            </span>

            <span>
              Statistics{" "}
              <strong>
                {reference.statistics_mode}
              </strong>
            </span>
          </>
        ) : (
          <span>
            {isReferenceLoading
              ? "Building reference population..."
              : "Reference population not available."}
          </span>
        )}
      </div>

      {reference && (
        <WideTemporalReferenceChart
          detail={detail}
          reference={reference}
        />
      )}

      <WideTemporalSeriesChart
        detail={detail}
      />

      <div
        style={{
          display: "grid",
          gap: "8px",
        }}
      >
        <strong>
          Observed negative transitions
        </strong>

        {detail.negative_transitions
          .length === 0 ? (
          <span>
            No negative adjacent transitions
            observed.
          </span>
        ) : (
          detail.negative_transitions.map(
            (transition) => (
              <div
                key={`${transition.from_index}-${transition.to_index}`}
                style={{
                  display: "grid",
                  gap: "2px",
                }}
              >
                <strong>
                  {transition.from_label}
                  {" → "}
                  {transition.to_label}
                </strong>

                <span>
                  {transition.previous_value}
                  {" → "}
                  {transition.current_value}
                  {" · change "}
                  {transition.change}
                </span>
              </div>
            ),
          )
        )}
      </div>
    </div>
  );
}
