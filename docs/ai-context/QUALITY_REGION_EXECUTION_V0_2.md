# Quality Region Execution v0.2 — full source, resource aware

Implementation: `engine/rawsight/quality_region_execution_v2.py`, entrypoint `execute_quality_regions_v2`.

## Purpose

- No arbitrary row, column or region-count ceilings. `batch_size` is a processing block size, **not** a data limit.
- Exact source-wide missing and timestamp counts from a single materialized scan-order snapshot in DuckDB.
- Full scan with stable adjacent-row comparisons across batch boundaries.
- Exact positive-interval median calculated within DuckDB; boundaries stored on disk (JSONL) without cap.
- Full half-open row-range partition, with transition neighborhoods and inter-transition stretches.
- Per-region positive/attention/insufficient evidence stored on disk (JSONL); no truncation, original source unchanged.
- No calendar assumption; if no time axis, boundaries can still come from missingness-pattern transitions.
- No `complete` status if a run cannot finish: an exception is raised and partial temporary artifacts removed.

## Important limitations

- The snapshot's scan order is stable *within the run*, but not certified as the original source file's physical row order; `source_order_certified=false`. A source-backed ordinal is needed for a stronger guarantee.
- Per-region time evidence counts adjacent repeats/reversals, not all non-adjacent duplicate timestamps. Source-wide unique timestamp count is exact.
- Full-region quality checks in this version are missingness and local timestamp consistency, not complete data-quality or business-normality certification.
- The result is **not a GUI integration**, nor a persistent indexed dataset service. JSONL event files are intentionally accessible for downstream investigation; they may be large.
- DuckDB will use memory, compute and temporary storage. If resources run out, the function reports failure rather than incomplete success. The implementation uses a caller-configurable batch size, but does not yet implement automatic machine-resource detection, dynamic batch tuning, resumability or progress callbacks.
- A highly irregular source can legitimately generate a very large region manifest. This is not silently capped.

## Next architecture work

Certify file order where available, make result paths project-managed and versioned, add progress/checkpoints and dynamic memory/batch adaptation, add richer per-region quality metrics and hierarchical exploration, connect to Dataset Profile/Understand/Discover after verification with real sources.
