# Quality Findings Summary v0.1

## Purpose
Read the existing Quality Region Execution v0.2 JSONL evidence, **without reanalysing, modifying or discarding source data**, and create an explanation-ready compact summary.

## Contract
- `summarize_quality_findings` reads *all* region/finding records; presentation examples are independently bounded (`examples_per_polarity`). This is a UI limit, **not** a data or analysis cap.
- `summarize_quality_run` reads exact paths and expected counts from a completed/exhaustive v0.2 result.
- Counts per `polarity` (`positive`, `attention`, `insufficient`) and `kind`, contiguous region coverage, and expected counts are checked.
- Each displayed example carries its region's half-open `[start,stop)` range, `region_id`, precise JSONL line reference, and the unmodified source filename/path.
- Retain full evidence JSONL; do **not** interpret one `attention` record as a confirmed error or a `positive` record as verified business correctness.
- Display ordering is only a simple heuristic; no claim of statistical significance or causal effect.
- Current checks in v0.2: per-column missingness and adjacent timestamp consistency. No extrema, metadata plausibility validation, non-adjacent per-region duplication or semantic normality inference yet.
- Source scan order is not certified as original CSV order. This remains explicit.

## Use
Run `execute_quality_regions_v2(...)` and then `summarize_quality_run(r)`; or summarize existing files using `summarize_quality_findings(evidence_path=..., boundaries_path=..., source_rows=..., expected_regions=..., expected_findings=...)`.

## Next
- Inspect real candidate examples and category distributions in Metro Interstate and MetroPT3.
- Improve prioritization based on verified region features, **not** mere frequency; add semantic metadata and data quality dimensions after evidence validation.
- Add a navigable indexed JSONL reader for GUI investigation.
- Add Execution Monitor to both analysis and summary.
- Connect to Understand/Discover only after outputs validated; don't flatten thousands of findings into a false single quality score.
