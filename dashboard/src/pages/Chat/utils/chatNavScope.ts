import { isTeamAgent } from "../../../utils/teamAgent";

/** Classic chat-nav filter under the search box. */
export type ChatNavScope = "experts" | "teams";

export const CHAT_NAV_SCOPES: readonly ChatNavScope[] = [
  "experts",
  "teams",
];

type NavAgent = {
  kind?: string | null;
  agent_id?: string | null;
};

/** Open the team tab when the current chat is a team; otherwise experts. */
export function initialChatNavScope(
  agent: { kind?: string | null } | null | undefined,
): ChatNavScope {
  return agent && isTeamAgent(agent) ? "teams" : "experts";
}

/** Teams include team agents; experts is everything else. */
export function matchesChatNavScope(
  agent: NavAgent,
  scope: ChatNavScope,
): boolean {
  if (scope === "teams") return isTeamAgent(agent);
  return !isTeamAgent(agent);
}
