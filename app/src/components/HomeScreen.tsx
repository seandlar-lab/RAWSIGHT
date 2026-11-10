import { useState } from "react";
import "./HomeScreen.css";

export type HomeProject = {
  id: string;
  name: string;
  path: string;
  updatedAt: string;
};

type Props = {
  projects: HomeProject[];
  projectRoot: string | null;
  onOpenDataset: () => void;
  onOpenProject: (project: HomeProject) => void;
  onChangeProjectRoot: () => void;
  onExit: () => void;
  busy: boolean;
  progressMessage: string;
  error: string | null;
};

function projectDate(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString("sv-SE");
}

function FolderIcon() {
  return <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6.5a2 2 0 0 1 2-2h4l2.2 2.3H19a2 2 0 0 1 2 2V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>;
}
function DataIcon() {
  return <svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/></svg>;
}
function HomeIcon() {
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1z"/></svg>;
}
function SettingsIcon() {
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10 3h4l.6 2.1a7 7 0 0 1 1.6.9l2.1-.6 2 3.5-1.6 1.5a8 8 0 0 1 0 1.8l1.6 1.5-2 3.5-2.1-.6a7 7 0 0 1-1.6.9L14 20h-4l-.6-2.1a7 7 0 0 1-1.6-.9l-2.1.6-2-3.5 1.6-1.5a8 8 0 0 1 0-1.8L3.7 9.3l2-3.5 2.1.6a7 7 0 0 1 1.6-.9z"/><circle cx="12" cy="11.5" r="2.8"/></svg>;
}
function WaveArtwork() {
  return <svg className="rs3-wave" viewBox="0 0 690 250" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="rs3-wave-back" x1="0" y1="0" x2="0.9" y2="1"><stop offset="0" stopColor="#a1c7ff" stopOpacity=".86"/><stop offset="1" stopColor="#d4e4fc" stopOpacity=".34"/></linearGradient><linearGradient id="rs3-wave-front" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#d5e7ff" stopOpacity=".7"/><stop offset=".48" stopColor="#82b1f6" stopOpacity=".74"/><stop offset="1" stopColor="#e5eefb" stopOpacity=".5"/></linearGradient></defs>
    <path d="M0 248 C70 247 94 168 150 178 C208 189 231 244 283 197 C328 155 337 26 395 47 C438 64 448 150 482 115 C525 67 543 -1 588 28 C639 62 652 115 690 97 L690 250 Z" fill="url(#rs3-wave-back)" />
    <path d="M0 250 C67 248 94 224 146 215 C202 204 216 158 273 181 C319 200 348 242 396 180 C447 114 459 98 507 133 C557 169 562 214 611 174 C643 150 669 155 690 164 L690 250 Z" fill="url(#rs3-wave-front)" opacity=".67" />
  </svg>;
}

