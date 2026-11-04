# RAWSIGHT – Quality Requirements Profile v0.1

**Status:** First implementation, verification in complete RAWSIGHT environment outstanding
**Baseline:** commit `73fa57d` (`main`)
**User-facing Swedish:** *analysområde* (internal JSONL field `region_id` unchanged).

## Purpose

Store **declared and traceable** quality requirements separately from Data Facts, evidence and assessments. A requirements profile is not a new detection engine. It must not create evidence or mutate the source.

## Supported in v0.1

- `DQ-COMP-001/0.1.0`: required completeness of a named column with an **integer `max_missing`**.
- Profile bound to `dataset_id` plus the **actual source-file SHA-256**. Caller must calculate and supply the real source SHA-256, not a fingerprint of a result file. RAWSIGHT does not independently certify filesystem origin in this adapter.
- Declared requirement `source`: a human/document reference, not a claim of independently verified approval.
- `status=draft` **never causes quality assessment**; `approved` requires named `approved_by` and `approved_at` fields (metadata, not cryptographic authorization).
- Dataset-wide column rule (`dataset_column`) and optional `area_column` override. An overriding requirement **must** cite the base requirement by its ID in `overrides`.
- Duplicate/conflicting definitions for the same target rejected; mismatching dataset identity or fingerprint rejected.
- Resolves to exactly the narrow `assess_completeness()` requirement interface; does not alter its five-state semantics.
- Streamed assessments for each existing `complete_column` finding in evidence JSONL. No source-file write.

## Explicit limits and safeguards

1. A dataset-level requirement applies to each assessed analysis area; this adapter does **not** claim a whole-dataset quality verdict from area-level results.
2. A missing finding/column/area is **not** silently marked `verified`; this stream processes available findings. Completeness of the evidence partition must be certified separately by the existing execution manifest and summary.
3. A source SHA-256 is an identity control, **not** proof that a quality requirement is legitimate.
4. A declared `approved` flag is not authorization enforcement. Future integration requires the host app to handle identity, approval audit, immutable versions and trust boundary.
5. If a source file changes, the caller must compute its new SHA-256; reusing an old fingerprint defeats the check.
6. Rules other than DQ-COMP-001 are only catalog designs, not executable in this module.
7. Time-based requirements, cross-dataset requirements and Analysis Suitability are future versions. No implicit time thresholds.
8. The adapter keeps the existing source/evidence JSONL files unchanged and never auto-generates an approved requirement.
9. Version and identity inputs are external arguments to the adapter; the app integration must bind them to the actual Dataset Profile and completed analysis run.

## Data model

`schema, profile_id, profile_version, status, source{dataset_id,sha256}, approved_by, approved_at, requirements[]`

Requirement object: `requirement_id, rule_id, rule_version, scope, column, [area_id], max_missing, source, [overrides]`.

No implicit inheritance of approval, no fabricated scope, and no `Good/Bad/Ugly` blanket verdict. Existing data facts remain neutral in unassessed areas.

## Verification

13 isolated unit tests (one lightweight stand-in for `assess_completeness`; **full integration not yet certified**). Required on user's machine: run the new unit tests and full Python suite with the real RAWSIGHT `data_quality_rules_v1.py`; then run one synthetic approved/draft case and inspect outcomes.

## Follow-up

- Wire profile to Dataset Profile store and run provenance, including profile version and hash captured at assessment time.
- Add coverage checks that detect requirements with no matching fact/area.
- Add a write/approval workflow with user authorization and append-only audit trail.
- Consider aggregating quality assessments only when the full partition and requirements coverage are explicitly verified.
- Expand to uniqueness, domain and schema rules only after the corresponding facts and rule semantics are defined.
