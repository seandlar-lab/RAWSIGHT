# RAWSIGHT – Nästa arbetsmoment

Uppdaterad: 2026-10-30

## Prioritet 1 – förstå senaste implementeringen
1. Granska vad `c6300fa` faktiskt ändrade (`git show --stat c6300fa` och riktad kodgranskning).
2. Identifiera API/resultatkontraktet för temporal gap cross-series comparison.
3. Fastställ vilka tester som täcker den och kör dem med `unittest`.
4. Kontrollera om gap i flera serier kan särskiljas från saknade värden på enstaka rader.

## Prioritet 2 – kontroll av helheten
1. Följ flödet UI → Tauri → Python → UI med ett litet reproducerbart dataset.
2. Verifiera beteendet för `break_before` med både gap och kontinuerliga serier.
3. Kontrollera resultaten vid tomt intervall, ogiltigt intervall, NULL och oändliga värden.

## Prioritet 3 – stabilisering och fortsatt analys
1. Granska lokal ändring i `long_temporal_execution.py` och besluta om den ska återställas.
2. Inventera `testdata/` innan någon Git-åtgärd.
3. Kontrollera varför lokala `main` är 123 commits före `origin/main` och om remote är avsedd backup. Gör ingen push utan beslut.
4. När nuläget är verifierat: formulera nästa analysfunktion utifrån faktiska resultat (t.ex. gemensamma respektive seriespecifika tidsluckor).

## Avslutningsrutin för varje arbetspass
- Uppdatera `STATE.md` med commit, arbetskatalogstatus och faktiskt körda tester.
- Uppdatera `NEXT.md` med en tydlig första åtgärd för nästa pass.
- Ange explicit vad som är implementerat, testat och ännu antaget.
