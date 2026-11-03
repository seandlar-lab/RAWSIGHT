# RAWSIGHT — Data Quality Framework v0.1

**Datum:** 2026-11-03
**Status:** Arkitekturförslag för granskning; ingen exekveringskod ändrad
**Utgångspunkt:** commit `ee6b5af` (senast rapporterad), Quality Findings Summary/Time Structure Evidence v0.3, 166 gröna Python-tester samt genomförda analyser av MetroPT3 och Metro Interstate Traffic Volume.

## 1. Syfte och grundregel

RAWSIGHT ska besvara tre separata frågor:

1. **Data Facts — Vad finns?** Observationer utan kvalitetsvärdering.
2. **Quality Assessment — Vad vet vi om kvaliteten?** Bedömning mot explicita, tillämpliga, versionshanterade regler.
3. **Analysis Suitability — Vad kan datan användas till?** Bedömning relativt en uttryckligen vald analysmetods krav.

**Observerad variation får aldrig i sig konverteras till ett fel.** Frånvaro av kända fel innebär inte att datan är korrekt. Bevara all ursprunglig evidens och redovisa den faktiska täckningen.

### Separata begrepp

- **Fact**: ett mätbart, reproducerbart förhållande, t.ex. `missing_cells = 0` eller `positive_intervals_all_equal = false`.
- **Requirement**: ett deklarerat krav med källa, ansvarig och giltighet, t.ex. att kolumn X måste vara unik.
- **Assessment**: resultatet av att jämföra ett Fact med ett tillämpligt Requirement.
- **Observation descriptor**: neutral, sökbar etikett för sådant som oregelbundenhet, extremvärden och tidsluckor. Inte en kvalitetssanktion.
- **Suitability**: tillämpligheten av data för en *specificerad* metod; inte en generell kvalitetsetikett.

## 2. Standardförankring och avgränsning

- **ISO/IEC 25012:2008**: övergripande modell för datakvalitet i strukturerade system, med 15 egenskaper ur inneboende och systemberoende perspektiv; ISO anger att den bekräftades 2025.
- **ISO/IEC 25024:2015**: mätning av egenskaper enligt 25012. Den **fastställer inte universella gränser för betyg/kvalitetsnivåer** — kontext och behov måste styra.
- **ISO/IEC 5259-2:2024**: modell, mått och rapportering för data inom analys och maskininlärning.
- **ISO/IEC TR 5259-6:2026**: teknisk rapport om visualisering av datakvalitet, relevant vid framtida Understand/Discover-utformning.

**Normativ anspråksnivå:** RAWSIGHT *mappar* egna regler till relevanta standardegenskaper. Denna handling är **inte** en fullständig implementation, certifiering eller konformitetsförklaring. Fulltextlicenser kan krävas för detaljerad normativ mappning.

### 25012-egenskaper (fullständig katalog, inte samma sak som implementerade kontroller)

Accuracy, Completeness, Consistency, Credibility, Currentness, Accessibility, Compliance, Confidentiality, Efficiency, Precision, Traceability, Understandability, Availability, Portability, Recoverability.

RAWSIGHT v0.1 börjar operativt med **Completeness** och **Consistency/Accuracy-relaterad syntaktisk giltighet**, samt med *egna tvärgående observationsbeskrivningar* av tid och fördelning. **Unikhet** är här en RAWSIGHT-regeltyp som kan mappas till konsistens/korrekthet efter kontext; den beskrivs inte som en egen ISO/IEC 25012-egenskap. **Analyslämplighet** är ett eget lager och påstås inte vara en av de 15 egenskaperna.

## 3. Fem bedömningstillstånd

Fältnamn `assessment_status`, med uttömmande enum:

| Kod | Svensk text | Kriterium |
|---|---|---|
| `verified` | Verifierad / krav uppfyllt | Ett **tillämpligt och deklarerat** krav finns, ett komplett giltigt mätunderlag finns, och kravet är uppfyllt. |
| `violation` | Verifierat regelbrott | Ett **tillämpligt och deklarerat** krav finns, relevant tillräcklig evidens finns, och regeln bryts. |
| `observed_variation` | Observerad variation | En konkret mätbar egenskap rapporteras, men ingen kvalitetsvärdering görs. Är **inte** samma sak som `violation`. |
| `insufficient_evidence` | Otillräckligt underlag | En relevant bedömning är önskad eller påbörjad men underlaget räcker inte. Ange orsak. |
| `not_assessed` | Ej bedömd | Ingen giltig bedömning har genomförts, t.ex. därför att ett tillämpligt krav saknas eller kontrollen ännu inte körts. Ange orsak. |

