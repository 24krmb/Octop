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
  onDeleteSession: (id: string) => void;
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
      )}
    </div>
  );
}
