import { createGlobalStyle } from "antd-style";
import { ConfigProvider, theme as antdTheme } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import dayjs from "dayjs";
import "dayjs/locale/zh-cn";
import { useEffect } from "react";
import DesktopWindowControls from "./components/DesktopWindowControls";
import {
  DesktopChromeProvider,
  useDesktopChrome,
} from "./hooks/useDesktopChrome";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useTranslation } from "react-i18next";
import MainLayout from "./layouts/MainLayout";
import LoginPage from "./pages/Login";
import OidcComplete from "./pages/Login/OidcComplete";
import SetupPage from "./pages/Setup";
import InvitePage from "./pages/Invite";
import AuthGuard from "./components/AuthGuard";
import OctopSpinner from "./components/OctopSpinner";
import { AntdAppProvider } from "./components/AntdAppProvider";
import GlobalErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { AgentProvider } from "./context/AgentContext";
import { LayoutModeProvider } from "./context/LayoutModeContext";
import { VoiceOutputProvider } from "./context/VoiceOutputContext";
import { useIsMobile } from "./hooks/useIsMobile";
import { useUnauthorizedRedirect } from "./hooks/useUnauthorizedRedirect";
import { installDesktopExternalLinks } from "./utils/desktopExternalLinks";
import "./styles/theme-vars.css";
import "./styles/layout.css";
import "./styles/form-override.css";
import "./styles/spin-override.css";

const GlobalStyle = createGlobalStyle`
* {
  margin: 0;
  box-sizing: border-box;
}
`;

