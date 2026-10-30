# RAWSIGHT – utvecklingsöverlämning och nästa arbetsplan

**Datum:** 2026-10-30  
**Avsett mål i repository:** `docs/ai-context/HANDOFF_2026-10-30.md`  
**Status:** Sammanställning av genomgång, lokala testutskrifter och gemensamt beslut om analysriktning.  
**Viktigt:** Denna fil har skapats utanför användarens lokala Git-repository. Ingen commit eller push har gjorts. Fakta i avsnittet *Verifierat* bygger på kodutdrag, terminalutskrifter och skärmbilder som användaren visat; andra slutsatser är uttryckligen markerade.

## 0. LÄS DETTA FÖRST – var vi ska fortsätta

**RAWSIGHTs mål är inte att enbart upptäcka luckor eller avvikande värden.** Systemet ska automatiskt identifiera datastruktur, återkommande mönster, samvariation och avvikande relationer, välja relevanta analyser och presentera evidens samt lämpliga visualiseringar.

**Överenskommen analysordning:**

1. **Structure & data quality:** Identifiera tidsaxel, observationernas ordning och täthet, NULL/ogiltiga värden samt tidsluckor.
2. **Cross-series gap analysis:** Avgör om ett avbrott gäller hela insamlingen (saknade rader), enskilda mätvärden (saknade/giltiga kolumnvärden) eller grupper av signaler. Samma uppehåll i alla signaler är ett *gemensamt observationsuppehåll*, inte bevis för flera sensorfel eller en känd driftorsak.
3. **Före/efter-jämförelse:** Jämför signalernas nivåer, spridning, trender och relationer på båda sidor om luckan. Behandla resultat som deskriptiv evidens, inte automatiskt kausalitet.
4. **Individuell anomalidetektion (per kolumn/tidsserie):** Punktavvikelser, kontextuella avvikelser, nivåskiften, trend- och variansförändringar, kollektiva mönster. Utgå från robusta baslinjer och drift-/tidskontext.
5. **Rad-/tvärserieanalys:** Jämför anomalier vid gemensamma tidpunkter, samtidighet, förskjutningar, korrelation och samvariation. Identifiera isolerade, gemensamma och relationsbaserade anomalier.
6. **Multivariat struktur:** Undersök korrelations-/kovariansmatriser, PCA, residualer och avvikelse från inlärda relationer där dataförutsättningarna motiverar det.
7. **Evidensbaserad tolkning och automatisk visualisering:** Presentera observation, beräknad indikation, osäkerhet och hypotes tydligt åtskilda; välj t.ex. tidsserie, heatmap, korrelationsmatris, scatterplot eller PCA-vy.

**Omedelbart nästa utvecklingsmoment:** Använd det verkliga 48-timmarsintervallet i MetroPT3 för **cross-series presence / gap analysis**. Undersök om hela datarader saknas respektive om vissa kolumner saknar giltiga värden. Jämför sedan före/efter. Först därefter byggs den individuella och multivariata anomalidetektionen ut. **Låt inte en kosmetisk diskussion om linjebrytning tränga undan denna ordning.**

## 1. Systemkontext och arkitektur

- Repository: `https://github.com/seandlar-lab/RAWSIGHT`
- Etablerad kontext finns i `docs/ai-context/PROJECT.md`, `ARCHITECTURE.md`, `STATE.md`, `NEXT.md`. Läs dessa samt denna överlämning vid ny session; kontrollera även Git HEAD och arbetskatalog så att dokumentationen inte misstas för aktuell Git-status.
- Frontend: React/TypeScript; Tauri/Rust som kommandobrygga; Python-analysmotor i `engine/`; DuckDB via `SourceExecutionContext`.
- Exempel på etablerad brygga: React (anrop inte end-to-end-verifierat) → Tauri `explore_cross_series_presence` (`app/src-tauri/src/lib.rs`) → Python CLI `cross-series-presence-context` (`engine/profile.py`) → `analyze_cross_series_presence` (`engine/rawsight/cross_series_presence.py`).
- Tauri-anropet använder `path`, `temporal_axis_json`, `start_time`, `end_time`. Python validerar en vertikal temporal axel, öppnar `SourceExecutionContext` och anropar analysfunktionen.
- Princip: *Detect → Normalize → Analyze → Visualize*. Återanvänd identifierad temporal struktur; kör inte om detektion i presentationslagret.

