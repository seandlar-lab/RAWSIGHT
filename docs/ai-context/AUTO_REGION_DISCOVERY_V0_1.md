# Automatic Analysis Region Discovery v0.1

Baseline: commit `e93928f`.

- Deterministic, in-memory reference planner; no calendars, mandatory time axes, cleaning, imputation, aggregation, or causality claims.
- API: `discover_quality_regions(rows, time_column=None, value_columns=None, max_regions=40, gap_multiplier=5, min_region_rows=3)`.
- Always includes `{'id':'dataset','kind':'whole'}`. Additional `row_range` partitions are disjoint and exhaustive in **source row order**.
- Proposes transitions due to repeated timestamps, source-order reversals, invalid timestamps, observed long gaps, and optional shifts in missingness patterns.
- Long gap boundaries are *transitions*, not a statement that either side is defective. 'between_transitions' is a structural description, never a verified clean period.
- Explicit `region_limit_exceeded` when discovered regions do not fit the budget. Never silently present a partial partition as complete.
- Compatible with existing `assess_quality(..., regions=[...])`; remove discovery-only `discovery_role` if desired (assess_quality ignores it).
- Important: repeated timestamps are kept intact; adjacent time delta is computed from original sequence without sorting.
- Limit: 100k in-memory rows, no source executor yet. May propose very many regions for noisy data; result is bounded and discloses overflow.
- Next: DuckDB-backed bounded source execution, richer region proposal (multi-dimensional and categorical), evidence scoring without global quality grade, UI/Understand integration.