function ThemedApp() {
  const { isDark } = useTheme();
  const { t, i18n } = useTranslation();
  const isMobile = useIsMobile();
  const desktopChrome = useDesktopChrome();
  // 品牌色固定为主题蓝（palette 体系已移除）。
  // 品牌色唯一真相来源 = theme-vars.css 的 --fn-* 变量（亮暗自动切换）。
  // antd 派生 token 全部显式映射到变量族，绕开算法对变量字符串的运算。
  const brandTokens = {
    colorPrimary: "var(--fn-color-brand)",
    colorPrimaryHover: "var(--fn-color-brand-hover)",
    colorPrimaryActive: "var(--fn-color-brand-hover)",
    colorLink: "var(--fn-color-brand)",
    colorPrimaryBg: "var(--fn-color-brand-bg)",
    colorPrimaryBgHover: "var(--fn-color-brand-bg)",
    colorPrimaryBorder: "var(--fn-color-brand-border)",
    colorPrimaryBorderHover: "var(--fn-color-brand-border)",
    colorPrimaryText: "var(--fn-text-brand)",
    colorPrimaryTextHover: "var(--fn-text-brand)",
    colorPrimaryTextActive: "var(--fn-text-brand)",
  };
  // Make antd built-ins (Popconfirm OK/Cancel, Modal default footer, Empty,
  // Pagination, DatePicker, Table… ) follow the current UI language.
  // DatePicker month/weekday labels come from dayjs — keep it in sync too.
  const isZh = i18n.language?.toLowerCase().startsWith("zh") ?? false;
  const antdLocale = isZh ? zhCN : enUS;
  dayjs.locale(isZh ? "zh-cn" : "en");

  useUnauthorizedRedirect();

  useEffect(() => installDesktopExternalLinks(), []);

  // Set document title based on current language
  useEffect(() => {
    document.title = t("app.pageTitle");
  }, [t]);

  const themeConfig = {
    algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: {
      borderRadius: 10,
      ...(isMobile
        ? {
            fontSize: 15,
            fontSizeSM: 13,
            fontSizeLG: 17,
            fontSizeXL: 22,
            controlHeight: 36,
          }
        : {}),
      ...(isDark
        ? {
            colorBgBase: "#0f1117",
            colorTextBase: "#e7e7ed",
            colorBgContainer: "#0f1117",
            colorBgElevated: "#1a1c28",
            colorBgLayout: "#0b0d14",
            colorBgSpotlight: "rgba(0, 0, 0, 0.85)",
            colorBgMask: "rgba(5, 5, 8, 0.80)",
            colorBorder: "rgba(255,255,255,0.08)",
            colorBorderSecondary: "rgba(255,255,255,0.05)",
            colorText: "rgba(255, 255, 255, 0.92)",
            colorTextSecondary: "rgba(255, 255, 255, 0.64)",
            colorTextTertiary: "rgba(255, 255, 255, 0.38)",
            colorTextQuaternary: "rgba(255, 255, 255, 0.22)",
            colorFill: "rgba(255, 255, 255, 0.06)",
            colorFillSecondary: "rgba(255, 255, 255, 0.04)",
            colorFillTertiary: "rgba(255, 255, 255, 0.03)",
            colorFillQuaternary: "rgba(255, 255, 255, 0.02)",
            colorBgTextHover: "rgba(255, 255, 255, 0.06)",
            ...brandTokens,
            boxShadow: "0px 4px 6px 0px rgba(0, 0, 0, 0.3)",
            boxShadowSecondary:
              "0px 12px 24px -16px rgba(0, 0, 0, 0.2), 0px 8px 40px 0px rgba(0, 0, 0, 0.3)",
          }
        : {
            colorText: "rgba(24, 49, 83, 0.9)",
            colorTextBase: "rgba(24, 49, 83, 1)",
            colorTextDescription: "rgba(24, 49, 83, 1)",
            ...brandTokens,
          }),
    },
    components: {
      // Tabs 激活/悬停色直接接管（组件 token 是叶子，原样输出变量字符串；
      // 否则暗色算法会把 itemSelectedColor 绑到 colorPrimaryActive 深变体）。
      Button: { primaryShadow: "var(--fn-shadow-soft-brand)" },
      Switch: { colorPrimary: "#00cc99" },
      Segmented: {
        itemColor: "var(--fn-text-primary)",
        trackBg: "var(--fn-bg-primary)",
        itemSelectedBg: "var(--fn-sidebar-item-active-bg)",
        itemSelectedColor: "var(--fn-sidebar-item-active-text)",
      },
      Tabs: {
        itemSelectedColor: "var(--fn-color-brand)",
        itemHoverColor: "var(--fn-color-brand)",
        inkBarColor: "var(--fn-color-brand)",
      },
      ...(isDark
        ? {
          Modal: { headerBg: "#1a1c28", contentBg: "#1a1c28" },
          Input: { colorBgBase: "#0f1117" },
          InputNumber: { colorBgBase: "#0f1117" },
          Select: { colorBgBase: "#0f1117", selectorBg: "#0f1117" },
          DatePicker: { colorBgBase: "#0f1117" },
          Card: { colorBgContainer: "var(--fn-bg-primary)" },
          Tooltip: { colorBgSpotlight: "#424242" },
        }
        : {}),
    },
  };

  return (
    <ConfigProvider
      theme={themeConfig}
      prefixCls="octop"
      locale={antdLocale}
      spin={{ indicator: <OctopSpinner /> }}
    >
      <AntdAppProvider>
        <DesktopChromeProvider value={desktopChrome}>
          {desktopChrome ? (
            <DesktopWindowControls chrome={desktopChrome} />
          ) : null}
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login/oidc/complete" element={<OidcComplete />} />
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/invite" element={<InvitePage />} />
            <Route
              path="/*"
              element={
                <AuthGuard>
                  <AgentProvider>
                    <LayoutModeProvider>
                      <VoiceOutputProvider>
                        <MainLayout />
                      </VoiceOutputProvider>
                    </LayoutModeProvider>
                  </AgentProvider>
                </AuthGuard>
              }
            />
          </Routes>
        </DesktopChromeProvider>
      </AntdAppProvider>
    </ConfigProvider>
  );
}

function App() {
  return (
    // `useTransitions` off: with router transitions on, React keeps the old
    // page mounted while a lazy route chunk downloads and never renders the
    // Suspense fallback, so a nav click looks like it did nothing.
    <BrowserRouter useTransitions={false}>
      <GlobalErrorBoundary>
        <GlobalStyle />
        <ThemeProvider>
          <ThemedApp />
        </ThemeProvider>
      </GlobalErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
