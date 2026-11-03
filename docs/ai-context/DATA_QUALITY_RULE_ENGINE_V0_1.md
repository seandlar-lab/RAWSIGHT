# RAWSIGHT – Data Quality Rule Engine v0.1

## Scope
Första deterministiska implementationen av `DQ-COMP-001` enligt designkatalog `DATA_QUALITY_RULE_CATALOG_V0_1.json`.
Ingen kvalitetsbedömning görs automatiskt av `quality_region_execution_v3` eller av den tidigare kvalitetskatalogen. Regeln aktiveras endast när anroparen tillhandahåller ett uttryckligt krav.

### Faktiskt underlag
`quality_evidence_*.jsonl`, poster med `record_type=finding`, `kind=complete_column`, `region_id`, `column`, `evidence.rows`, `evidence.missing`.
Regeln bedömer **en kolumn i ett specificerat analysområde**; inte automatiskt en hel datauppsättning.

### Kravkontrakt
```json
{
  "rule_id": "DQ-COMP-001",
  "rule_version": "0.1.0",
  "column": "TP3",
  "area_id": "region_000000149",
  "max_missing": 0,
  "source": "DEMO ONLY - replaced by a documented business requirement"
}
```
`source` måste ange varifrån ett **faktiskt** kvalitetskrav härrör för produktionsbedömningar. Demokrav får inte presenteras som verkliga verksamhetskrav.

### Resultat
- `not_assessed`: inget krav. Fakta kan ändå redovisas neutralt.
- `verified`: krav finns, komplett direkt observerad evidens finns för samma kolumn och område, och antal saknade värden är inom gränsen.
- `violation`: motsvarande evidens visar fler saknade värden än tillåtet.
- `insufficient_evidence`: tillämpligt krav finns men fullständiga, direkt observerade uppgifter saknas; gäller också tomt område (0 rader).
- `observed_variation`: används **inte** av DQ-COMP-001. Reserverat för neutrala beskrivningar från andra regler.

Felaktiga krav, typfel, logiskt omöjlig evidens och felaktigt matchad omfattning ger `ValueError`, **inte** något av ovanstående kvalitetsomdömen.

### Spårbarhet och avgränsningar
- `evidence_ref` refererar till ursprunglig JSONL och exakt rad (vid strömmad läsning).
- Kravets `source` redovisas separat från evidensens sökväg.
- Indatafyndet lämnas orört; CSV och JSONL ändras inte.
- Strömmad läsning återanvänder befintliga evidensfiler och läser en post åt gången.
- Ett krav som saknar matchande fynd ger `insufficient_evidence` när filen är slut.
- Resultaten är **områdesvisa**. Inga påståenden om global datakvalitet eller alla kolumner.
- Den här v0.1 stöder endast antal saknade värden, inte procentsatströsklar, fältberoenden, schemavalidering, andra DQ-regler eller kravhantering via GUI.
- Regelmotorn är inte ansluten till Tauri/React. Ingen versionändring av befintlig JSONL-evidens krävs.
- Originalfilens fysiska radordning är inte certifierad i befintliga kvalitetsexekveringar; DQ-COMP-001 behöver inte tidsordning.

### Nästa iteration
Inför separat kravprofil per datakälla med versionshanterade och godkända verksamhetskrav, samt metadata som binder krav till datamängd och identifierad analyskörning. Först därefter kan en dataset-övergripande fullständighetsbedömning införas, med explicit kontroll av täckning och kolumner.
