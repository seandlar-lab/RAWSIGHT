# Event Context Similarity Execution v0.1

Goal: source-backed, bounded comparison of temporal-gap contexts, using the existing `execute_event_context` and `compare_event_contexts` contracts.

- Scans a **single selected data source** for temporal gaps (strictly larger than `expected_interval_seconds * gap_multiple`), orders by duration, and rejects more than `max_events` to avoid silently implying exhaustive search.
- Verifies each gap's adjacent source observations through `execute_event_context`.
- Fetches bounded, ordered real observations in selected numeric columns before and after each gap; stops at any secondary temporal gap.
- Requires exactly `points_per_side` contiguous observations per side to score that side. Shorter windows are deliberately unscorable (no zero-padding used for scores; placeholder None values flag insufficient evidence).
- Calls existing Event Context Similarity separately for before and after; full similarity requires both sides.
- Alignment uses **observation index**, not elapsed time: a correlation-based shape score is not proof of equivalent duration or dynamics. Report each side's elapsed span and warning if its ratio exceeds 1.25.
- No resampling, interpolation, matching across source datasets, significance, causation, or automatic validation of similarity against a null model.
- This first version only finds temporal gaps in one dataset. Point-event anchors and cross-dataset alignment are future extensions.

## Resource controls

`points_per_side` 3–1000; `max_events` 2–100. This protects returned data volume, but the gap scan still reads the source temporal column and each event window generates bounded source queries. Large CSV scans can be expensive. Tune or precompute a local DuckDB source table for speed.

## Integration validation

Run the Python tests with `PYTHONPATH=./engine` and then execute the smoke test on MetroPT3. Verify the chosen time axis specification from your working Event Context smoke script. If MetroPT3 has >`max_events` gaps, the adapter intentionally raises; choose a narrow source scope or increase the cap, never silently take a partial set and call it comprehensive.
