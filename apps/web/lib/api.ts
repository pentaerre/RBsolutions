export const API_PREFIX = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type Health = {
  ok: boolean;
  ollama: {
    ok: boolean;
    models: string[];
    default_model?: string;
    default_available?: boolean;
    error?: string;
  };
  documents_dir: string;
  index: { chunks: number };
  embed_backend: string;
  platform?: { apps: number; tools: number; agents: number; database: string };
};

export type DocumentFile = {
  filename: string;
  size_bytes: number;
  indexed: boolean;
  chunks: number;
  pages: number;
  doc_type?: string;
  source?: string;
  status?: string;
  records?: number;
};

export type ExtractedRow = {
  id: string;
  kind: string;
  filename: string;
  payload: Record<string, unknown>;
};

export type ToolItem = {
  id: string;
  slug: string;
  name: string;
  status: string;
  kind: string;
  summary: string;
};

export type AgentItem = {
  id: string;
  slug: string;
  name: string;
  role: string;
  status: string;
  summary: string;
  tools: string[];
};

export type AppItem = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  status: string;
  base_url: string;
  summary: string;
};

export type ChatEvent =
  | { type: "route"; agent: string; name?: string }
  | { type: "tool"; slug: string; ok: boolean }
  | { type: "sources"; items: { filename: string; chunk_index: number; distance: number }[] }
  | { type: "model"; name: string }
  | { type: "token"; content: string }
  | { type: "error"; message: string }
  | { type: "done" };
