# RAWSIGHT Dataset Profile Persistence v0.1

## Goal
Separate import/light analysis from repeated Explore runs. User imports a dataset and optional metadata, RAWSIGHT profiles once and persists a reusable result.

## Implementation
`engine/rawsight/dataset_profile_store.py` wraps existing `rawsight.light_analysis.profile_dataset`; does not replace it. Saves JSON into caller-supplied store directory, atomically. Source rows are not copied. Fast identity uses absolute path, size, nanosecond modification time, and SHA256 of first/last 64 KiB. This is **not** a full content hash; edits confined to the middle while preserving timestamps/size are not detected.

- `external_metadata`: supplied JSON dictionary, preserved verbatim and distinct from analysis.
- `light_analysis`: unchanged dict produced by the existing profiler.
- `user_confirmed_metadata`: reserved for a future explicit confirmation workflow; no automatic inference is promoted to confirmed metadata.
- `cache_status`: `created`, `reused`, or `refreshed`.
- `analysis_version`: explicit cache invalidation marker; must be incremented when profiling behavior changes.
- No automatic discovery of metadata files in v0.1; user will select optional file.

## Next integration
1. Add project-scoped profile store path to Rust/Tauri project storage (do **not** persist under the dataset folder implicitly).
2. Route import to `get_or_create_profile` using the *existing* `profile_dataset` function. Preserve existing result JSON contract and progress behavior.
3. Show imported datasets with cache state, metadata provenance, and a simple `Explore` action.
4. Later add user confirmation/correction of metadata and more robust full-hash/quick-hash modes.

## QA
Run `PYTHONPATH=engine python -m unittest discover -s engine/tests -p test_dataset_profile_store.py -v`. Module unit tests use a fake profiler; real DuckDB integration is not claimed until tested in target environment.
