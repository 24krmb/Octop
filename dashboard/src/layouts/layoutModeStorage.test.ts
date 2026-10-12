import { afterEach, describe, expect, it } from "vitest";
import {
  MINIMAL_NAV_PANE_KEY,
  loadMinimalNavPane,
  saveMinimalNavPane,
} from "../../src/layouts/layoutModeStorage";

describe("layoutModeStorage", () => {
  afterEach(() => {
    localStorage.removeItem(MINIMAL_NAV_PANE_KEY);
  });

  it("defaults to the capabilities pane", () => {
    expect(loadMinimalNavPane()).toBe("settings");
  });

  it("persists the selected pane", () => {
    saveMinimalNavPane("records");
    expect(loadMinimalNavPane()).toBe("records");
  });

  it("migrates briefly-shipped chat/nav aliases", () => {
    localStorage.setItem(MINIMAL_NAV_PANE_KEY, "chat");
    expect(loadMinimalNavPane()).toBe("records");
    localStorage.setItem(MINIMAL_NAV_PANE_KEY, "nav");
    expect(loadMinimalNavPane()).toBe("settings");
  });

  it("ignores invalid stored values", () => {
    localStorage.setItem(MINIMAL_NAV_PANE_KEY, "other");
    expect(loadMinimalNavPane()).toBe("settings");
  });
});
