# Quality Findings Summary v0.2 – grounded area interpretation

## Purpose
Turn full-source JSONL evidence into a **complete accounting** and a **small, transparent presentation**. All evidence remains on disk. No new event detection, quality scoring, business inference, ranking of significance or data cleaning.

## Source contracts
- `quality_region_execution_v2.py` outputs a JSONL area record (`record_type=region`, `discovery_role=between_transitions|transition_neighborhood`, half-open `start/stop`) followed by its `record_type=finding` records. Adjacent-boundary records are in a separate JSONL.
- Entry point `rawsight.quality_findings_summary_v2.summarize_quality_areas_v2`.
- The module verifies contiguous nonoverlapping complete coverage, region/finding linkage, expected counts, basic finding evidence consistency and ordered valid boundaries. It counts all records while retaining only a configurable number of **display examples**.
- Public-facing Swedish uses *område*, *analysområde*, *områdesgräns*, never *region*. Existing internal `region_id` remains unchanged for compatibility.

## Key distinctions / no ghosts
- An observed gap is a temporal adjacency in the **snapshotted scan order**; the actual source physical order is not certified. **No claim that a sensor was off** or that it represents a business incident.
- `transition_neighborhood` is an algorithmic area created around a structural boundary, not itself a separate defect.
- Two observations are insufficient to conclude cadence stability. That is a **method limitation**, not negative evidence about the original data.
- Positive completeness means *the selected column has no missing values in that area*, not that the data is true or normal.
- The module reports how many rows lie in each area role, not just area counts. A single meaningful anomaly must not be buried by repeated findings.
- Example areas are selected by **largest row span** for deterministic inspection. The examples are *not the most important*; no significance ranking is claimed.
- JSONL evidence lines and source paths are retained for navigation. All original events and findings remain in the original files.
- `source_order_certified` must be provided truthfully from upstream; in current v0.2 upstream it is false.

## Current limitations
- No AI interpretation or GUI integration; no area-level statistical significance or cause determination.
- `time_structure` checks within an area compare adjacent timestamps only, so no claim is made about nonadjacent duplicates. Source-wide distinct timestamps remain an independent DuckDB statistic.
- No reliable original physical source order proof, and no external metadata semantics yet.
- Workload is streamed from disk; display examples require only a bounded amount of in-memory state, but counters/column dictionaries grow with the diversity of data.

## Acceptance checks
- MetroPT3 should show 1,516,948 rows in 663 areas; 331 `large_observed_gap` boundaries, 331 2-row transition neighborhoods (662 rows), all with insufficient local cadence evidence. *These 331 insufficiencies are a methodological result.*
- Traffic sample should show 48,204 rows in 2,365 areas; counts must agree with the previous summary's 9,460 findings, 7,732 boundaries. Do not infer causes without reviewing evidence.
- Latest verified code checkpoint before this module: `6b94bc4`. v0.1 summary is an uncommitted local module; do not overwrite it.

## Next
Verify on saved MetroPT3 and traffic JSONL; then decide which plain-language consolidation earns its place in the Understand UI. Later use metadata to qualify what is meaningful and add process progress reporting.
