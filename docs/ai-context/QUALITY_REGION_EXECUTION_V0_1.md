# Quality Region Execution v0.1

Base commit: `fe52afa`.

## Responsibilities

`engine/rawsight/quality_region_execution.py` uses the established `SourceExecutionContext` and DuckDB source view. It computes exact full-source counts for selected columns (missing fields) and, if an explicit temporal column is supplied, unique/invalid timestamps. No data is rewritten.

It also retrieves a bounded **prefix of rows returned by the DuckDB source view**, at most 100,000 observations, to invoke `discover_quality_regions` and `assess_quality`. The results are explicitly labelled as **partial** if the full source contains more rows. This preview is neither representative nor exhaustive, and DuckDB view order must not be confused with a stable canonical source-row order.

There is NO automatic temporal-axis inference, no calendar partitioning, no transformation, no quality score, no AI and no GUI bridge in v0.1. The maximum is configurable with `max_rows` (default 60,000); the analysis fails explicitly if the chosen column budget exceeds 24 rather than silently dropping fields.

## Next

- Test against original Metro Interstate Traffic Volume (48,204 rows): expect complete region coverage when `max_rows=60000`, but region-budget overflow may prohibit an exhaustive partition; this is explicitly reported.
- Test against MetroPT3 (~1.5M rows): expect exact source-wide counts and `partial_region_coverage` for region discovery.
- Improve stable source order or source-index provenance and scalable all-source region scanning before treating region boundaries as exhaustive or applying them directly as source-row addresses.
- Add semantic metadata, positive/negative region narratives and evidence links to Dataset Profile/Discover after validation.
