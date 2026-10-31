# Analysis Evidence v0.1

## Intent
Display source-derived facts in RAWSIGHT's existing Explore detail view, without inventing a new dashboard or conflating an observation gap with a process anomaly.

## Contract
- `AnalysisEvidenceItem`: `id`, `kind`, `method`, `status`, `title`, `summary`, `scope`, `provenance`, optional `intervals`.
- Status `measured` means a source-derived property was calculated; it does not imply normality, abnormality or cause.
- `bounded` means the analysis retained only a sample of candidate evidence, not exhaustive coverage.
- Method-specific results adapt to the common presentation contract; source/backend contracts remain unchanged.

## Implemented
- Continuity adapter from `LongTemporalContinuityEvidence`.
- Shared `AnalysisEvidencePanel`; the existing `ContinuityEvidenceStrip` remains as a compatibility wrapper.
- Calendar-time interval bar clips evidence to selected range.
- No changes to `TimeSeriesChart`, Python, Rust, dataset loading, or existing selection behavior.

## Not implemented
- Connections for Pattern Similarity, Episode Discovery, MAD, Matrix Profile, Isolation Forest.
- Automated confidence or causality inference.
- Complete gap inventory or automatic episode selection.

## Verification
`cd app; npm run build`. Start Tauri and inspect selected interval across the known April 25–27 gap. Confirm that detail chart remains unchanged and the evidence panel still appears with source timestamps and bounded-sample warning.
