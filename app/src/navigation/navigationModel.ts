/** Navigation state only. Dataset identity, analysis results and selection belong elsewhere. */
export type MainSection = "explore" | "data" | "metadata" | "history";
export type ExploreView = "overview" | "discoveries" | "visualization" | "quality";
export type DataView = "overview" | "columns" | "profile";

export type Location =
  | { section: "explore"; view: ExploreView }
  | { section: "data"; view: DataView }
  | { section: "metadata"; view: "overview" }
  | { section: "history"; view: "overview" };

export interface NavigationState {
  current: Location;
  history: Location[];
  lastBySection: Partial<Record<MainSection, Location>>;
}

export const DEFAULT_LOCATION: Location = { section: "explore", view: "overview" };

export function createNavigationState(): NavigationState {
  return {
    current: DEFAULT_LOCATION,
    history: [],
    lastBySection: { explore: DEFAULT_LOCATION },
  };
}

function sameLocation(a: Location, b: Location): boolean {
  return a.section === b.section && a.view === b.view;
}

/** Record navigation without mutating existing state. */
export function navigate(state: NavigationState, target: Location): NavigationState {
  if (sameLocation(state.current, target)) return state;
  return {
    current: target,
    history: [...state.history, state.current],
    lastBySection: { ...state.lastBySection, [target.section]: target },
  };
}

/** Main menu returns to the last opened view in that section. */
export function navigateMain(state: NavigationState, section: MainSection): NavigationState {
  const target = state.lastBySection[section] ?? defaultForSection(section);
  return navigate(state, target);
}

export function defaultForSection(section: MainSection): Location {
  switch (section) {
    case "explore": return DEFAULT_LOCATION;
    case "data": return { section: "data", view: "overview" };
    case "metadata": return { section: "metadata", view: "overview" };
    case "history": return { section: "history", view: "overview" };
  }
}

/** Back does not clear active project, dataset, profile or analysis context. */
export function navigateBack(state: NavigationState): NavigationState {
  if (state.history.length === 0) return state;
  const previous = state.history[state.history.length - 1];
  return {
    current: previous,
    history: state.history.slice(0, -1),
    lastBySection: { ...state.lastBySection, [previous.section]: previous },
  };
}

/** Call only when intentionally entering a different project or closing workspace. */
export function resetNavigation(): NavigationState {
  return createNavigationState();
}
