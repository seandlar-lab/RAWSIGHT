# RAWSIGHT – Automatic Episode Discovery v0.1 (första kärna)

Datum: 2026-10-31. Status: *fristående prototyp, inte integrerad i projektet eller testad mot MetroPT3*. Designunderlag bygger på `SESSION_2026-10-30.md` och nuvarande `pattern_similarity.py`.

## Avsikt

Identifiera **kandidatepisoder**, inte normala/onormala driftlägen, felorsaker eller verkliga händelser. Den första detektorn arbetar med en redan sorterad sekvens av observationer med gemensam tidsaxel. Den kan segmentera vid:

1. **Temporal gap**: observerat tidsavstånd större än `expected_interval_seconds * gap_multiple`.
2. **Concurrent change**: två eller fler (konfigurerbart) numeriska signaler med absolut förändring mellan intilliggande observationer över varsin explicit angiven tröskel.

För alla andra punkter fortsätter episoden. Detta betyder särskilt att **gradvis stigande förlopp ännu inte upptäcks självständigt**. Denna första version avser kontrakt, säker segmentering och testbarhet; fas 2 behöver automatisk förändringspunktdetektion, skaloberoende signalurval samt episodkandidater för gradvisa förlopp.

## Funktionskontrakt

`discover_episodes(observations, *, timestamp_key="time", selected_columns=None, expected_interval_seconds, gap_multiple=3.0, change_thresholds=None, minimum_changed_signals=2, minimum_episode_points=3) -> dict`

Indata är en lista av dict-objekt, t.ex. `[ {"time": "2020-01-01T00:00:00", "x": 1.0, "y": 2.0} ]`. Tidsstämpel anges i ISO-format och måste vara strikt stigande. Blandade tidszoner och dubblettider avvisas i stället för att få en opålitlig ordning. Inga saknade värden fylls i. Om `selected_columns` utelämnas används samtliga andra fält, sorterade lexikografiskt.

Resultat:

- `analysis_kind`: `automatic_episode_discovery`.
- `status`: `measured` eller `insufficient_data`.
- `method`: `gap_and_explicit_concurrent_change_v0_1`.
- `boundaries`: lista med `index`, `reason`, `gap_seconds`, `signals`.
- `episodes`: `id`, start/slut i index och tid, `observation_count`, `status` (`candidate`/`too_short`), `valid_counts`, `coverage`, `start_boundary`.
- `limitations`: förklarar beroende av givna trösklar, strikt tidsordning och frånvaro av anomalitolkning.

Deterministiskt ID bygger på radindex i den insända sekvensen och är **inte** stabilt över datainlägg. En framtida källa-/hashbaserad identitet behöver designas när DuckDB-kopplingen görs.

## Testomfång

Sju syntetiska tester: kontinuerlig sekvens, gapgräns, samtidig förändring, NULL/NaN, dubbla tider, determinism och felaktiga parametrar. Testade lokalt i dokumentframställningsmiljön 2026-10-31: 7/7 OK. **Inte körda i användarens `.venv` ännu.**

## Viktiga begränsningar

- Inga automatiskt lärda signaltrösklar; inga gradvisa förändringspunkter.
- Ingen automatisk binning/normalisering av oregelbundet samplade serier.
- Inga signalvikter, mönsterfamiljer eller poäng för anomali.
- Ingen anslutning till DuckDB / `SourceExecutionContext`, `compare_episodes()`, Tauri eller React.
- Stora dataset ska i nästa fas streamas/batchas; använd inte denna in-memory-ingång för hela MetroPT3 utan tydliga resursgränser.

## Nästa verifiering

1. Lägg in endast `episode_discovery.py` och `test_episode_discovery.py` i projektets respektive kataloger.
2. Kör separat test och därefter hela testsuiten; `git status -sb` före commit.
3. Bygg en läsande DuckDB-adapter för ett litet begränsat analysfönster och testa MetroPT3:s kända tidslucka utan hårdkodning i detektorn.
4. Utveckla separat automatisk upptäckt av flersignalsramper/förlopp; verifiera på historiska MetroPT3-episoder som ännu inte används som detektionsfacit.
5. Koppla detekterade, tidsjusterade avsnitt till `compare_episodes()` först när upptäckt och urval testats var för sig.

**Versionsnotering:** `STATE.md` och `NEXT.md` på GitHub är äldre än `SESSION_2026-10-30.md`; uppdateras först efter att lokal installation/test och aktuell Git-status har verifierats.
