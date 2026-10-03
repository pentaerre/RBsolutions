export const API_PREFIX = "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
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
  rel_path?: string;
  path?: string;
  size_bytes: number;
  indexed: boolean;
  chunks: number;
  pages: number;
  doc_type?: string;
  source?: string;
  status?: string;
  records?: number;
  classify_method?: string;
  classify_note?: string;
  error?: string;
  taxonomy_l1?: string;
  taxonomy_l2?: string;
};

export type LibraryDocument = {
  id: string;
  filename: string;
  rel_path: string;
  abs_path: string;
  source: string;
  suffix: string;
  status: string;
  pages: number;
  read_pages: number;
  chunks: number;
  size_bytes: number;
  summary: string;
  keywords: string[];
  taxonomy_l1: string;
  taxonomy_l2: string;
  taxonomist_slug?: string;
  classified_path?: string;
  classify_method?: string;
  classify_note?: string;
  ocr_used: boolean;
  rag_selected: boolean;
  file_created_at: string;
  created_at: string;
  error?: string;
};

export type TaxonomyNode = {
  id: string;
  label: string;
  children: { id: string; label: string }[];
};

export type LibraryTaxonomist = {
  slug: string;
  name: string;
  taxonomy_name: string;
  scope_path: string;
  cadence: string;
  model?: string;
};

export type LibraryPayload = {
  documents: LibraryDocument[];
  cadence: string;
  taxonomy_name: string;
  tree: TaxonomyNode[];
  inbox: string;
  scope_path?: string;
  taxonomist?: string;
  taxonomists?: LibraryTaxonomist[];
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
  agents?: string[];
};

export type AgentItem = {
  id: string;
  slug: string;
  name: string;
  role: string;
  status: string;
  summary: string;
  model?: string;
  uses_llm?: boolean;
  tools: string[];
  config?: { roster?: boolean; [key: string]: unknown };
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
