# RAWSIGHT – överlämning 2026-11-01

## Utgångsläge

- Senast bekräftade push före dagens UI-arbete: `57394f5` på `main` (Event Context Similarity v0.1).
- Pythonanalysen Event Context Similarity Execution, tidsavgränsning och metadatafix har verifierats mot MetroPT3. Senast rapporterade Python-testsvit: **83/83 OK**.
- Explore-integrationen Discover → Investigate → Use as reference har installerats lokalt. **`npm run build` och `cargo check` passerade** efter JSX-korrigering.
- Temporal Selection v0.1 har installerats från korrigerat installationspaket. **`npm run build` och `cargo check` passerade** efter installationen.
- Användaren har visat fungerande RAWSIGHT-skärmbilder: Event Similarity finns i Explore, verkliga tidsluckor och mätserievisa jämförelser kan öppnas.
- Inget meddelande i denna session bekräftar att dagens ändringar har committats eller pushats. Kontrollera `git status` före commit.

## Verifierade UX-/analysobservationer

- Med större tidsurval (ca 4–28 april) upptäcktes **44 verifierade gaps och 43 kandidater**, med referensluckan `2020-04-25 01:10:51 → 2020-04-27 01:12:49`.
- Teknisk kolumn `column00` var initialt förvald; den gav artificiellt perfekt formlikhet före en kandidat eftersom övriga signaler var konstanta. Användaren avmarkerade kolumnen och körde om analysen.
- Utan `column00`: kandidatlucka **2020-04-12 01:10:17 → 2020-04-12 04:44:35**: formscore före **0,7195**, efter **0,8230**, **6/6** jämförbara serier per sida, ca **287–288 sekunders** fönster, **30 observationspar** per serie.
- Mätserievis före/efter: TP2 **0,5093/0,9821**; TP3 **0,9993/0,9981**; H1 **0,4245/0,5451**; DV_pressure **0,4085/0,4179**; Reservoirs **0,9993/0,9981**; Oil_temperature **0,9760/0,9970**.
- Efter-händelse-delta, referens/kandidat: TP2 **+4,190/+4,554**; TP3 **+4,310/+4,700**; Reservoirs **+4,314/+4,708**; Oil_temperature **+18,000/+18,350**.
- TP3 och Reservoirs är starkt samvarierande (Pearson cirka 0,999993 i tidigare global analys), så de riskerar dubbelviktning.
- Likhetspoäng är korrelationsbaserad **formlikhet** med observationsindexjustering; det är varken signifikans, orsak eller bevis för identiska tillstånd. Inga saknade observationer interpoleras.

## Produktprinciper

- RAWSIGHT: **Discover → Investigate → Explore Further** i befintliga Explore; varje fynd ska gå att fördjupa och återanvända som ny referens, utan att tappa datakälla/urval.
- Användaren vill välja tidsperiod både **visuellt i grafen** och med **exakta datum/tider**, synkroniserade. Temporal Selection v0.1 är första steg (separat kompakt översikt, inte ännu direkt pensel i huvuddiagrammet).
- En eller flera mätserier, senare flera dataset med explicit tids-/nyckeljustering. Undvik omotiverad automatisk exkludering utifrån kolumnnamn; identifiera tekniska index via dataegenskaper och låt användaren styra.

## Prioriterad fortsättning

1. **Spara lokal fungerande kod först**. Från `C:\Users\User\Dataprodukt`: kör `git status -sb`, `git diff --stat`, `git diff --check`. Granska ändrade filer. Använd **explicit `git add`**, aldrig `git add .`, för att undvika ZIP, `_...`-mappar, `.bak` och `testdata/`.
2. Kontrollera om `Use as reference – rerun analysis` verkligen startar ny beräkning och bevarar urvalet. Det har synts som knapp, men klickbeteendet har inte bekräftats i denna konversation.
3. **Visualisera verkliga före-/efterkurvor överlagrade** för referens och kandidat i Investigate; inkludera tidsskala, täckning och avgränsningar, utan interpolering över gaps.
4. Förbättra evidenskvalitet: tydliggör antal bidragande serier, avvisa/flagga falskt höga poäng från indexliknande eller redundanta kolumner. Undvik att TP3 och Reservoirs okritiskt räknas som oberoende evidens.
5. Verifiera Temporal Selection UX: synkronisering mellan grafurval och tidsfält samt att Event Similarity och Episode Discovery använder avsett intervall. Testa 2020-04-25 00:00:00 till 2020-04-28 00:00:00 (slut exklusivt). Markering direkt i huvudgrafen är framtida förbättring.
6. Upprepa `PYTHONPATH=.\engine` + full unittest-svit, `npm run build`, `cargo check` efter ändringar och `npm run tauri dev` för funktionstest.

## Git – föreslaget arbetssätt

Kör från projektroten:

```powershell
cd C:\Users\User\Dataprodukt
git status -sb
git diff --stat
git diff --check
```

Granska listan med ändrade och nya källfiler, och lägg enbart dem och denna överlämning (`docs/ai-context/RAWSIGHT_SESSION_2026-11-01.md`) i staging. Kontrollera `git diff --cached --stat` före `git commit`, därefter `git push origin main`. Inga exakta `git add`-rader ges här eftersom aktuell lokal status inte har verifierats.
