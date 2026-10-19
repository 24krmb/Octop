import SessionList from "./SessionList";
import MinimalAgentSessionNav from "./MinimalAgentSessionNav";
import type { Session } from "../hooks/useSessions";
import type { OctopAgent } from "../../../context/AgentContext";
import styles from "../index.module.less";

interface ChatSidebarPanelProps {
  isMobile: boolean;
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
  onDeleteSession: (
    id: string,
    compact: boolean,
  ) => void | Promise<boolean | void>;
  onRenameSession: (id: string, name: string) => void;
  onPinSession: (id: string, pinned: boolean) => void;
  onForkSession: (id: string, agentId?: string | null) => void;
  forkDisabled?: boolean;
  forkDisabledHint?: string;
}

/**
 * Session-history panel hosted inside the nav sidebar's records tab via
 * portal — there is no standalone sidebar chrome anymore. Mobile keeps the
 * compact merged nav; desktop renders the full session list.
 */
export default function ChatSidebarPanel({
  isMobile,
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
}: ChatSidebarPanelProps) {
  return (
    <div className={styles.sidebarNavEmbedded} data-testid="chat-nav-records">
      {isMobile ? (
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
      )}

      <div
        ref={sidebarElRef}
        className={`${styles.sidebar} ${
          sidebarOpen ? styles.sidebarOpen : ""
        } ${isSidebarResizing ? styles.sidebarResizing : ""}`}
        style={
          !isMobile && sidebarOpen
            ? { width: sidebarWidth, minWidth: sidebarWidth }
            : undefined
        }
      >
        {sessionList}
        {!isMobile && sidebarOpen && (
          <div
            className={`${styles.sidebarResizeHandle} ${
              isSidebarResizing ? styles.sidebarResizeHandleActive : ""
            }`}
            onPointerDown={onSidebarResizeStart}
            role="separator"
            aria-orientation="vertical"
            aria-label={t("chat.resizeSidebar", "调整侧栏宽度")}
          />
        )}
      </div>

      {!isMobile && (
        <RailEdgeControl
          expanded={sidebarOpen}
          onToggle={handleRailToggle}
          side={sidebarOpen ? "end" : "start"}
          /* Collapsed: share the nav rail divider — avoid a second gapped line. */
          showLine={sidebarOpen}
          placement={sidebarOpen ? "center" : "after"}
          className={
            sidebarOpen ? styles.chatRailEdgeOpen : styles.chatRailEdgeClosed
          }
        />
      )}
    </div>
  );
}
