# RAWSIGHT – Understand v0.1

Status: implementation ready for local frontend verification (not yet validated by project npm build).

## Scope
- Adds a read-only Understand view between Light Analysis and Explore in existing navigation.
- Reuses currently loaded DatasetProfile, no new Tauri or Python calls.
- Displays dataset row/column counts, missingness measured by profile, and duplicate row count if measured.
- Does not equate null/missingness with data correctness or requirement compliance.
- Does not assume time-series, geographical, traffic or sensor data.
- Does not present Good/Bad/Verified as an official quality assessment; no quality rule evaluations are loaded in this version.
- Keeps existing features unchanged; app remains in existing style, component has scoped styles.

## Implementation
- app/src/components/UnderstandOverview.tsx
- app/src/components/UnderstandOverview.css
- anchored modifications in app/src/App.tsx:
  1. import component
  2. add ProjectSection 'understand'
  3. add navigation item after Light Analysis
  4. add workspace label
  5. render overview from profile

## Verification
1. Run installer in dry-run then apply; stop if anchors no longer match.
2. `cd app; npm run build`.
3. Open existing project; navigate Understand and verify the currently selected Dataset Profile is shown.
4. Check project with no profile: clear empty state and route to Light Analysis.
5. Verify actions open existing Light Analysis and Explore.
6. Change projects and confirm displayed profile follows selected source.
7. Run Python unittest suite and `git diff --check`.

## Deferred
- JSONL Quality Findings Summary integration / full provenance.
- Quality Requirements Profile and Rule Engine assessments.
- Resource & Progress Monitor integration.
- Cross-dataset comparative analysis.
- Wider navigation redesign or theme replacement.
