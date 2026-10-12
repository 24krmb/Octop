import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { CHAT_HISTORY_RAIL_ID } from "../../../layouts/chatHistoryRail";
import { useLayoutMode } from "../../../context/LayoutModeContext";

/** DOM mount for the session-history rail (the nav sidebar's records pane). */
export function useChatHistoryRail(): HTMLElement | null {
  const { minimalPane } = useLayoutMode();
  const { pathname } = useLocation();
  const [rail, setRail] = useState<HTMLElement | null>(() =>
    typeof document !== "undefined"
      ? document.getElementById(CHAT_HISTORY_RAIL_ID)
      : null,
  );

  useEffect(() => {
    const sync = () => {
      setRail(document.getElementById(CHAT_HISTORY_RAIL_ID));
    };
    sync();
    // Pane / route swaps remount or clear the rail after paint.
    const raf = window.requestAnimationFrame(sync);
    const t = window.setTimeout(sync, 0);
    return () => {
      window.cancelAnimationFrame(raf);
      window.clearTimeout(t);
    };
  }, [minimalPane, pathname]);

  return rail;
}
