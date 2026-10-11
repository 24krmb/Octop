import { useTranslation } from "react-i18next";
import type { MinimalNavPane } from "./layoutModeStorage";
import styles from "./Sidebar.module.less";

/**
 * Two-segment tab control (能力 | 对话) shown above the unified sidebar
 * panes on desktop. Replaces the per-mode pane toggle on the expanded rail.
 */
export default function SidebarPaneTabs({
  capabilitiesLabel,
  value,
  onSelect,
}: {
  /** Name of the first navigation group（"能力"）. */
  capabilitiesLabel: string;
  /** Active pane — "settings" renders the capability nav, "records" the chat list. */
  value: MinimalNavPane;
  onSelect: (pane: MinimalNavPane) => void;
}) {
  const { t } = useTranslation();
  const tabs: Array<{ key: MinimalNavPane; label: string }> = [
    { key: "settings", label: capabilitiesLabel },
    { key: "records", label: t("nav.chat", "对话") },
  ];

  return (
    <div className={styles.paneTabs} role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={value === tab.key}
          className={`${styles.paneTab} ${
            value === tab.key ? styles.paneTabActive : ""
          }`}
          onClick={() => onSelect(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
