import "./UnderstandOverview.css";

export type UnderstandColumn = {
  name: string;
  type: string;
  null_count: number | null;
};

export type UnderstandProfile = {
  file: string;
  rows: number;
  column_count: number;
  missing_values: number | null;
  duplicate_rows: number | null;
  columns: UnderstandColumn[];
  analysis_strategy?: { strategy: string };
};

type Props = {
  profile: UnderstandProfile | null;
  fileName?: string | null;
  loading?: boolean;
  onOpenAnalysis: () => void;
  onExplore: () => void;
};

const count = (value: number) => value.toLocaleString("sv-SE");

export function UnderstandOverview({
  profile,
  fileName,
  loading = false,
  onOpenAnalysis,
  onExplore,
}: Props) {
  if (!profile) {
    return (
      <section className="rs-understand" aria-labelledby="rs-understand-title">
        <header className="rs-understand-intro">
          <p className="rs-understand-eyebrow">UNDERSTAND · FÖRSTA INTRYCKET</p>
          <h2 id="rs-understand-title">Vad har vi här?</h2>
          <p>Det finns ingen inläst dataprofil ännu. Börja med att läsa in eller skapa en profil.</p>
        </header>
        <button type="button" onClick={onOpenAnalysis} disabled={loading}>
          {loading ? "Läser in profil…" : "Öppna Light Analysis"}
        </button>
      </section>
    );
  }

  const columns = profile.columns ?? [];
  const measuredColumns = columns.filter(
    (column) => typeof column.null_count === "number" && Number.isFinite(column.null_count),
  );
  const missingColumns = measuredColumns.filter((column) => (column.null_count ?? 0) > 0);
  const fullyObservedColumns = measuredColumns.filter((column) => column.null_count === 0);
  const unknownColumns = Math.max(0, profile.column_count - measuredColumns.length);
  const hasMissingCount = typeof profile.missing_values === "number";
  const duplicateCount = profile.duplicate_rows;

  return (
    <section className="rs-understand" aria-labelledby="rs-understand-title">
      <header className="rs-understand-intro">
        <p className="rs-understand-eyebrow">UNDERSTAND · DATAFAKTA</p>
        <h2 id="rs-understand-title">Så här ser dina data ut.</h2>
        <p className="rs-understand-subtitle">{fileName || profile.file || "Aktuell datamängd"}</p>
        <p>Det här är vad den sparade dataprofilen visar. Inga kvalitetsomdömen har lagts till.</p>
      </header>

      <div className="rs-understand-metrics" aria-label="Översikt över datamängden">
        <div className="rs-understand-metric">
          <span>Rader</span>
          <strong>{count(profile.rows)}</strong>
        </div>
        <div className="rs-understand-metric">
          <span>Kolumner</span>
          <strong>{count(profile.column_count)}</strong>
        </div>
        <div className="rs-understand-metric">
          <span>Saknade värden</span>
          <strong>{hasMissingCount ? count(profile.missing_values as number) : "Ej uppmätt"}</strong>
        </div>
        <div className="rs-understand-metric">
          <span>Likadana rader utöver första förekomsten</span>
          <strong>{duplicateCount === null ? "Ej uppmätt" : count(duplicateCount)}</strong>
        </div>
      </div>

      <div className="rs-understand-panels">
        <article className="rs-understand-panel">
          <p className="rs-understand-eyebrow">DET VET VI</p>
          <h3>Fullständighet, som den är uppmätt</h3>
          <p>
            {measuredColumns.length > 0
              ? `${count(fullyObservedColumns.length)} av ${count(measuredColumns.length)} kontrollerade kolumner saknar nullvärden.`
              : "Det finns inga kolumnvisa mätvärden för saknade värden i profilen."}
          </p>
          {missingColumns.length > 0 && (
            <details>
              <summary>Visa kolumner med saknade värden ({count(missingColumns.length)})</summary>
              <ul>
                {missingColumns.map((column) => (
                  <li key={column.name}>{column.name}: {count(column.null_count as number)} saknade</li>
                ))}
              </ul>
            </details>
          )}
          {unknownColumns > 0 && <p className="rs-understand-note">{count(unknownColumns)} kolumner saknar en sådan mätning i profilen.</p>}
          <p className="rs-understand-note">Nullvärden är inte samma sak som alla former av saknad eller felaktig information.</p>
        </article>

        <article className="rs-understand-panel">
          <p className="rs-understand-eyebrow">DET HAR VI INTE AVGJORT</p>
          <h3>Är datan tillförlitlig?</h3>
          <p>En dataprofil visar struktur och uppmätta egenskaper. Den bevisar inte att innehållet är korrekt.</p>
          <p className="rs-understand-note">Inga godkända kvalitetskrav eller bedömningar är kopplade till den här vyn ännu.</p>
        </article>
      </div>

      <div className="rs-understand-actions">
        <button type="button" onClick={onExplore}>Undersök data i Explore</button>
        <button type="button" className="rs-understand-secondary" onClick={onOpenAnalysis}>Visa teknisk dataprofil</button>
      </div>
      <p className="rs-understand-footnote">Källa: sparad Dataset Profile (Light Analysis). Denna vy gör inga nya beräkningar och ändrar inte datakällan.</p>
    </section>
  );
}
