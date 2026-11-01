/**
 * Browser session state — stub after the 24K-Claw browser removal.
 * Keeps the original hook shape so legacy imports compile; all
 * browser-session plumbing is inert.
 */
export function useBrowserSessionState(
  _threadId?: string | null,
  _hasBrowserTool?: boolean,
  _bridgeConnectionId?: string | null,
) {
  return {
    sessionId: null as string | null,
    state: "idle" as string,
    controlOwner: null as string | null,
    environment: "removed" as string,
    refresh: () => {},
  };
}

export default useBrowserSessionState;
