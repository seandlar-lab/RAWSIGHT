# RAWSIGHT – överlämning 2026-10-31: från analysmetoder till användarvärde

## Utgångspunkt och senast verifierad kodstatus

- Projekt/repo: `https://github.com/seandlar-lab/RAWSIGHT`.
- Projektrot lokalt: `C:\Users\User\Dataprodukt` (PowerShell).
- Senast **bekräftade** push för Relationship Analysis v0.1: commit `4cd92a2` på `main`. Kontrollera `git log -3 --oneline` nästa gång för faktisk HEAD; anta inte att den är oförändrad.
- Relationship Analysis v0.1: 8/8 tester godkända, full Python-testsuite 35/35 godkända i användarens lokala miljö.
- Äldre verifierade funktioner: Episode Discovery i Explore via Tauri/Python, Continuity Evidence, Continuity Axis och Episode Evidence UI, Pattern Similarity v0.1, gemensamt Analysis Evidence-kontrakt.
- Temporära ZIP-paket, installationsmappar, `.bak` och `testdata/` låg utanför Git; använd explicita `git add`-sökvägar och aldrig `git add .` utan kontroll.

## Verifierad Relationship Analysis med verkliga MetroPT3-data

Dataset `testdata/metropt3/MetroPT3(AirCompressor).csv`, 1 516 948 observationer, åtta manuellt valda numeriska kolumner i ett verifieringstest. Resultatet `measured`, metod `pearson_pairwise_complete_v0_1`, exakt DuckDB-aggregat utan sampling.

- TP3 / Reservoirs: Pearson r = 0.999993393678728; medel absolut värdeskillnad = 0.0018621020628277617; max absolut skillnad = 0.182; 1 013 954 värdepar skiljer sig åt. Slutsats: nästan samma variation, inte identiska variabler.
- H1 / COMP: r = +0.9714.
- TP2 / H1: r = −0.9613.
- TP2 / COMP: r = −0.9555.
- TP2 / Motor_current: r = +0.6975.
- H1 / Motor_current: global r = −0.6002.

**Explorativ gruppjämförelse (manuell SQL-kontroll, INTE implementerad generell analysfunktion):**

| Relation | Alla observationer | COMP=0 (247 328 rader) | COMP=1 (1 269 620 rader) |
|---|---:|---:|---:|
| TP2 / H1 | −0.9613 | −0.6211 | −0.2142 |
| TP2 / Motor_current | +0.6975 | +0.8347 | +0.0781 |
| H1 / Motor_current | −0.6002 | −0.7101 | +0.7168 |

Gruppjämförelsen illustrerar att globala korrelationer kan dölja betydande skillnader; ingen kausal tolkning och ingen automatisk klassificering som Simpsonparadox.

## Viktigaste produktbeslutet från avslutande diskussion

Användaren frågade: **"Vad får användaren ut av detta?"** Vi enades i resonemanget om att prioritera produktvärdet framför fler algoritmer:

> RAWSIGHT ska inte främst visa hur mycket statistik det kan räkna ut. Det ska hjälpa användaren upptäcka vad som är värt att förstå.

Användaren bör mötas av **undersökningsvärda fynd** med begriplig förklaring, evidens och föreslagen fördjupning – inte bara en korrelationsmatris, råa koefficienter eller tekniska metodnamn.

Exempel på fynd som kan presenteras med evidens:
1. **Nästan likartad variation:** TP3 och Reservoirs varierar nästan likadant, men värdena är inte identiska.
2. **Samband varierar mellan grupper:** H1 och Motor_current samvarierar negativt i en grupp och positivt i en annan – *gruppjämförelsen är än så länge manuellt verifierad och kräver en framtida generell algoritm för automatisk upptäckt*.
3. **Tidskontinuitet:** verifierat observationsuppehåll om 48 h 1 min 58 s mellan 2020-04-25 01:10:51 och 2020-04-27 01:12:49.
4. **Mönsterlikhet:** likheter mellan manuellt valda historiska episoder verifierade med Pattern Similarity; automatisk episodsökning och motividentifiering återstår.

De här exemplen ska inte framställas som om allt redan identifieras automatiskt.

## Rekommenderat NÄSTA STEG: RAWSIGHT Discoveries v0.1

**Börja med befintliga analysresultat och befintlig Explore-vy.** Bygg inte en parallell dashboard och inför inte fler beräkningsalgoritmer innan fyndpresentationen kan verifieras.

1. Granska den aktuella `App.tsx`, `AnalysisEvidencePanel`, analysspecifika adaptrar samt Relationship Analysis-resultatkontrakt. Utgå från faktisk HEAD.
2. Definiera ett enkelt, generellt *discovery*-kontrakt: typ/kategori, kort rubrik, observerat fynd, metod, omfattning, berörda kolumner/intervall, numeriskt underlag, begränsningar, föreslagen fördjupning och tydlig skillnad mellan `observed/measured`, `candidate` och `hypothesis`.
3. Implementera ett första **regelbaserat, reproducerbart** fynd från den befintliga relationsanalysen, exempelvis stark positiv/negativ samvariation och *candidate near-redundancy* med försiktiga påståenden. Upptäckten måste verkligen stödjas av beräknad evidens; om detaljer saknas, bygg en verifierbar beräkning eller avstå påståendet.
4. Presentera fynd i befintlig Explore i anslutning till dess analys, med möjlighet att undersöka data bakom påståendet. Undvik dubblerad information.
5. Testa först med syntetiska data, sedan med MetroPT3. Först därefter commit/push.
6. Överväg **Relationship Analysis v0.2** med automatisk villkorad relationsanalys först efter att användarvärdet i det första fyndet är demonstrerat.

## Framtida metoder (behåll som idéer, inte aktuellt implementationsarbete)

- STUMPY / Matrix Profile: återkommande eller ovanliga delsekvenser.
- Vektoriserad MAD: robust avvikelse-/spridningsanalys.
- Batched Isolation Forest: ovanliga multivariata kombinationer.

För alla metoder: domänoberoende, tydlig evidens, inga automatiska kausala slutsatser, lämplighet styrs av dataegenskaper.

## Checklista nästa pass

```powershell
cd C:\Users\User\Dataprodukt
git status -sb
git log -4 --oneline
$env:PYTHONPATH = '.\engine'
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -v
```

Senaste kända fullständiga teststatus: 35/35. Bekräfta på nytt vid behov. Fråga inte om tidigare besvarade arkitekturfrågor; börja med att granska befintlig kod och planera en liten, verifierbar Explore-integrering för *Discoveries v0.1*.
