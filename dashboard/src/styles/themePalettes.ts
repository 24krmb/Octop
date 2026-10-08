/** 品牌色板 — 仅保留专家图标取色用的精选色板与品牌色工具。 */

export type ThemePalette =
  | "rose"
  | "tech"
  | "indigo"
  | "teal"
  | "violet"
  | "emerald"
  | "amber"
  | "slate"
  | "custom";

export const VALID_PALETTES: ThemePalette[] = [
  "rose",
  "tech",
  "indigo",
  "teal",
  "violet",
  "emerald",
  "amber",
  "slate",
];

/** 仅内置精选色板 — "custom" 通过十六进制色值单独处理。 */
export const CURATED_PALETTES: ThemePalette[] = [...VALID_PALETTES];

export const DEFAULT_PALETTE: ThemePalette = "custom";
export const DEFAULT_CUSTOM_COLOR = "#1d4ed8";

export function isCuratedPalette(value: string): value is ThemePalette {
  return (VALID_PALETTES as string[]).includes(value);
}

/** 明暗偏好共用的 localStorage 键。 */
export const THEME_STORAGE_KEY = "theme";

/** 色板选择器中展示的色块颜色（浅色品牌色）。 */
export const PALETTE_SWATCH: Record<ThemePalette, string> = {
  rose: "#E85D75",
  tech: "#4B74FA",
  indigo: "#6366F1",
  teal: "#0D9488",
  violet: "#7C3AED",
  emerald: "#10B981",
  amber: "#F59E0B",
  slate: "#64748B",
  custom: DEFAULT_CUSTOM_COLOR, // 实时色块由选择器 UI 提供
};

type AntdBrandTokens = {
  colorPrimary: string;
  colorPrimaryHover: string;
  colorPrimaryActive: string;
  colorLink: string;
  colorPrimaryBg?: string;
  colorPrimaryBgHover?: string;
  colorPrimaryBorder?: string;
  colorPrimaryBorderHover?: string;
  colorPrimaryText?: string;
  colorPrimaryTextHover?: string;
  colorPrimaryTextActive?: string;
};

/** 当前色板 × 模式下解析后的 Ant Design / 图表主色。 */
export function brandPrimary(
  palette: ThemePalette,
  isDark: boolean,
  customColor?: string | null,
): string {
  const tokens = brandTokensFor(palette, isDark, customColor);
  return isDark ? tokens.colorLink : tokens.colorPrimary;
}

// ---------------------------------------------------------------------------
// 自定义品牌色 — 由一个十六进制色值派生完整的 token 集合
// ---------------------------------------------------------------------------

/** 将用户输入规范化为 #rrggbb。 */
export function normalizeHexColor(
  input: string | null | undefined,
): string | null {
  const raw = (input ?? "").trim().replace(/^#/, "");
  if (/^[0-9a-fA-F]{3}$/.test(raw)) {
    return `#${raw
      .split("")
      .map((ch) => `${ch}${ch}`)
      .join("")
      .toLowerCase()}`;
  }
  if (/^[0-9a-fA-F]{6}$/.test(raw)) {
    return `#${raw.toLowerCase()}`;
  }
  return null;
}

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  return `#${((clamp(r) << 16) | (clamp(g) << 8) | clamp(b))
    .toString(16)
    .padStart(6, "0")}`;
}

/** 两个十六进制颜色之间的线性插值（t 取值范围 [0,1]）。 */
export function mixHex(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
}

function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((c) => {
    const v = c / 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** 两个十六进制颜色之间的 WCAG 对比度（1..21）。 */
export function contrastRatio(a: string, b: string): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const lighter = Math.max(la, lb);
  const darker = Math.min(la, lb);
  return (lighter + 0.05) / (darker + 0.05);
}

/** 持续提亮直到在深色背景上可读（与 #0f1117 对比度 ≥3:1）。 */
function ensureTextOnDark(hex: string): string {
  let color = hex;
  for (let i = 0; i < 12 && contrastRatio(color, "#0f1117") < 3; i++) {
    color = mixHex(color, "#FFFFFF", 0.12);
  }
  return color;
}

export interface CustomBrandColors {
  /** 加深后的实色主色，搭配白色文字保持可读（浅色模式）。 */
  solid: string;
  /** 提亮后的文字/链接变体，用于深色模式。 */
  onDark: string;
  /** 徽章/标签用的强调色变体（保留原始色相，中等亮度）。 */
  accent: string;
}

export function deriveCustomBrandColors(hex: string): CustomBrandColors {
  return {
    solid: hex,
    onDark: ensureTextOnDark(hex),
    accent: ensureTextOnDark(mixHex(hex, "#FFFFFF", 0.12)),
  };
}

/** 自定义色板对应的 Ant Design 品牌 token，由一个十六进制色值派生。 */
export function customBrandTokens(hex: string): {
  light: AntdBrandTokens;
  dark: AntdBrandTokens;
} {
  const { solid, onDark } = deriveCustomBrandColors(hex);
  const solidHover = mixHex(solid, "#000000", 0.1);
  const solidActive = mixHex(solid, "#000000", 0.2);
  return {
    light: {
      colorPrimary: solid,
      colorPrimaryHover: solidHover,
      colorPrimaryActive: solidActive,
      colorLink: solid,
    },
    dark: {
      colorPrimary: solid,
      colorPrimaryBg: `rgba(${hexToRgb(solid).join(", ")}, 0.12)`,
      colorPrimaryBgHover: `rgba(${hexToRgb(solid).join(", ")}, 0.16)`,
      colorPrimaryBorder: `rgba(${hexToRgb(solid).join(", ")}, 0.25)`,
      colorPrimaryBorderHover: `rgba(${hexToRgb(solid).join(", ")}, 0.35)`,
      colorPrimaryHover: mixHex(onDark, "#FFFFFF", 0.12),
      colorPrimaryActive: solid,
      colorPrimaryText: onDark,
      colorPrimaryTextHover: mixHex(onDark, "#FFFFFF", 0.18),
      colorPrimaryTextActive: onDark,
      colorLink: onDark,
    },
  };
}

/** 固定品牌色的 Ant token — 品牌色已在 theme-vars.css 定死，仅 custom 路径派生。 */
export function brandTokensFor(
  _palette: ThemePalette,
  isDark: boolean,
  customColor?: string | null,
): AntdBrandTokens {
  return customBrandTokens(customColor || DEFAULT_CUSTOM_COLOR)[
    isDark ? "dark" : "light"
  ];
}
