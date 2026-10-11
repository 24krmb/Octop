import { useCallback } from "react";
import SessionList from "./SessionList";
import MinimalAgentSessionNav from "./MinimalAgentSessionNav";
import type { Session } from "../hooks/useSessions";
import type { OctopAgent } from "../../../context/AgentContext";
import styles from "../index.module.less";

/** Dispatched when the chat history rail expand control is clicked. */
export const EXPAND_CHAT_RAIL_EVENT = "octop:expand-chat-rail";

interface ChatSidebarPanelProps {
  isMobile: boolean;
  sidebarOpen: boolean;
  agents: OctopAgent[];
  sessions: Session[];
  activeThreadId: string | null;
  resolvedAgentId: string | null | undefined;
  sessionsHasMore: boolean;
  sessionsLoadingMore: boolean;
  onLoadMoreSessions: () => void;
  onFetchAllSessions: () => void;
  onSelectSession: (sessionId: string, agentId: string) => void;
  onAgentSelect: (agentId: string) => void;
  /** Start a fresh chat from an expert row (classic + minimal). */
  onNewChatWithAgent: (agentId: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, name: string) => void;
  onPinSession: (id: string, pinned: boolean) => void;
  onForkSession: (id: string, agentId?: string | null) => void;
  forkDisabled?: boolean;
  forkDisabledHint?: string;
  onSidebarOpenChange: (open: boolean) => void;
  /**
   * Unified-sidebar mode: panel lives inside the nav rail's records tab
   * (no second rail chrome). ``false`` keeps the legacy mobile overlay.
   */
  navEmbedded?: boolean;
}

export default function ChatSidebarPanel({
  isMobile,
  sidebarOpen,
  agents,
  sessions,
  activeThreadId,
  resolvedAgentId,
  sessionsHasMore,
  sessionsLoadingMore,
  onLoadMoreSessions,
  onFetchAllSessions,
  onSelectSession,
  onAgentSelect,
  onNewChatWithAgent,
  onDeleteSession,
  onRenameSession,
  onPinSession,
  onForkSession,
  forkDisabled,
  forkDisabledHint,
  onSidebarOpenChange,
  navEmbedded = false,
}: ChatSidebarPanelProps) {
  const handleOverlayClick = useCallback(() => {
    onSidebarOpenChange(false);
  }, [onSidebarOpenChange]);

  // Mobile minimal drawer keeps the compact merged nav; the desktop records
  // tab renders the full session list (search + agent cards).
  const sessionList =
    navEmbedded && isMobile ? (
      <MinimalAgentSessionNav
        agents={agents}
        activeId={activeThreadId}
        activeAgentId={resolvedAgentId ?? null}
        activeSessions={sessions}
        onSelect={onSelectSession}
        onAgentSelect={onAgentSelect}
        onNewChat={onNewChatWithAgent}
        onDeleteActive={onDeleteSession}
        onRenameActive={onRenameSession}
        onPinActive={onPinSession}
        onFork={onForkSession}
        activeForkDisabled={forkDisabled}
        activeForkDisabledHint={forkDisabledHint}
      />
    ) : (
      <SessionList
        agents={agents}
        sessions={sessions}
        activeId={activeThreadId}
        activeAgentId={resolvedAgentId ?? null}
        hasMore={sessionsHasMore}
        loadingMore={sessionsLoadingMore}
        onLoadMore={onLoadMoreSessions}
        onFetchAllSessions={onFetchAllSessions}
        onSelect={onSelectSession}
        onAgentSelect={onAgentSelect}
        onNewChat={onNewChatWithAgent}
        onDelete={onDeleteSession}
        onRename={onRenameSession}
        onPin={onPinSession}
        onFork={onForkSession}
        activeForkDisabled={forkDisabled}
        activeForkDisabledHint={forkDisabledHint}
      />
    );

  if (navEmbedded) {
    return (
      <div className={styles.sidebarNavEmbedded} data-testid="chat-nav-records">
        {sessionList}
      </div>
    );
  }

  // Legacy mobile overlay drawer (desktop now renders inside the nav rail).
  return (
    <div className={`${styles.sidebarWrapper} ${!isMobile && !sidebarOpen ? styles.sidebarWrapperCollapsed : ""}`}>
      {isMobile && sidebarOpen && (
        <div className={styles.overlay} onClick={handleOverlayClick} />
      )}

      <div
        className={`${styles.sidebar} ${
          sidebarOpen ? styles.sidebarOpen : ""
        }`}
      >
        {sessionList}
      </div>
    </div>
  );
}