## 2. Bekräftad status 2026-10-30

### 2.1 Tester och korrigering K4

Användaren körde följande i sin Windows/ARM-miljö, från `C:\Users\User\Dataprodukt`:

```powershell
$env:PYTHONPATH = '.\engine'
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -v
```

**8 av 8 befintliga enhetstester gick igenom** (4 för `cross_series_presence`, 4 för `temporal_gap_comparison`; körtid 0,256 s). Utskriften visade alla testfall som `ok`; den avslutande `OK`-raden var inte med i just det delade terminalutdraget, men inga fel visades.

Ett särskilt femfallstest av `analyze_long_temporal_axis()` gav **före fix** `UnboundLocalError` för tom serie, en observation, dubbla tidsstämplar och fallande tidsstämplar; en normal serie fungerade.

**K4-korrigering gjord lokalt** i `engine/rawsight/long_temporal.py`, vid rad ~337: flyttat initialiseringen `retained_largest_intervals = []` från åtta till fyra indragna blanksteg så att den står på samma nivå som följande `for`-loop. `git diff` bekräftade endast denna radförändring för filen. Efter ändringen gav samma fem gränsfall:

```text
tom OK 0
en_observation OK 0
dubbla_tider OK 0
fallande_tider OK 0
normal_serie OK 2
```

K4:s tidigare undantag är därmed **reproducerat och avhjälpt i lokal kod**. Testerna verifierar inte full semantisk korrekthet för alla randfall. **Ingen commit/push är rapporterad för denna fix.** Git varnade också att CRLF kan konverteras till LF; den varningen är inte ett testfel.

### 2.2 Temporal Gap Comparison

`engine/rawsight/temporal_gap_comparison.py`, `analyze_temporal_gap_comparison(source_context, temporal_axis, gap_start, gap_end, observations_per_side=100)`:

- Kräver giltiga och stigande luckgränser, begränsar antalet observationer per sida till 1–10 000.
- Väljer de senaste N raderna vid/före `gap_start` respektive första N vid/efter `gap_end` (DuckDB); identifierar numeriska kolumner och beräknar giltigt antal, medelvärde, populationsstandardavvikelse, min, max och `mean_delta` per kolumn.
- Interpolerar inte värden i luckan. Resultatkontraktet anger uttryckligen begränsningar.
- **4/4 befintliga enhetstester godkända lokalt**, men detta är inte end-to-end-verifiering.
- `git grep -n temporal_gap_comparison` gav referenser endast i modul och tester; ingen direkt integration i `engine/profile.py`, Tauri eller frontend identifierades. Dynamiska anrop har inte uteslutits fullständigt.
- Dokumenterade begränsningar: `status=measured` betyder rader på båda sidor, inte nödvändigtvis giltiga värden för varje kolumn; lika många observationer ger inte lika långa tidsperioder; dubbla tidsstämplar saknar entydig ordning; före/efter-skillnader är inte kausal evidens.

### 2.3 Kontinuitets- och visualiseringskedja

