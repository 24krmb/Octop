/** Sidebar's lower pane: capability nav (settings) vs chat records. */
export type MinimalNavPane = "settings" | "records";

/** v2: default pane is records (primary). */
export const MINIMAL_NAV_PANE_KEY = "octop:sidebar-minimal-pane-v2";

export function loadMinimalNavPane(): MinimalNavPane {
  try {
    const raw = localStorage.getItem(MINIMAL_NAV_PANE_KEY);
    // Accept briefly-shipped chat/nav aliases if present.
    if (raw === "settings" || raw === "nav") return "settings";
    if (raw === "records" || raw === "chat") return "records";
  } catch {
    /* ignore */
  }
  // Unified sidebar tabs default to the capability nav (能力).
  return "settings";
}

export function saveMinimalNavPane(pane: MinimalNavPane): void {
  try {
    localStorage.setItem(MINIMAL_NAV_PANE_KEY, pane);
  } catch {
    /* ignore */
  }
}