En evidenspost kan ge **flera parallella utsagor** på olika dimensioner. Ett analysområde kan t.ex. ha `verified` fullständighet och `observed_variation` i tidsintervall. Inget globalt betyg och ingen sammanvägd score i v0.1.

**Viktig skillnad:** `positive`/`attention`/`informational`/`insufficient` i befintliga v0.3-JSONL är **motorernas evidensklassificeringar**, inte de fem regelmotorstatusarna. Ingen 1:1-översättning är tillåten. Exempel: `complete_column: positive` betyder observerat noll saknade celler, men `verified` för datakvalitetskravet ”fullständig” kräver att obligatoriskhet/tillämpningsområde har definierats; annars rapporteras faktumet utan en påhittad verksamhetsregel.

## 4. Good, Bad, Ugly — presentationsspråk, inte datamodell

- **Good** kan vara en användarvänlig summering av en eller flera `verified`-bedömningar, alltid med avgränsning.
- **Bad** förutsätter en eller flera `violation`-bedömningar för explicita regler.
- **Ugly** är en valfri explorativ etikett för *observerad komplexitet*, aldrig bevisat fel och aldrig ett automatiskt kvalitetskrav.
- **Unknown** rymmer två skilda typer: `insufficient_evidence` och `not_assessed`, som aldrig får slås ihop tekniskt.

UX ska i första hand visa exakta tillstånd, dimensioner, täckning och evidenslänkar. Good/Bad/Ugly kan användas som informella filter, om det inte skymmer nyanser.

## 5. Kvalitetsregelns kontrakt

Varje regel har minst:

- `rule_id`, `rule_version`, `title_sv`, `description_sv`.
- `dimension`: 25012-mappning eller explicit `rawsight_observation` / `analysis_suitability`.
- `rule_kind`: t.ex. `required_non_null`, `declared_unique`, `allowed_range`, `time_cadence_requirement` eller `observation_only`.
- `scope`: vilka dataset, kolumner, område och tidsspann regeln gäller för; saknas tillämpligt scope -> ingen bedömning.
- `requirement`: en maskinläsbar predikatdefinition **eller null för observation-only**.
- `requirement_source`: användarbeslut, datakontrakt, verksamhetskrav etc. **Måste finnas för kvalitetsvärdering.**
- `measure`: måttets definition och enhet, förväntat evidensfält och utfallskriterium.
- `evaluation_policy`: hantering av noll rader, null, typkonvertering, partiellt underlag och tidsordning.
- `evidence_refs`: exakt sökväg, radnummer, område (`region_id` internt), gränshändelse och/eller mätfält.
- `assessment_status` samt `reason_code`, `explanation_sv`, `assessed_at`, `engine_version`.

Versionsbyte av regel eller ändrat tillämpningsområde får inte retroaktivt skriva om ursprungliga Facts eller tidigare Assessments. Nya bedömningar får ny version.

## 6. Första föreslagna regelkatalogen

| ID | Typ | Uppgift i v0.1 | Gräns för kvalitetsbedömning |
|---|---|---|---|
| DQ-COMP-001 | Fullständighet | Redovisa antal giltiga/saknade värden och täckning för angivna kolumner. | `verified`/`violation` **endast** om obligatoriska kolumner och tillåten frånvaro har deklarerats. |
| DQ-UNIQ-001 | Unikhet | Redovisa förekomst av identiska nyckelvärden inom känt scope. | Kräver deklarerad unik nyckel. Upprepade tidsstämplar utan nyckelkrav är neutrala observationer. |
| DQ-DOM-001 | Domängiltighet | Redovisa förekomst utanför angiven värdemängd eller intervall. | Kräver explicit dokumenterad domänregel. |
| DQ-TIME-001 | Tidsstruktur | Redovisa typiskt/min/max och variation, luckor, lika tidpunkter och ordningscertifiering. | **Observation-only som standard.** Ingen automatisk varning för positiva varierande intervall. |
| DQ-STRUCT-001 | Struktur/typ | Redovisa läsbarhet, typer och konverteringsfel. | `violation` bara mot deklarerad schemaregel; annars faktum. |
| DQ-SUIT-001 | Analyslämplighet | Relatera fakta till *vald* metods förutsättningar. | Avstå om metod saknas. Separat domän, inte ett övergripande datakvalitetsbetyg. |

