# RAWSIGHT — Event Context Similarity v0.1

## Goal
Compare *supplied* multivariate observation sequences around two or more verified events. Report pattern similarity separately **before** and **after**. Do not compare directly across an event gap.

## Implementation
`engine/rawsight/event_context_similarity.py`: `compare_event_contexts(target, candidates, selected_columns=[...], minimum_points=3, minimum_coverage=1.0, minimum_measured_signals=1, max_candidates=100)`.

Each event is an object with a unique `id` and `before` and `after`, each containing:

```json
{"series":{"A":[1,2,3,4,5],"B":[4,3,2,1,0]},"alignment":{"method":"observation_index","bin_count":5}}
```

`observation_index` indicates a caller-established ordered sequence aligned by position. This is **not** elapsed-time alignment, and the caller must ensure corresponding positions represent meaningful comparable observations. `elapsed_time_bins` is accepted only when **caller-provided** sequences already use time bins of the same `bin_width_seconds`, with no imputation. This module does not create these bins.

The implementation delegates the actual per-signal similarity calculation to existing `rawsight.pattern_similarity.compare_episodes()`; the two sides are calculated independently. A full-event similarity is the equal-weight mean of the before- and after-scores **only when both sides have enough qualifying signals**. Each side retains `signals` and `excluded_signals` evidence including counts and coverage. Insufficient comparison on either side leaves `full_context_similarity=None` and status `partial_evidence`.

## Limitations
- No source-backed fetching, verified anchor validation, automatic alignment, interpolation, resampling, anomaly detection, significance testing or discovery of event pairs in this release.
- `Event Context Execution` currently returns descriptive summaries, **not the raw ordered observation windows**. The source-backed adapter still needs to expose validated bounded sequences or provide a dedicated fetcher before production use.
- Pearson-based shape similarity does not prove equal levels, amplitude, elapsed time, causality or normal operation. A short monotonic trend can have high similarity.
- Multi-dataset alignment and source identity/key semantics are not supported yet.
- Prevent combinatorial over-search by bounding candidates. An isolated high correlation is not statistical significance.

## Verification
14 isolated unit tests for paired sides, missing/constant signals, alignment incompatibilities, selection thresholds, ranking, limits and input mutation. Run the full RAWSIGHT Python suite in the actual project using the real existing Pattern Similarity module. No UI/Tauri changes.

## Next
Provide a bounded DuckDB evidence-window fetcher preserving actual timestamps, gap boundaries, selected signals, and alignment metadata. Compare at least two independently verified events. For shorter windows either return insufficient comparison or use an explicitly defined and validated alignment policy; do not silently truncate to a fixed count. Then present per-signal evidence in Discoveries.