- `long_temporal_series_execution.py` väljer `continuity_evidence` via `_select_detail_continuity_evidence`, som filtrerar de befintliga `continuity['largest_positive_intervals']` med överlappning mot begärt intervall. Funktionen detekterar inte nya luckor.
- Resultatet returnerar **både** `continuity_evidence` och `display_projection`, även i normalt resultat med `status='measured'`.
- Detaljanalysen arbetar mot ursprunglig datakälla (inte översiktsprojektion), filtrerar giltiga numeriska värden med `ISFINITE`, och väljer `exact_observations` om antalet giltiga observationer ryms inom `point_limit` (standard 1000 i granskad signatur). Större datamängder projiceras/extremvärdesreduceras.
- I `exact_observations` sätts **alltid** `break_before: False` på datapunkterna.
- Bucketprojektioner beräknar `break_before` från hopp i bucketindex; de bryter därmed vid vissa tomma buckets, inte nödvändigtvis baserat på samma semantik som tidigare kontinuitetsanalys.
- `LongTemporalSeriesChart.tsx` för vidare `break_before` som `breakBefore` till `TimeSeriesChart.tsx`. Där körs `flushSegment()` när `point.breakBefore` är sant, eller om värdet saknas/är icke-finit.
- **Kodmässig inkonsekvens bekräftad:** Exact-läget saknar avbrottsmarkering, medan bucketläget kan bryta vid tomma buckets. Detta är inte samma sak som att samtliga appdiagram visar fel.
- `largest_positive_intervals` är ett *begränsat urval av de största positiva observationsavstånden*, inte en uttömmande lista över klassificerade avbrott. Det räcker inte ensamt som generellt facit för alla `break_before`.

### 2.4 Visuell verifiering i RAWSIGHT-appen

- Appen startade via `cd app; npm run tauri dev` och renderade Temporal overview/detail.
- Dataset: **MetroPT3 (AirCompressor)**; vald kolumn i skärmbilderna **TP2**.
- I appen visades `Usable observations 1 516 948`, översiktsprojektion `time_bucketed_extrema`, `Display points 976`.
- Temporal continuity visade: tidsfält `timestamp`, observerad ordning `strictly_increasing`, dominerande positivt intervall **10 s**, andel vid dominerande intervall **88,2 %**, **337** distinkta positiva intervall, frekvensanalys komplett och *Canonical order established: No*.
- Största visade positiva intervallet: **48,0 timmar**, från **2020-04-25T01:10:51** till **2020-04-27T01:12:49** (tidsskillnad 48 h 1 min 58 s). Det är ett observerat avstånd mellan registrerade tidsstämplar; orsaken är okänd.
- Skärmbilder från ett detaljintervall över slutet av april visade ett tomt område mellan grupper av datapunkter i en reducerad projektion. Det är *förenligt med* korrekt avbrottsrendering där, men ett kontrollerat UI-test av exact-läget med samma gap har inte utförts.

### 2.5 Git / arbetskatalog

Senast delade `git status -sb` före K4-fixen visade:

```text
## main...origin/main
 M engine/rawsight/long_temporal_execution.py
?? testdata/
```

Efter K4-fixen är även `engine/rawsight/long_temporal.py` lokalt modifierad. Kontrollera alltid färsk `git status -sb` och `git diff` innan commit. `long_temporal_execution.py` och `testdata/` fanns sedan tidigare och ska **inte** återställas eller läggas till utan att deras innehåll först förstås. En tidigare `git push` synkroniserade `main` till `origin/main` enligt användarens terminalutskrift, men aktuell HEAD är inte återverifierad i denna överlämning.

## 3. Beslutad analyssemantik – håll dessa begrepp isär

1. **Radnärvaro:** En tidsstämplad datarad finns över huvud taget i källan.
2. **Giltigt värde per mätserie:** Raden finns, men varje kolumn kan vara NULL/NaN/icke-finit. Det är inte samma sak som saknade datarader.
3. **Observerat tidsavstånd:** Avståndet mellan två observationers tidsstämplar – matematiskt faktum, inte automatiskt anomali.
4. **Klassificerat kontinuitetsavbrott:** Ett tidsavstånd som efter explicit, evidensbaserat kriterium bedöms som avbrott (exempelvis relation till förväntad kadens/driftfas).
5. **Visuell linjebrytning:** Presentation av ett avbrott; ska inte vara den algoritm som bestämmer om avbrottet finns.
6. **Statistisk anomali:** Ett mätvärde, tidsmönster eller samband som avviker från relevant baslinje, oberoende av saknad data.
7. **Hypotes om orsak:** Gemensamt stopp i loggning, maskin avstängd, sensorfel etc. är *möjliga förklaringar* tills metadata eller driftloggar ger stöd.

