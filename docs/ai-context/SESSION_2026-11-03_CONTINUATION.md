# RAWSIGHT – Session checkpoint 2026-11-03

## Verifierat nuläge
- Senaste commit: 02f8f60
- main synkroniserad med origin/main
- Python: 179/179 tester godkända
- Quality Findings Summary v0.3 verifierad
- Time Structure Evidence v0.3 verifierad mot MetroPT3 och trafikdata
- Data Quality Framework v0.1 etablerat
- DQ-COMP-001 implementerad och testad mot verklig evidens

## Beslutade arkitekturprinciper
- Data Facts och Quality Assessment hålls åtskilda
- ISO/IEC 25012, 25024 och relevanta delar av 5259-serien
- Bedömningar: verified, violation, observed_variation,
  insufficient_evidence och not_assessed
- Inga kvalitetsomdömen utan tillämpliga regler och evidens
- Ingen automatisk likställning av ovanliga data med dåliga data
- Ingen tyst begränsning av analysens datatäckning
- Svensk terminologi: analysområde, inte region

## Produktvision
RAWSIGHT ska hjälpa användaren att förstå:
1. Vad har jag för data?
2. Vad betyder de?
3. Hur bra är de?
4. Vad kan jag använda dem till?

## Ny långsiktig förmåga: Cross-Dataset Discovery
RAWSIGHT ska kunna kombinera och jämföra flera datamängder.

Exempel:
- Referensdata: väderobservationer
- Mätdata: sensorvärden, energiförbrukning eller trafikflöden

Möjliga analyser:
- Samvariation och korrelation
- Tidsförskjutna samband
- Gemensamma förändringar
- Avvikelser som inte förklaras av observerade samband

Förutsättningar:
- Tidssynkronisering och tidsupplösning
- Geografisk jämförbarhet
- Enhetskonvertering
- Datakvalitet och proveniens
- Saknade observationer och osäkerhet
- Korrelation får inte förväxlas med kausalitet

Referensdata ska inte automatiskt betraktas som felfria.

## Nästa utvecklingssteg
Quality Requirements Profile v0.1:
- Kravprofil per datamängd
- Krav per kolumn och analysområde
- Kravkälla, version och giltighet
- Konflikthantering
- Integration med DQ-COMP-001

Därefter:
- Understand-vyn
- Execution Monitor med progress och resursinformation
- Cross-Dataset Discovery i senare utvecklingsfas

## Arbetsprincip
Utveckla stegvis. Verifiera mot riktiga data.
Inga ogrundade kvalitetsbedömningar.
Inga påhittade samband eller problem i materialet.
