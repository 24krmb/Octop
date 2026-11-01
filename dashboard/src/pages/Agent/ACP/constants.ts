import opencodeIcon from "../../../assets/acp/opencode.svg";
import openaiIcon from "../../../assets/providers/openai.png";
import moonshotIcon from "../../../assets/acp/moonshot.png";
import cursorIcon from "../../../assets/acp/cursor.png";
import piIcon from "../../../assets/acp/pi.png";
import customRunnerIcon from "../../../assets/providers/custom-provider.svg";

/** Built-in ACP runner ids (order preserved in the grid). */
export const BUILTIN_RUNNER_ORDER = [
  "opencode",
  "codex",
  "kimi_code",
  "cursor_cli",
  "pi",
] as const;

export type BuiltinRunnerKey = (typeof BUILTIN_RUNNER_ORDER)[number];

export function isBuiltinRunner(key: string): key is BuiltinRunnerKey {
  return (BUILTIN_RUNNER_ORDER as readonly string[]).includes(key);
}

export const RUNNER_ICONS: Record<string, string> = {
  opencode: opencodeIcon,
  codex: openaiIcon,
  kimi_code: moonshotIcon,
  cursor_cli: cursorIcon,
  pi: piIcon,
};

export const RUNNER_LABEL_KEYS: Record<string, string> = {
  opencode: "acp.runner_opencode",
  codex: "acp.runner_codex",
  kimi_code: "acp.runner_kimi_code",
  cursor_cli: "acp.runner_cursor_cli",
  pi: "acp.runner_pi",
};

export const RUNNER_INTRO_KEYS: Record<string, string> = {
  opencode: "acp.intro_opencode",
  codex: "acp.intro_codex",
  kimi_code: "acp.intro_kimi_code",
  cursor_cli: "acp.intro_cursor_cli",
  pi: "acp.intro_pi",
};

export function runnerIcon(key: string): string {
  return RUNNER_ICONS[key] ?? customRunnerIcon;
}

export function runnerLabelKey(key: string): string {
  return RUNNER_LABEL_KEYS[key] ?? "acp.runner_custom";
}

export function runnerIntroKey(key: string): string {
  return RUNNER_INTRO_KEYS[key] ?? "acp.intro_custom";
}
