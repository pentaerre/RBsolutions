export const API_PREFIX = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function apiSend<T>(path: string, method: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type Health = {
  ok: boolean;
  ollama: { ok: boolean; models: string[]; default_model?: string; error?: string };
  index: { chunks: number };
  platform: { apps: number; tools: number; agents: number; database: string };
};

export type AppItem = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  base_url: string;
  status: string;
  summary: string;
};

export type ToolItem = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  status: string;
  summary: string;
  entrypoint: string;
  config: Record<string, unknown>;
  agents: string[];
};

export type AgentItem = {
  id: string;
  slug: string;
  name: string;
  role: string;
  status: string;
  summary: string;
  model: string;
  system_prompt: string;
  config: Record<string, unknown>;
  tools: string[];
};
