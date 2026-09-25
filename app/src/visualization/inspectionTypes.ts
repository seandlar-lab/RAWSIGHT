export type InspectionLinkProps = {
  /**
   * Shared semantic point index, e.g. wide-temporal axis_index.
   * null means that no point is currently inspected.
   */
  inspectionIndex?: number | null;

  /**
   * True when the shared inspection point has been locked by click.
   */
  inspectionLocked?: boolean;

  /**
   * Reports transient hover inspection. null clears hover.
   */
  onInspectionHover?: (index: number | null) => void;

  /**
   * Requests that the supplied semantic point index is locked/unlocked.
   */
  onInspectionToggle?: (index: number) => void;
};
