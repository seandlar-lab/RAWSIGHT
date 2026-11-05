import type { ComponentProps, ReactNode } from "react";
import { UnderstandOverview } from "../components/UnderstandOverview";
import type { ExploreView } from "../navigation/navigationModel";

/**
 * Explore presentation boundary. Navigation and analytical state are owned by App.
 * Visualisation children are provided by App until their actions have been extracted.
 */
type OverviewProps = ComponentProps<typeof UnderstandOverview>;

export interface ExploreWorkspaceProps {
  view: ExploreView;
  profile: OverviewProps["profile"];
  fileName: OverviewProps["fileName"];
  loading: OverviewProps["loading"];
  onOpenAnalysis: OverviewProps["onOpenAnalysis"];
  onOverview: () => void;
  onVisualization: () => void;
  children: ReactNode;
}

export function ExploreWorkspace({
  view,
  profile,
  fileName,
  loading,
  onOpenAnalysis,
  onOverview,
  onVisualization,
  children,
}: ExploreWorkspaceProps) {
  return (
    <section className="metadata-workspace" aria-label="Explore workspace">
      {view === "overview" && (
        <UnderstandOverview
          profile={profile}
          fileName={fileName}
          loading={loading}
          onOpenAnalysis={onOpenAnalysis}
          onExplore={onVisualization}
        />
      )}
      <nav
        style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}
        aria-label="Utforska data"
      >
        <button
          type="button"
          onClick={onOverview}
          aria-current={view === "overview" ? "page" : undefined}
          disabled={view === "overview"}
        >
          Överblick
        </button>
        <button
          type="button"
          onClick={onVisualization}
          aria-current={view === "visualization" ? "page" : undefined}
          disabled={view === "visualization"}
        >
          Visualisering
        </button>
      </nav>
      {view === "visualization" && (
        <>
          <div id="rs-explore-details" className="metadata-header">
            <div>
              <strong>Explore</strong>
              <p>Explore the dataset using the structure detected by Light Analysis.</p>
            </div>
          </div>
          {children}
        </>
      )}
      {view !== "overview" && view !== "visualization" && (
        <div className="workspace-placeholder" role="status">
          <strong>{view === "discoveries" ? "Upptäckter" : "Kvalitet"}</strong>
          <p>Denna vy är ännu inte ansluten.</p>
        </div>
      )}
    </section>
  );
}
