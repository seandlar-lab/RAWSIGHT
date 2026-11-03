# Time Structure Evidence v0.3

## Syfte

Låt RAWSIGHT redovisa observerad tidsvariation utan att förväxla den med ett datakvalitetsproblem. V0.2 använde villkoret `positive_intervals_all_equal == false` för varningsstatus (`attention`), trots att alla tidpunkter i den analyserade sekvensen kunde vara giltiga och strikt stigande.

## Nytt kontrakt

- `quality_region_execution_v3.py` är en parallell, fullständig och diskbaserad exekvering; v0.2 behålls.
- Evidensens `time_structure` innehåller samma äldre fält, plus:
  - `positive_interval_distribution`: `count`, `min_seconds`, `max_seconds`, `mean_seconds`, `population_stddev_seconds`, `whole_source_median_baseline_seconds`, `exact_baseline_matches`.
  - `invalid_or_incomparable_adjacent_pairs`.
  - `cadence_observation`.
- Med enbart varierande, positiva intervall blir status `informational` (neutral observation), varken `positive` eller `attention`.
- Ogiltiga tidpunkter, lika intilliggande tidsstämplar eller bakåtgående tid ger fortsatt `attention`.
- Färre än två positiva intervall utan strukturella problem ger `insufficient`.
- Helt lika, positiva intervall och inga andra strukturella problem ger `positive` för just likformighet i analyserad ordning — inte bevis på verklig systemstabilitet.
- `quality_findings_summary_v3.py` accepterar både v0.2 och v0.3-evidens; äldre `attention` tolkas inte retroaktivt om. Nytt fält `time_interval_distribution_coverage` och ny exempelkategori `variability_examples`.

## Begränsningar

- Medelvärde och standardavvikelse beräknas strömmande på positiva intervall, inte på alla tidsskillnader. Min/max beskriver extrema positiva intervall.
- `whole_source_median_baseline_seconds` är empirisk median i källans snapshot, inte ett av verksamheten deklarerat mätkrav.
- `exact_baseline_matches` avser exakt lika numeriska tidsintervall, inte toleransbaserad närhet. Detta är medvetet för att inte hitta på en tolerans.
- Fysisk källordning är inte certifierad (`source_order_certified: false`). Sekvensberoende tolkning är därför preliminär.
- Ingen ny detektion, ingen datarensning, inget härlett orsaksantagande eller påstående om signifikans.
- Alla tidigare JSONL-filer lämnas oförändrade. Uppdaterad evidens kräver ny fullständig körning och skrivs i ny katalog.
- Ingen progressindikator eller checkpoint/resume i denna version.

## Verifiering

9 isolerade enhetstester har körts i en lokal miljö med *stubbar för externa projektberoenden*. De verifierar tidslogik och sammanfattningskontrakt, inte full RAWSIGHT-integration. Full suite och verkliga CSV-test ska genomföras på användarens arbetskopia innan commit.