**Datagranskningsprincip:** En tidslucka som syns i en gemensam timestamp-kolumn och helt saknar rader betyder per definition att ingen av kolumnerna har registrerade värden under just intervallet i *den datakällan*. Att be flera mätkolumner bekräfta samma radlucka ger då inte oberoende evidens för driftsorsaken. Det verkligt kompletterande testet är att undersöka värdegiltighet i befintliga rader före/efter, jämföra separata källor om sådana finns samt analysera förändrade relationer.

## 4. Nästa exekverbara plan – utan att fastna i UI

### Fas A: Färdigställ Cross-Series Gap Analysis med befintlig kod

**Referensfall A1:** MetroPT3 / TP2, observerat intervall `2020-04-25T01:10:51` → `2020-04-27T01:12:49`.

1. Verifiera från DuckDB/originaldata att det verkligen saknas *rader strikt mellan* dessa två timestamps. Kontrollera även om mätkolumner har NULL eller ogiltiga värden i fönster före och efter.
2. Inventera vilka resultat `cross_series_presence` kan producera för ett valfritt tidsintervall. Notera särskilt att ett helt radtomt intervall inte kan ge per-kolumnnärvaro och att samma tidsaxel kan delas av många kolumner.
3. Jämför närvaro över tre tidsfönster: före, inne i gapet, efter. Redovisa `row_count` och `valid_count` per kolumn samt täckningsgrad när en meningsfull nämnare finns.
4. Kör `temporal_gap_comparison` direkt på samma gapgränser (fristående Python-funktion, ännu inte appintegrerad). Verifiera medelvärden, spridning och valid_count före/efter; skilj nivåskillnader från möjliga driftlägesförändringar.
5. Dokumentera ett minimalt strukturerat resultat: `gap`, `row_presence`, `column_presence`, `before_after`, `interpretation`, `limitations`, `evidence`.
6. Skapa små reproducerbara referensfall för (a) global radlucka, (b) selektiv NULL-lucka, (c) gruppvis värdebortfall, (d) oförändrat/ändrat beteende efter lucka.

**Definition of done (Fas A):** RAWSIGHT kan för ett identifierat gap redogöra för vilka observationer som saknas, vilka mätvärden som är giltiga i närliggande fönster, om förändringar syns efteråt och vad som inte kan slutsatsbestämmas. Inga påståenden om maskindrift utan extern evidens.

### Fas B: Individuell anomalidetektion

- Varje numerisk kolumn analyseras mot lämplig baslinje och, när möjligt, mot jämförbar tids-/driftkontext.
- Kandidatmått: robust läge/spridning (median/MAD med skydd för MAD=0), distributionens svansar, nivåskiften, segmenttrend, lokala residualer, förändrad varians och periodiska mönster.
- Markera observations-/värdebortfall separat från numeriska avvikelser.
- Resultat per observation/segment: signal, metod, score, referensperiod, typ, styrka, antal giltiga datapunkter och begränsningar.
- **Ingen metod ska väljas generellt utan dataprofilering:** periodiska, diskreta, starkt autokorrelerade och multisystemiska signaler kräver olika referenser.

### Fas C: Tvärserie- och radbaserad anomalijämförelse

- För tidsmässigt samordnade observationer: anomalimatris (tid × variabel), samtidighet och laggade samband, gruppmönster och isolerade signaler.
- Standardisera/normalisera med hänsyn till mätstorhet och robust variabilitet; hantera missingness explicit.
- Identifiera **relationsavvikelser**: t.ex. TP3 ökar utan normal motsvarande förändring i Oil, även om båda enskilda värden ligger inom sina vanliga intervall.
- Utvärdera korrelation, kovarians, PCA/subspace-residualer och relevanta begränsningar vid brus, driftfaser och saknade värden.
- Begreppet *rad* betyder gemensam observation endast när datans orientering och synkronisering faktiskt stöder det; undvik att blanda observationsrader med tidsoberoende poster.

### Fas D: Evidens och automatisk visualisering

