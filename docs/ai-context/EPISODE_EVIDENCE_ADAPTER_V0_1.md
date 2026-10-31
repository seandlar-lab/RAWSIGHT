# Episode Discovery → Analysis Evidence adapter v0.1

## Purpose
Introduces a typed TypeScript contract matching Python `discover_episodes()` and adapts its *candidate segments* into shared `AnalysisEvidenceItem`. The detector remains server-side, not in React. This version **does not yet connect a backend invocation to Explore**. No synthetic or hard-coded episodes are displayed.

## Semantics
- New kind `temporal_segment` denotes a candidate grouping of observed rows, **not** an anomaly, operating mode, motif, or missing observation.
- `status: candidate` even though the detector itself has `status: measured`; that status confirms the algorithm ran, not that its inferred segment is a validated fact about the domain.
- `temporal_gap` boundaries stay with existing continuity evidence to avoid duplicate evidence and false overlays.
- No `intervals` in these evidence items, because `AnalysisEvidencePanel` currently shades all interval items with an orange bar that denotes an observational gap. Presenting segment spans using that bar would be misleading.
- Distinguishes *adapter available* from *runtime integrated*: the latter is not complete.

## Next implementation
1. Define a bounded invocation from the active dataset/selected range through existing Python/Tauri architecture. Do not ship 1.5M observations over IPC.
2. Return an `EpisodeDiscoveryResult` and adapt it at the Explore detail view.
3. Extend shared panel with textual rendering for non-interval evidence, without presenting segment durations as data gaps.
4. Add integration tests for actual runtime payload and selection semantics.

## Validation
Run project's existing frontend build after installation. The adapter is pure and can be unit tested independently.
