import { App } from "antd";
import { useEffect, type ReactNode } from "react";
import { bindAntdMessage, unbindAntdMessage } from "../utils/antdMessage";
import { bindAntdModal, unbindAntdModal } from "../utils/antdModal";

/** Captures App.useApp() APIs for non-hook call sites (utils). */
function AntdAppApiBinder() {
  const { message, modal } = App.useApp();
  useEffect(() => {
    bindAntdMessage(message);
    bindAntdModal(modal);
    return () => {
      unbindAntdMessage();
      unbindAntdModal();
    };
  }, [message, modal]);
  return null;
}

/** Wrap under ConfigProvider so message/modal/notification follow theme. */
export function AntdAppProvider({ children }: { children: ReactNode }) {
  // getPrefixCls returns customizePrefixCls verbatim (no -app suffix), so
  // pass the full class to get exactly class="… 24kclaw-app".
  return (
    <App prefixCls="24kclaw-app">
      <AntdAppApiBinder />
      {children}
    </App>
  );
}
