# RAWSIGHT Relationship Analysis v0.1

## Purpose
Domain-agnostic analysis of relationships among technically numeric source columns. Runs full-source exact DuckDB aggregate queries, not a visualization projection.

## API
`execute_relationship_analysis(file_path=..., selected_columns=None, max_columns=16, min_pair_observations=3, temporal_axis=None, start_time=None, end_time=None, source_context=None)`.

- `selected_columns=None`: analyze all technically numeric columns; if more than `max_columns`, return `resource_limit` without silently selecting a subset.
- Output `columns`: per-column number of finite values, missing/nonfinite count, sample SD and minimum/maximum.
- Output `relationships`: pairwise Pearson r and *pair-specific* number of complete observations, sorted by magnitude when measured.
- Constant or insufficient pairwise variance yields `pearson_r=null` and explicit status.
- Optional time scope only with an existing vertical temporal axis; never infers a new temporal axis.
- No statistical sampling, significance tests, p-values, Spearman, PCA, clustering or causality claims.
- No automatic identifier exclusion, because numerical appearance alone cannot establish semantics.

## Known limits
- One aggregate SQL scan may still be computationally expensive on a very large dataset; `max_columns` bounds comparisons, **not rows**. Consider explicit execution budgets and progressive results later.
- Strong correlation can be driven by global trends, time dependence, duplicated representations, mixtures of regimes, or common confounders.
- Pairwise-complete samples differ between pairs.
- Technical numeric filtering does not resolve semantic columns (e.g. identifiers encoded numerically). Such columns must remain transparently selectable/excludable.
- Not yet wired to `profile.py`, Rust/Tauri, React or evidence adapter. This is engine v0.1 only.

## Verification
Run `PYTHONPATH=./engine python -m unittest discover -s engine/tests -p test_relationship_analysis.py -v` and full suite. Tests require DuckDB and should be run in the user's RAWSIGHT environment.
