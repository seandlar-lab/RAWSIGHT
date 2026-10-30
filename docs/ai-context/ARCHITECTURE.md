# RAWSIGHT – Arkitekturöversikt

Uppdaterad: 2026-10-30
Status: Partiellt verifierad från sökningar i användarens lokala Git-repo, inte fullständig kodgranskning.

## Teknik och komponenter
- Frontend: React/TypeScript, i `app/src/`.
- Desktop/backend-brygga: Tauri/Rust, bl.a. `app/src-tauri/src/lib.rs`.
- Analysmotor: Python, bl.a. `engine/profile.py` och `engine/rawsight/`.
- Databas för analys: DuckDB (verifierad i enhetstest).

## Identifierade kodvägar
- `engine/rawsight/long_temporal_series.py`: förekomster av `break_before` och tidsseriehantering.
- `app/src/types/longTemporalSeries.ts`: `break_before: boolean` i TypeScript-kontrakt.
- `app/src/components/LongTemporalSeriesChart.tsx`: konsumerar `point.break_before`.
- `engine/rawsight/long_temporal_series_execution.py`: resultat som innehåller `break_before`; beteendet behöver undersökas.
- `engine/rawsight/cross_series_presence.py`: `analyze_cross_series_presence`.
- `engine/profile.py`: kommandot `cross-series-presence-context`.
- `app/src-tauri/src/lib.rs`: `explore_cross_series_presence` och registrering av Tauri-kommando.
- `engine/tests/test_cross_series_presence.py`: enhetstester för cross-series presence.

## Att verifiera
- End-to-end-flödet från UI till Tauri, Python och tillbaka.
- Exakt algoritm och semantik för `break_before` i olika tidsserievägar.
- Skillnaden mellan presence-analys och temporal gap cross-series comparison.
- Persistens, prestanda och gränser för större datamängder.
