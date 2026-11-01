# Event Context Execution v0.1

## Purpose
Connect `event_context.analyze_event_context()` to original source observations through `SourceExecutionContext` and the existing normalized vertical temporal-axis metadata.

## Entry point
`rawsight.event_context_execution.execute_event_context(file_path, temporal_axis, anchor, selected_columns, expected_interval_seconds, ...)`.

- `temporal_gap` anchor: exact existing `before_time` and `after_time` observations. The execution layer checks that they are unique and *adjacent* in the complete source (no other valid timestamp strictly in between).
- `point_event` anchor: exactly one existing source observation at `time`. The anchor value is returned separately and excluded from both context windows.
- Source-local naive timestamps only; no implicit timezone conversions.
- Up to 1,000 source observations per side by default. This is a hard rejection on excess request, not sampling. Actual windows may be shorter if the source ends or a further gap is encountered.
- Explicit technical-numeric column selection, no silent auto-selection.
- Source records are sorted by parsed time, never by file order. Missing values are retained as missing; no interpolation or extrapolation.
- Source context caller retains ownership of supplied open context.

## Output and scope
The output uses the existing `event_context` response (`before`, `after`, `anchor`, `window_spec`, `limitations`) plus `execution` metadata. These are descriptive statistics per side (first/last values, delta, minimum/maximum and coverage); this is **not** motif clustering or similarity across different event anchors.

## Tests and limitations
10 deterministic unit tests with fake source-context semantics; require real DuckDB smoke test in the RAWSIGHT installation before any claim of successful source integration. No Tauri or React connection in this change. The adapter may scan the source several times per event; optimize only after profiling on realistic datasets. `temporal_gap` detection is not performed by this module; caller must supply candidate anchors. No causal assertion or anomaly classification.

## Next
Run tests and real-source smoke test; commit files separately. Then compare aligned before/after contexts across multiple verified event anchors with coverage and sample-size safeguards, incorporating existing Pattern Similarity when time alignment is meaningful.
