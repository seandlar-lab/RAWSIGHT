# RAWSIGHT – Data Quality Evidence v0.1

This is a deterministic, standalone evidence contract over **explicit Analysis Regions**.
It reports positive, attention-worthy, and insufficient findings together.
It makes no assumptions about calendar months, timestamps, or even temporal data.

## Region types

- `whole`: the entire supplied observation collection
- `row_range`: half-open range of row offsets (zero-based, source order)
- `category`: rows with a selected category value
- `time_range`: half-open timestamp interval, requires an explicit time column

**Region selection is not automatic in this version.** A future planner will choose meaningful partitions based on structure and user intent. An unknown structure defaults to whole dataset.

## Scope and semantics

- Observation quality is different from normal business behaviour.
- Positive evidence never proves values are correct.
- Repeated timestamps are not assumed to be duplicates of full rows.
- No source modification, aggregation, imputation, or silent cleanup.
- Findings include a region ID, column, polarity, kind, message, measurable evidence and provenance.
- In-memory reference limit: 100,000 rows; scalable DuckDB execution and Dataset Profile integration are subsequent changes.

## Next implementation steps

1. Build a DuckDB-backed executor using SourceExecutionContext for larger sources, with bounded output and no unconditional `fetchall()`.
2. Add analysis-region discovery that uses observed data boundaries, not fixed calendar partitions.
3. Store quality evidence separately from light-analysis cache, with its own version/invalidation.
4. Surface selected positive, negative and insufficient findings in a plain-language Understand view, with links to source rows or time ranges.
5. Verify with Metro Interstate Traffic Volume and MetroPT3, plus a non-temporal dataset.
