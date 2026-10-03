import type { AgentItem } from "@/lib/api";

/** Workspace Equipo is the specialist roster. A utility such as Brief stays a room, not a teammate. */
const UTILITY_SLUGS = new Set(["sentinel", "teams", "post"]);

export function onRoster(agent: AgentItem): boolean {
  if (UTILITY_SLUGS.has(agent.slug)) {
    return false;
  }
  return agent.config?.roster !== false;
}
