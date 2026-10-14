import { afterEach, describe, expect, it } from "vitest";
import {
  loadAppearanceOnBoot,
  readStoredAppearance,
  writeStoredAppearance,
} from "./appearanceStorage";
import { THEME_STORAGE_KEY } from "./themePalettes";

afterEach(() => {
  localStorage.removeItem(THEME_STORAGE_KEY);
});

describe("appearanceStorage", () => {
  it("defaults to the system preference", () => {
    expect(readStoredAppearance()).toEqual({ preference: "system" });
  });

  it("reads a legacy plain preference string", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");

    expect(readStoredAppearance()).toEqual({ preference: "dark" });
  });

  it("reads the preference from unified JSON and ignores palette fields", () => {
    localStorage.setItem(
      THEME_STORAGE_KEY,
      JSON.stringify({
        preference: "light",
        palette: "indigo",
        customColor: "#66f",
      }),
    );

    expect(readStoredAppearance()).toEqual({ preference: "light" });
  });

  it("writes only the preference under the theme key", () => {
    writeStoredAppearance({ preference: "light" });

    expect(JSON.parse(localStorage.getItem(THEME_STORAGE_KEY)!)).toEqual({
      preference: "light",
    });
  });

  it("loadAppearanceOnBoot re-persists the normalized preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");

    expect(loadAppearanceOnBoot()).toEqual({ preference: "dark" });
    expect(JSON.parse(localStorage.getItem(THEME_STORAGE_KEY)!)).toEqual({
      preference: "dark",
    });
  });

  it("falls back safely on invalid JSON or unknown values", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "{not-json");
    expect(readStoredAppearance().preference).toBe("system");

    localStorage.setItem(
      THEME_STORAGE_KEY,
      JSON.stringify({ preference: "neon", palette: "pink" }),
    );
    expect(readStoredAppearance().preference).toBe("system");
  });
});
