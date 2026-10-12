import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  loadMinimalNavPane,
  saveMinimalNavPane,
  type MinimalNavPane,
} from "../layouts/layoutModeStorage";

interface LayoutModeContextValue {
  /** Lower sidebar pane: capability nav (settings) vs chat records. */
  minimalPane: MinimalNavPane;
  setMinimalPane: (pane: MinimalNavPane) => void;
}

const LayoutModeContext = createContext<LayoutModeContextValue>({
  minimalPane: "settings",
  setMinimalPane: () => {},
});

export function LayoutModeProvider({ children }: { children: ReactNode }) {
  const [minimalPane, setMinimalPaneState] = useState<MinimalNavPane>(() =>
    loadMinimalNavPane(),
  );

  const setMinimalPane = useCallback((pane: MinimalNavPane) => {
    setMinimalPaneState(pane);
    saveMinimalNavPane(pane);
  }, []);

  const value = useMemo(
    () => ({ minimalPane, setMinimalPane }),
    [minimalPane, setMinimalPane],
  );

  return (
    <LayoutModeContext.Provider value={value}>
      {children}
    </LayoutModeContext.Provider>
  );
}

export function useLayoutMode(): LayoutModeContextValue {
  return useContext(LayoutModeContext);
}