Första körbara regeln bör vara **DQ-COMP-001**, med en uttrycklig valfri kravprofil. **DQ-TIME-001** är ett rent rapporterings- och tolkningskontrakt tills ett krav på mätfrekvens finns.

## 7. Evidens och täckning

Alla bedömningar ska redovisa:

1. `rows_evaluated`, `source_rows`, `exhaustive`; även vilka kolumner som faktiskt granskats.
2. `source_order_certified`: `false` betyder att slutsatser om *ursprunglig fysisk ordning* inte får presenteras som verifierade.
3. `fact_refs` direkt till ursprungliga JSONL-fynd samt regelns version.
4. `calculation_method` och `aggregation_scope` — jämför aldrig rått antal fynd med antal källfel.
5. `limitations`: vilket kvalitetsanspråk som inte kan göras.

Exempel från MetroPT3: tre mätkolumner har `missing_cells = 0` över 1 516 948 rader. Det är ett verifierat **faktum**; korrekthet, kalibrering och analyslämplighet är fortfarande okända. 331 observerade större tidsluckor ger inga automatiska regelbrott. De 331 korta övergångsområdenas otillräckliga tidsevidens är en metodbegränsning och får inte dubbelräknas som ytterligare källfel.

Exempel från trafikdata: 7 629 upprepade intilliggande tidsstämplar och 103 större observerade luckor är fakta. Det finns ännu ingen dokumenterad regel som gör varje sådan förekomst till ett kvalitetsfel. Från v0.3 återstår 1 137 `attention`-fynd, vars innebörd kräver regelkontext och separat genomgång.

## 8. Föreslaget dataflöde

```
Originalkälla (oförändrad)
      |
      v
Dataset Profile / Quality Region Execution v0.3
      |  JSONL-fakta + områdes- och källreferenser
      v
Facts Adapter (planerad, läser strömmande)
      |  normaliserade fakta, noll omtolkningar
      v
Rule Catalog + Explicit Context/Requirements
      |  predicate + declared scope + requirement source
      v
Quality Assessment Engine (planerad)
      |  statuses + motivering + regelversion + evidens
      v
Understand / Discover (planerad)
      |  tydlig fakta-/bedömningsseparation + fördjupning
      v
Analysis Suitability (planerad, metodberoende)
```

**Execution Monitor** blir ett gemensamt framtida sidokontrakt för progress och resursanvändning, inte en del av kvalitetsklassificeringen.

## 9. Verifieringskrav innan implementering av regelmotorn

1. Inget explicit krav -> **inga** `verified`/`violation`-bedömningar, endast fakta/`not_assessed`.
2. Samma fakta, olika dokumenterade krav -> kan ge olika bedömning utan att fakta ändras.
3. Variation i positiva tidsintervall -> observerad variation, inte automatiskt regelbrott.
4. Upprepade tidsstämplar -> neutrala tills giltig unikhetsregel finns.
5. Varje `violation` måste ha identifierbar regel, version, kravkälla och exakt faktareferens.
6. Ofullständigt underlag -> inga obefogade positiva eller negativa slutsatser.
7. Tvåraders övergångsområde -> får inte dubbelräknas som separat datakällfel.
8. Endast valda kolumner får bedömas; inga globala påståenden om övriga kolumner.
9. Resultat från v0.2/v0.3 förblir läsbara utan tvingad migrering.
10. Storskalig evidens läses strömmande; resultat tillåts vara diskbaserade; ingen dold sampling/trunkering.

## 10. Beslut och nästa steg

**Föreslaget beslut:** godkänn detta som *design baseline* för RAWSIGHT Data Quality Framework v0.1. Ingen ändring i det verifierade `ee6b5af`-checkpointet krävs för att granska förslaget.

Nästa tekniska steg: (a) granska den konkreta fältstrukturen i befintlig JSONL och Dataset Profile, (b) definiera en minimal `Fact`/`Rule`/`Assessment`-JSON-schema, (c) implementera DQ-COMP-001 utan implicit kvalitetskrav, (d) tester mot syntetiska data och båda befintliga evidensfilerna, (e) först därefter andra regler och Understand-vyn.

## Referenser

- ISO/IEC 25012:2008: https://www.iso.org/standard/35736.html
- ISO/IEC 25024:2015: https://committee.iso.org/standard/35749.html
- ISO/IEC 5259-2:2024: https://www.iso.org/standard/81860.html
- ISO/IEC TR 5259-6:2026: https://www.iso.org/standard/86532.html