- Dela upp resultaten i **observerat faktum → beräknad indikation → möjlig hypotes**.
- Föreslå visualisering efter typ av fynd: tidsserie med luckor, närvaromatris, anomalimatris, korrelationsheatmap, scatterplot, PCA-vy och förändringspunkter.
- Dokumentera datatäckning, osäkerhet och varför analysmetoden valts. AI/RAG kan senare hjälpa till med frågor och förklaringar, men får inte ersätta numerisk evidens.

## 5. Tekniska sidospår och prioritering

**Att åtgärda utan att förlora huvudspåret:**

- **K1–K3:** Konsolidera kontinuitetssemantik och `break_before` över exact- och bucketprojektioner. Kräver separat specifikation och regressionstest. Detta är ett legitimt presentations-/datakontraktsproblem, men **inte blockerande för den fristående cross-series gap-analysen**.
- **K4:** Lokalt korrigerat och testat; inväntar commit samt eventuellt ett varaktigt regressionstest för de fem randfallen.
- Kontrollera ordningssemantik (`relation_scan` vs canonical order), dubletter och urvalets determinism.
- `temporal_gap_comparison` är ännu inte integrerad i kommandorouter/Tauri/UI. Behöver inte integreras förrän analysens kontrakt och kvalitetskrav är klara.
- Undersök prestanda på stora dataserier först när riktade fall är korrekta.

## 6. Kommandon för att återuppta sessionen

```powershell
cd C:\Users\User\Dataprodukt
git status -sb
git diff -- engine/rawsight/long_temporal.py
git diff -- engine/rawsight/long_temporal_series_execution.py
$env:PYTHONPATH = '.\engine'
.\.venv\Scripts\python.exe -m unittest discover -s engine/tests -v
```

**Fortsätt sedan direkt med Fas A – Cross-Series Gap Analysis för 48-timmarsintervallet.** Återupprepa inte hela `break_before`-granskningen om inte nya tester visar att den är nödvändig.

## 7. Evidensnivå och öppna frågor

- **Verifierat genom användarens terminal:** 4/4 + 4/4 Python-enhetstester; fem riktade kontinuitetsfall passerade efter K4-fix; diffens enda radändring i `long_temporal.py`; Git-sökningar efter funktionsreferenser.
- **Verifierat genom delade kodutdrag:** huvudgränssnitt, SQL-urval och returstruktur i gap comparison; kontinuitetsevidens i detaljresultat; `break_before` i exact och bucket; frontendens segmentbyggare.
- **Observerat i användarens appskärmbilder:** MetroPT3-statistik, valt signalnamn, visualiserad översikt/detalj och stora observationsavstånd. Full instrumenterad end-to-end-körning ej utförd.
- **Kräver ytterligare test:** Det exakt valda 48-timmarsintervallets radantal, per-kolumnvärdegiltighet, före/efter-struktur, om `break_before` ger ett felaktigt linjesegment i exact-läget, fullständigt resultatkontrakt för nya sammansatta analyser, aktuell HEAD/status efter sista ändringen.
- **Antaganden/hypoteser, inte fakta:** Uppehållet beror på att maskinen var avstängd; all datainsamling stoppade av samma fysiska orsak; efterföljande förskjutningar indikerar ett faktiskt fel. Sådana tolkningar kräver stöd.

---

**Kort återstartsinstruktion till en ny ChatGPT-session:**

> Fortsätt RAWSIGHT från `docs/ai-context/HANDOFF_2026-10-30.md` och de fyra grundfilerna i samma mapp. K4 är lokalt fixat och 8 enhetstester + 5 manuella gränsfall har passerat. Vi har redan granskat `break_before` och visualiserat en stor tidslucka. Återgå nu till huvudmålet: Cross-Series Gap Analysis för MetroPT3:s 48-timmarsuppehåll 25–27 april 2020, därefter före/efter-analys, individuell anomalidetektion per mätserie och tvärserie-/PCA-analys. Skilj radbortfall från kolumnvärdebortfall och observation från hypotes. Börja med att kontrollera aktuell Git-status och sedan konkret analys av befintliga data; undvik lång repetition.
