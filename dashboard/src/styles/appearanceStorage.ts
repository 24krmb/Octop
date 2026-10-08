import { THEME_STORAGE_KEY } from "./themePalettes";

export type ThemePreference = "system" | "light" | "dark";

export type StoredAppearance = {
  preference: ThemePreference;
};

const VALID_PREFERENCES: ThemePreference[] = ["system", "light", "dark"];

function isPreference(value: unknown): value is ThemePreference {
  return (
    typeof value === "string" && (VALID_PREFERENCES as string[]).includes(value)
  );
}

/**
 * Read light/dark preference from the shared `theme` key.
 * Legacy JSON shapes (palette/customColor) are tolerated but ignored —
 * the brand palette is fixed at build time now.
 */
export function readStoredAppearance(): StoredAppearance {
  const raw = localStorage.getItem(THEME_STORAGE_KEY);
  if (!raw) {
    return { preference: "system" };
  }

  // Legacy: plain preference string
  if (isPreference(raw)) {
    return { preference: raw };
  }

  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      const obj = parsed as Record<string, unknown>;
      const preference = isPreference(obj.preference)
        ? obj.preference
        : "system";
      return { preference };
    }
  } catch {
    // fall through
  }

  return { preference: "system" };
}

/** Persist the preference under the same `theme` key. */
export function writeStoredAppearance(appearance: StoredAppearance): void {
  localStorage.setItem(
    THEME_STORAGE_KEY,
    JSON.stringify({ preference: appearance.preference }),
  );
}

/** One-shot boot read for ThemeProvider initial state. */
export function loadAppearanceOnBoot(): StoredAppearance {
  const appearance = readStoredAppearance();
  writeStoredAppearance(appearance);
  return appearance;
}
