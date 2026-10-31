# Episode Evidence UI v0.2

Purpose: improve the existing Explore result presentation without changing detection, Python, Rust, or the time-series plots.

- Uses `EpisodeDiscoveryResult` and the existing `episodeDiscoveryToAnalysisEvidence` adapter.
- Shows individual candidate segments, observed start/end, source observation count, start-boundary reason, contributing signals (when supplied), and a collapsible per-signal coverage section.
- Does not confuse candidate segments with anomalies, motifs, operational states or unobserved intervals.
- Does not present inferred data between observed boundaries.
- Limits surface content by making coverage and limitations collapsible; no attempt at automatic episode classifications.
- The generic `AnalysisEvidencePanel` remains in place for continuity evidence elsewhere in the app.
- Resource-limit and insufficient-data handling remain in the existing Explore component.

Validation: `cd app; npm run build; cd ..`; run the existing Explore selection and confirm 2 candidate segments and the temporal gap after invoking the analysis. Stage only the three intended source/doc files.
