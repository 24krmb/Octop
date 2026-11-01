import dida365 from "./dida365.png";
import notion from "./notion.png";
import openalex from "./openalex.svg";
import tencentDocs from "./tencent-docs.png";
import tencentIma from "./tencent-ima.png";
import tencentLexiang from "./tencent-lexiang.png";
import weknora from "./weknora.svg";
import youdaoNote from "./youdao-note.png";
import windStockData from "./wind-stock-data.png";
import tdxFinance from "./tdx-finance.png";
import fiona from "./fiona.png";
import yuqueMcp from "./yuque-mcp.png";

export const CONNECTOR_LOGOS: Record<string, string> = {
  "tencent-docs": tencentDocs,
  "tencent-ima": tencentIma,
  "tencent-lexiang": tencentLexiang,
  notion,
  openalex,
  dida365: dida365,
  "youdao-note": youdaoNote,
  weknora,
  "wind-stock-data": windStockData,
  "wind-index-data": windStockData,
  "wind-fund-data": windStockData,
  "wind-economic-data": windStockData,
  "wind-bond-data": windStockData,
  "wind-analytics-data": windStockData,
  "wind-financial-docs": windStockData,
  "tdx-finance": tdxFinance,
};

/**
 * Custom-MCP instances all share kind "custom-mcp", so kind-based lookup
 * cannot give them distinct logos. These keys match against the connector's
 * display name instead (case-insensitive substring).
 */
const CONNECTOR_NAME_LOGOS: Record<string, string> = {
  通达信: tdxFinance,
  tdx: tdxFinance,
  语雀: yuqueMcp,
  yuque: yuqueMcp,
  繁微: fiona,
  fiona: fiona,
};

export function getConnectorLogoByName(
  name: string | null | undefined,
): string | undefined {
  if (!name) return undefined;
  const needle = name.toLowerCase();
  for (const [key, logo] of Object.entries(CONNECTOR_NAME_LOGOS)) {
    if (needle.includes(key.toLowerCase())) return logo;
  }
  return undefined;
}

export function getConnectorLogo(kind: string): string | undefined {
  if (!kind) return undefined;
  const direct = CONNECTOR_LOGOS[kind];
  if (direct) return direct;
  // Tolerate minor kind drift between a connector instance and the catalog
  // (e.g. a dev-era "baidu_map" persisted on an instance vs the finalized
  // "baidu-map" used as the logo key). Without this, the chat connector
  // picker (which renders instance.kind) falls back to a placeholder while
  // the catalog grid (entry.kind) still shows the logo.
  const normalized = kind.toLowerCase().replace(/[_\s]+/g, "-");
  if (normalized !== kind) {
    const fallback = CONNECTOR_LOGOS[normalized];
    if (fallback) return fallback;
  }
  return undefined;
}
