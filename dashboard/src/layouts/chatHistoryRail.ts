export const CHAT_HISTORY_RAIL_ID = "octop-chat-history-rail";

/** Open mobile/desktop nav on the minimal-mode records pane. */
export const OPEN_NAV_RECORDS_EVENT = "octop:open-nav-records";

/** Close the mobile nav drawer (e.g. after picking a session in the records pane). */
export const CLOSE_NAV_EVENT = "octop:close-nav";

export function isChatPath(pathname: string): boolean {
  return pathname === "/chat" || pathname.startsWith("/chat/");
}

export { isGroupedNavKey as isSettingsPaneNavKey } from "./sidebarNav";
