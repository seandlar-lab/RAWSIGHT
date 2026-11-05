# RAWSIGHT – Checkpoint 2026-11-05

## Verifierad status

- Branch: main, synkroniserad med origin/main
- HEAD: cec35ba
- Event Similarity-statushantering: 4522459
- Explore struktur och kontinuitet: cc8c941
- ExploreWorkspace presentation: 52274da
- Navigation v2.1: dbe210e

## Tester och byggstatus

- Python: 199 passed, 6 subtests passed
- TypeScript/Vite: godkänt
- 655 moduler
- Vite-byggtid: 5,91 sekunder
- JavaScript-bundle: 1462,42 kB
- Befintlig varning om stor bundle kvarstår

## Genomförd arkitekturförbättring

- Separat navigationsmodell med Tillbaka
- ExploreWorkspace extraherad stegvis
- ExploreVisualization extraherad
- LongTemporalSeriesPresentation extraherad
- Analysmotor och presentationslogik hålls separerade

## Event Similarity

- insufficient_ordering vid otillräcklig observationsordning
- resource_limit vid överskriden resursgräns
- Inga osäkra likhetsvärden
- Ingen ändring av likhetsalgoritmen

## Nästa prioritet

Event Similarity – UI Status Handling.

Anpassa EventSimilarityExplore.tsx och vid behov dess typer
för measured, insufficient_ordering, resource_limit och
insufficient_events.

Visa begripliga svenska förklaringar.
Visa inga likhetsvärden vid otillräckligt underlag.
Ändra inte Python/DuckDB-motorn under UI-etappen.

## Arbetsprinciper

- Små, verifierbara kodändringar
- Tester före Git-commit
- Separata commits för motor och gränssnitt
- Bevara dataset, urval och analysresultat vid navigation
- Inga installationspaket i projektroten
- Två lokala MetroPT3-smoke-skript fortfarande ospårade
