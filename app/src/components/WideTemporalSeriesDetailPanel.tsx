import { useEffect, useState } from "react";

import type {
  WideTemporalSeriesDetail,
} from "../types/wideTemporalExplore";
import type {
  WideTemporalReferenceProfile,
} from "../types/wideTemporalReference";
import type {
  WideTemporalReferenceComparisonExecution,
} from "../types/wideTemporalReferenceComparison";
import {
  WideTemporalSeriesChart,
} from "./WideTemporalSeriesChart";
import {
  WideTemporalReferenceChart,
} from "./WideTemporalReferenceChart";
import {
  WideTemporalPercentilePositionChart,
} from "./WideTemporalPercentilePositionChart";

type Props = {
  detail: WideTemporalSeriesDetail;
  reference: WideTemporalReferenceProfile | null;
  isReferenceLoading: boolean;
  comparison: WideTemporalReferenceComparisonExecution | null;
  isComparisonLoading: boolean;
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
  comparison,
  isComparisonLoading,
  onClose,
}: Props) {
  const firstPoint =
    detail.temporal_points[0];

  const lastPoint =
    detail.temporal_points[
      detail.temporal_points.length - 1
    ];

  const [
    hoveredAxisIndex,
    setHoveredAxisIndex,
  ] = useState<number | null>(
    null,
  );

  const [
    lockedAxisIndex,
    setLockedAxisIndex,
  ] = useState<number | null>(
    null,
  );

  useEffect(() => {
    setHoveredAxisIndex(null);
    setLockedAxisIndex(null);
  }, [detail.series_index]);

  const inspectionAxisIndex =
    lockedAxisIndex ??
    hoveredAxisIndex;

  const inspectionLocked =
    lockedAxisIndex !== null;

  const inspectedComparison =
    inspectionAxisIndex === null
      ? null
      : comparison?.comparison.positions.find(
          (position) =>
            position.axis_index ===
            inspectionAxisIndex,
        ) ?? null;

  const inspectedReference =
    inspectionAxisIndex === null
      ? null
      : reference?.positions.find(
          (position) =>
            position.axis_index ===
            inspectionAxisIndex,
        ) ?? null;

  const inspectedDetail =
    inspectionAxisIndex === null
      ? null
      : detail.temporal_points.find(
          (point) =>
            point.axis_index ===
            inspectionAxisIndex,
        ) ?? null;

  const inspectionLabel =
    inspectedComparison?.label ??
    inspectedReference?.label ??
    inspectedDetail?.label ??
    null;

  const handleInspectionHover = (
    index: number | null,
  ) => {
    if (
      lockedAxisIndex !== null
    ) {
      return;
    }

    setHoveredAxisIndex(
      index,
    );
  };

  const handleInspectionToggle = (
    index: number,
  ) => {
    setLockedAxisIndex(
      (current) =>
        current === index
          ? null
          : index,
    );

    setHoveredAxisIndex(
      index,
    );
  };

  const clearInspection = () => {
    setHoveredAxisIndex(null);
    setLockedAxisIndex(null);
  };

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
          display: "grid",
          gap: "8px",
          padding: "12px",
          border: "1px solid currentColor",
          borderRadius: "6px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <strong>
            Linked point inspection
          </strong>

          {inspectionAxisIndex !== null && (
            <button
              type="button"
              onClick={clearInspection}
            >
              Clear
            </button>
          )}
        </div>

        {inspectionAxisIndex === null ? (
          <span
            style={{
              opacity: 0.75,
            }}
          >
            Hover any chart to inspect the same time position in all views.
            Click a point to lock it.
          </span>
        ) : (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "14px",
            }}
          >
            <span>
              {inspectionLocked
                ? "Locked"
                : "Inspecting"}{" "}
              <strong>
                {inspectionLabel ?? `Position ${inspectionAxisIndex}`}
              </strong>
            </span>

            <span>
              Selected{" "}
              <strong>
                {inspectedComparison?.selected_value ??
                  (
                    typeof inspectedDetail?.value === "number"
                      ? inspectedDetail.value
                      : "—"
                  )}
              </strong>
            </span>

            <span>
              Population median{" "}
              <strong>
                {inspectedComparison?.reference_median ??
                  inspectedReference?.p50 ??
                  "—"}
              </strong>
            </span>

            <span>
              Difference{" "}
              <strong>
                {inspectedComparison?.difference_from_median ??
                  "—"}
              </strong>
            </span>

            <span>
              Percentile{" "}
              <strong>
                {inspectedComparison?.percentile_position === null ||
                inspectedComparison?.percentile_position === undefined
                  ? "—"
                  : `P${inspectedComparison.percentile_position.toFixed(1)}`}
              </strong>
            </span>

            <span>
              P25–P75{" "}
              <strong>
                {inspectedReference?.p25 ?? "—"}
                {" – "}
                {inspectedReference?.p75 ?? "—"}
              </strong>
            </span>

            <span>
              Numeric population{" "}
              <strong>
                {(
                  inspectedComparison?.reference_numeric_count ??
                  inspectedReference?.numeric_count
                )?.toLocaleString() ?? "—"}
              </strong>
              {inspectedReference
                ? ` / ${inspectedReference.population_count.toLocaleString()}`
                : ""}
            </span>
          </div>
        )}
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
          inspectionIndex={
            inspectionAxisIndex
          }
          inspectionLocked={
            inspectionLocked
          }
          onInspectionHover={
            handleInspectionHover
          }
          onInspectionToggle={
            handleInspectionToggle
          }
        />
      )}


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
        <strong>Relative position</strong>

        {comparison ? (
          <>
            <span>
              Evaluated{" "}
              <strong>
                {comparison.comparison.evaluated_position_count.toLocaleString()}
              </strong>
            </span>

            <span>
              Range{" "}
              <strong>
                {comparison.comparison.percentile_position_min === null
                  ? "—"
                  : `P${comparison.comparison.percentile_position_min.toFixed(1)}`}
                {" – "}
                {comparison.comparison.percentile_position_max === null
                  ? "—"
                  : `P${comparison.comparison.percentile_position_max.toFixed(1)}`}
              </strong>
            </span>

            <span>
              Method{" "}
              <strong>
                {comparison.comparison.percentile_position_method}
              </strong>
            </span>
          </>
        ) : (
          <span>
            {isComparisonLoading
              ? "Calculating relative position..."
              : "Relative position not available."}
          </span>
        )}
      </div>

      {comparison && (
        <WideTemporalPercentilePositionChart
          comparison={comparison}
          inspectionIndex={
            inspectionAxisIndex
          }
          inspectionLocked={
            inspectionLocked
          }
          onInspectionHover={
            handleInspectionHover
          }
          onInspectionToggle={
            handleInspectionToggle
          }
        />
      )}

      <WideTemporalSeriesChart
        detail={detail}
        inspectionIndex={
          inspectionAxisIndex
        }
        inspectionLocked={
          inspectionLocked
        }
        onInspectionHover={
          handleInspectionHover
        }
        onInspectionToggle={
          handleInspectionToggle
        }
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
