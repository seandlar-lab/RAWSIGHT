# RAWSIGHT – Verifierad arbetsstatus

Kontrollerad: 2026-10-30

## Git
- Branch: `main`.
- HEAD: `c6300fa` – Add temporal gap cross-series comparison.
- Historik i senaste fem commits:
  - `c6300fa` Add temporal gap cross-series comparison
  - `b2fb0e8` Connect cross-series presence to Tauri backend
  - `e5cb1ad` Add cross-series presence analysis
  - `bfe8c60` Expose continuity evidence in temporal detail
  - `6880717` Plumb continuity context into long temporal detail
- Lokal `main` rapporterades ligga 123 commits före `origin/main`; remote-status har inte verifierats med fetch.

## Arbetskatalog vid senaste kontroll
- Modifierad: `engine/rawsight/long_temporal_execution.py`.
- Diff visade endast extra indrag i en strängliteral för RuntimeError (rad ca 127); ändringen bör granskas innan den åtgärdas.
- Ej spårad: `testdata/`. Innehållet har inte granskats; ta inte bort katalogen.
- Git gav radslutsvarning (CRLF till LF); ingen åtgärd utförd.

## Tester
Kommando som kördes från projektroten:

```powershell
$env:PYTHONPATH = '.\engine'
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -p 'test_cross_series_presence.py' -v
```

Resultat: **4 tester körda, samtliga OK** (0,154 s):
- `test_counts_and_extrema`
- `test_empty_interval`
- `test_invalid_range`
- `test_outside_rows_excluded`

Detta verifierar enhetstesterna för cross-series presence, inte hela applikationen eller senaste gapjämförelsen.

## Funktioner – evidensnivå
- Cross-series presence i Python: **enhetstestad**.
- Kommando/registrering i Tauri: **identifierad i källkod**, inte end-to-end-verifierad.
- `break_before` i Python och React: **identifierad i källkod**, funktionellt beteende ej omtestat i denna session.
- Temporal gap cross-series comparison: **commit identifierad**, funktion och tester ännu ej inspekterade här.

## Miljö
- Windows/PowerShell, repo `C:\Users\User\Dataprodukt`.
- Virtuell Pythonmiljö `.venv` finns och användes för godkända tester.
- `pytest` finns inte installerat; enhetstesterna använder `unittest`.
