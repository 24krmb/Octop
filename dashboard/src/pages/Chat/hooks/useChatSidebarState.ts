import { useSyncExternalStore } from "react";

export const CHAT_SIDEBAR_KEY = "octop:chat-sidebar:open";
/** Viewport width at/above which the chat session drawer defaults open. */
export const CHAT_SIDEBAR_WIDE_BREAKPOINT = 1200;

/**
 * Resolve initial open state: explicit localStorage preference wins;
 * otherwise default open on wide viewports only. Does not react to resize.
 */
export function resolveChatSidebarDefaultOpen(
  stored: string | null,
  viewportWidth: number,
): boolean {
  if (stored === "true") return true;
  if (stored === "false") return false;
  return viewportWidth >= CHAT_SIDEBAR_WIDE_BREAKPOINT;
}

let sidebarOpen = (() => {
  let stored: string | null = null;
  try {
    stored = localStorage.getItem(CHAT_SIDEBAR_KEY);
  } catch {
    stored = null;
  }
  const width =
    typeof window !== "undefined" && typeof window.innerWidth === "number"
      ? window.innerWidth
      : 0;
  return resolveChatSidebarDefaultOpen(stored, width);
})();

const sidebarListeners = new Set<() => void>();

function setSidebarOpenGlobal(value: boolean | ((prev: boolean) => boolean)) {
  const next = typeof value === "function" ? value(sidebarOpen) : value;
  if (next === sidebarOpen) return;
  sidebarOpen = next;
  try {
    localStorage.setItem(CHAT_SIDEBAR_KEY, String(next));
  } catch {
    /* ignore */
  }
  for (const fn of sidebarListeners) {
    try {
      fn();
    } catch {
      /* ignore */
    }
  }
}

function subscribeSidebar(listener: () => void) {
  sidebarListeners.add(listener);
  return () => {
    sidebarListeners.delete(listener);
  };
}

function getSidebarSnapshot() {
  return sidebarOpen;
}

/**
 * Mobile overlay open state for the legacy chat-session drawer.
 *
 * The desktop sidebar is now the unified nav rail (capability/records tabs);
 * this state only drives the mobile overlay drawer and is kept module-global
 * so the mobile header and chat toolbar can toggle the same drawer.
 */
export function useChatSidebarOpen(): [
  boolean,
  (v: boolean | ((prev: boolean) => boolean)) => void,
] {
  const value = useSyncExternalStore(
    subscribeSidebar,
    getSidebarSnapshot,
    getSidebarSnapshot,
  );
  return [value, setSidebarOpenGlobal];
}
