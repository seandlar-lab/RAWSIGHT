# RAWSIGHT – Event Context v0.1

## Goal
General description of observed numeric context on both sides of a supplied event anchor, first temporal gaps, then point events such as extreme values. Domain neutral.

## Contract
`analyze_event_context(observations, anchor, selected_columns, expected_interval_seconds, gap_multiple=3.0, before_points=30, after_points=30)`.

Two anchor variants:
- `{kind: temporal_gap, before_time: ISO, after_time: ISO}` must reference consecutive source rows with a sufficiently large interval.
- `{kind: point_event, time: ISO, label: extreme_value}` must reference an existing row; anchor row is excluded from the before and after windows and returned separately.

Each side yields observation count, start/end time, and per-column valid count, coverage, first/last valid values, delta, minimum and maximum. Return explicit `insufficient_context` if one side is unavailable. No interpolation, no crossing gaps, no anomaly or causal claims.

## Deliberate limitations
- Input is already materialized, sorted, unique-timestamp observations. This is **not** the DuckDB SourceExecutionContext adapter and is **not** suited to passing entire datasets through memory.
- Fixed number of observations can represent different elapsed durations: retain boundaries and sampling information before any similarity comparison.
- No automatic discovery of anchor events; use the existing continuity/episode analysis to supply gap anchors. An extreme-value detector can supply point anchors later.
- No pattern matching implemented. `pattern_similarity.compare_episodes` requires aligned equal-duration bin sequences; that adapter is separate future work.
- Incomplete context at the edge of the supplied input may reflect extraction limits; caller should record provenance and bounds.

## Next
1. Verify ten isolated tests and full suite locally.
2. Read bounded windows around selected source anchors from DuckDB without extracting all rows, respecting true gap boundaries.
3. Compare context across multiple events using transparent, aligned bins and coverage safeguards.
4. Present evidence in existing Explore, without framing recurrent patterns as normal or causal.