export function HomeScreen({ projects, projectRoot, onOpenDataset, onOpenProject, onChangeProjectRoot, onExit, busy, progressMessage, error }: Props) {
  const [showProjectRoot, setShowProjectRoot] = useState(false);
  const [showAllProjects, setShowAllProjects] = useState(false);
  const [projectDetails, setProjectDetails] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const uniqueProjects = Array.from(new Map(projects.map((project) => [project.path || project.id, project])).values())
    .sort((a, b) => (Date.parse(b.updatedAt) || 0) - (Date.parse(a.updatedAt) || 0));
  const visibleProjects = showAllProjects ? uniqueProjects : uniqueProjects.slice(0, 3);

  function showProjects() {
    setShowSettings(false);
    setShowAllProjects(true);
    setProjectDetails(null);
  }

  return (
    <div className="rs3-shell">
      <aside className="rs3-sidebar" aria-label="Huvudmeny">
        <div className="rs3-brand"><span className="rs3-brand-symbol" aria-hidden="true"/><span>RAWSIGHT</span></div>
        <nav className="rs3-navigation" aria-label="Startmeny">
          <button type="button" className={!showSettings ? "rs3-nav rs3-nav-active" : "rs3-nav"} onClick={() => { setShowSettings(false); setShowAllProjects(false); setProjectDetails(null); }}><HomeIcon/>Start</button>
          <button type="button" className={showAllProjects && !showSettings ? "rs3-nav rs3-nav-active" : "rs3-nav"} onClick={showProjects}><FolderIcon/>Projekt</button>
          <button type="button" className={showSettings ? "rs3-nav rs3-nav-active" : "rs3-nav"} onClick={() => { setShowSettings((value) => !value); setProjectDetails(null); }} aria-expanded={showSettings}><SettingsIcon/>Inställningar</button>
        </nav>
        <div className="rs3-sidebar-bottom">RAWSIGHT <span>· lokalt datamaterial</span></div>
      </aside>
      <div className="rs3-main">
        <header className="rs3-topline"><span className="rs3-topline-label">RAWSIGHT</span><button type="button" className="rs3-power" onClick={onExit} aria-label="Avsluta RAWSIGHT" title="Avsluta RAWSIGHT">⏻</button></header>
        <div className="rs3-content">
          {showSettings ? (
            <section className="rs3-settings">
              <div className="rs3-kicker">RAWSIGHT</div><h1>Inställningar</h1><p>Inställningar för projekt och lokal datalagring.</p>
              <div className="rs3-settings-card"><strong>Projektplats</strong><div className="rs3-settings-path" title={projectRoot || ""}>{projectRoot || "Ingen projektplats angiven"}</div><button type="button" onClick={onChangeProjectRoot} disabled={busy}>Ändra projektplats</button></div>
              <button type="button" className="rs3-text-link" onClick={() => setShowSettings(false)}>← Till startsidan</button>
            </section>
          ) : (
            <>
              {!showAllProjects && <section className="rs3-hero" aria-label="Välkommen till RAWSIGHT">
                <WaveArtwork/>
                <div className="rs3-hero-copy"><h1>The good, the bad and<br/>the ugly of your data.</h1><p>Discover what your data can tell you.</p></div>
              </section>}
              {!showAllProjects && <section className="rs3-actions" aria-label="Börja arbeta">
                <button type="button" className="rs3-action rs3-action-primary" disabled={busy} onClick={onOpenDataset}><span className="rs3-action-symbol" aria-hidden="true">＋</span><span className="rs3-action-copy"><strong>Utforska nytt datamaterial</strong><small>CSV, Excel eller Parquet</small></span><span className="rs3-arrow" aria-hidden="true">→</span></button>
                <button type="button" className="rs3-action" disabled={busy || uniqueProjects.length === 0} onClick={showProjects}><span className="rs3-action-symbol" aria-hidden="true"><FolderIcon/></span><span className="rs3-action-copy"><strong>Öppna projekt</strong><small>{uniqueProjects.length ? "Fortsätt med ett tidigare Datalandskap" : "Inga sparade projekt ännu"}</small></span><span className="rs3-arrow" aria-hidden="true">→</span></button>
              </section>}
              {busy && <div className="rs3-progress" role="status" aria-live="polite"><span className="rs3-spinner" aria-hidden="true"/><span><strong>RAWSIGHT arbetar</strong><small>{progressMessage || "Förbereder arbete"} · tidsåtgång okänd</small></span></div>}
              {error && <div className="rs3-error" role="alert"><strong>Något gick fel</strong><p>{error}</p></div>}
              <section className={showAllProjects ? "rs3-recents rs3-recents-all" : "rs3-recents"} id="rs3-recents">
                <div className="rs3-section-header">
                  <div>
                    {showAllProjects && <p className="rs3-kicker">RAWSIGHT / PROJEKT</p>}
                    <h2>{showAllProjects ? "Öppna projekt" : "Fortsätt där du slutade"}</h2>
                    {showAllProjects && <p className="rs3-section-description">Välj ett tidigare projekt. Projekt med samma namn kan ha olika innehåll.</p>}
                  </div>
                  {showAllProjects ? <button type="button" className="rs3-text-link" onClick={() => { setShowAllProjects(false); setProjectDetails(null); }}>← Till startsidan</button>
                    : uniqueProjects.length > 3 ? <button type="button" className="rs3-text-link" onClick={showProjects}>Visa alla ({uniqueProjects.length})</button>
                    : <span>Senaste projekt</span>}
                </div>
                {uniqueProjects.length === 0 ? <div className="rs3-empty">Dina sparade projekt visas här.</div> : <div className="rs3-project-list">
                  {visibleProjects.map((project, index) => {
                    const key = project.path || project.id;
                    const expanded = projectDetails === key;
                    const repeatedName = uniqueProjects.filter((item) => item.name === project.name).length > 1;
                    return <div key={key} className="rs3-project-entry">
                      <div className={`rs3-project ${index === 0 && !showAllProjects ? "rs3-project-first" : ""}`}>
                        <span className="rs3-project-symbol"><DataIcon/></span>
                        <span className="rs3-project-info"><strong title={project.name}>{project.name}</strong><small>{projectDate(project.updatedAt) ? `Uppdaterat ${projectDate(project.updatedAt)}` : "Sparat projekt"}{repeatedName ? " · Flera projekt har detta namn" : ""}</small></span>
                        <div className="rs3-project-controls">
                          <button type="button" className="rs3-project-detail-toggle" aria-expanded={expanded} aria-label={`Visa detaljer för ${project.name}`} title="Visa projektinformation" onClick={() => setProjectDetails(expanded ? null : key)}>{expanded ? "⌃" : "ⓘ"}</button>
                          <button type="button" className="rs3-project-open" disabled={busy} onClick={() => onOpenProject(project)}>Öppna <span aria-hidden="true">›</span></button>
                        </div>
                      </div>
                      {expanded && <div className="rs3-project-details"><span><strong>Projektfil</strong><span>{project.path || "Ingen sökväg registrerad"}</span></span><span><strong>Senast uppdaterat</strong><span>{projectDate(project.updatedAt) ?? "Datum saknas"}</span></span></div>}
                    </div>;
                  })}
                </div>}
                {showAllProjects && uniqueProjects.length > 0 && <p className="rs3-project-note">Visar {visibleProjects.length} sparade projekt. Projekt med olika sökvägar behandlas separat.</p>}
              </section>
              <footer className="rs3-footer"><span>Dina källdata stannar lokalt.</span>{projectRoot && <div className="rs3-root"><button type="button" className="rs3-text-link" onClick={() => setShowProjectRoot((value) => !value)} aria-expanded={showProjectRoot}>Projektplats {showProjectRoot ? "⌃" : "⌄"}</button>{showProjectRoot && <div className="rs3-root-detail"><span title={projectRoot}>{projectRoot}</span><button type="button" onClick={onChangeProjectRoot} disabled={busy}>Ändra</button></div>}</div>}</footer>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
