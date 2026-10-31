# RAWSIGHT – Episode Discovery Execution v0.1

- Source: RAWSIGHT `SourceExecutionContext` and existing vertical temporal-axis metadata.
- Input: explicit interval, expected sampling interval, optional numeric signal selection and caller-supplied change thresholds.
- Output: existing `automatic_episode_discovery` result plus execution metadata.
- Analysis is performed on *original observations*, never reduced display points.
- Resource safeguard: at most `max_observations` can be fully analyzed. If the interval exceeds the cap, return `status=resource_limit`, with **no partial episodes**.
- Duplicate timestamps are not silently normalized; the existing detector rejects them.
- No automatic baseline estimation, gradual trend detection, causal inference, or anomaly labels.
- Only vertical temporal data are supported in this execution route.
- This module is **not yet wired** through `profile.py`, Tauri, or React.

## Local verification

From the repository root:

```powershell
$env:PYTHONPATH = '.\engine'
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -p 'test_episode_discovery_execution.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -v
```

Expected: 7 new tests (27 total if the prior 20 remain). Confirm results locally before committing.

## Next integration step

Expose an explicit engine CLI command using existing JSON temporal-axis context; then add a Tauri invocation and reuse `episodeDiscoveryEvidenceAdapter` in Explore. Keep command arguments bounded; don't serialize millions of rows to frontend.
