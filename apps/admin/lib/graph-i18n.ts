import type { Locale } from "./locale";

type GraphNode = { id: string; label: string; kind: string; detail?: string; layer?: number; row?: number; model?: string; count?: number; hot?: boolean };
type GraphEdge = { from: string; to: string; label?: string };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };

const NODE_ES: Record<string, { label?: string; detail?: string }> = {
  people: { label: "Operadores", detail: "Equipos de 100–1000 personas" },
  channels: { label: "Canales", detail: "Carpeta · IMAP · Telegram" },
  intake: { label: "Entrada" },
  library: { label: "Biblioteca" },
  line: { label: "Línea documental" },
  memory: { label: "GraphRAG" },
  ledger: { label: "Libro" },
  governance: { label: "Gobernanza" },
  start: { label: "Mensaje", detail: "Workspace o API" },
  router: { label: "Orquestador", detail: "Router LangGraph" },
  folder: { label: "Carpeta", detail: "bandeja / documentos" },
  email: { label: "Buzón", detail: "Adjuntos IMAP" },
  telegram: { label: "Telegram", detail: "Archivos / aviso" },
  workspace: { label: "Workspace", detail: ":3000 operadores" },
  admin: { label: "Admin", detail: ":3001 plano de control" },
  watchman: { detail: "Ve archivos nuevos" },
  mailroom: { detail: "Descarga adjuntos" },
  sentinel: { detail: "Brief de bandejas compartidas" },
  courier: { detail: "Telegram entra / sale" },
  teams: { detail: "Webhook apagado" },
  post: { detail: "SMTP apagado" },
  orchestrator: { label: "Orquestador", detail: "Enruta especialistas" },
  parser: { detail: "PDF XLSX PPT PPTX DOC DOCX TXT" },
  reader: { detail: "OCR + dos primeras páginas" },
  taxonomist: { detail: "Taxonomía de dos niveles" },
  ingestor: { detail: "Ejecuta toda la línea" },
  architect: { detail: "Explica el mapa" },
  scribe: { detail: "Sincroniza prompts" },
  triage: { detail: "factura / política / …" },
  chunker: { detail: "Parte y embebe" },
  extractor: { detail: "Campos estructurados" },
  clerk: { detail: "classified/{clase}/{subclase}" },
  reviewer: { detail: "Puerta humana" },
  graphsmith: { detail: "Entidades en Neo4j" },
  recorder: { detail: "Filas SQL" },
  pathfinder: { detail: "Quién está conectado" },
  librarian: { detail: "Responde con GraphRAG" },
  postgres: { detail: "Catálogo + libro SQL" },
  qdrant: { detail: "Vectores de fragmentos" },
  neo4j: { detail: "Grafo de entidades" },
  ollama: { detail: "LLM local" },
  document: { label: "Documento", detail: "PDF / XLSX / PPTX" },
  query: { label: "Pregunta", detail: "Chat del workspace" },
  hybrid: { label: "Recuperación híbrida", detail: "Fragmentos + vecinos" },
  answer: { label: "Respuesta", detail: "Citas + entidades" },
};

const EDGE_ES: Record<string, string> = {
  work: "trabaja",
  govern: "gobierna",
  send: "envía",
  files: "archivos",
  chat: "chat",
  catalog: "catálogo",
  writes: "escribe",
  route: "ruta",
  "opt-in": "a petición",
  calendar: "calendario",
  ocr: "ocr",
  taxonomy: "taxonomía",
  "first pages": "primeras páginas",
  "opt-in RAG": "RAG a petición",
  knowledge: "conocimiento",
  structured: "estructurado",
  exceptions: "excepciones",
  chunks: "fragmentos",
  entities: "entidades",
  answer: "responde",
  rows: "filas",
  notify: "avisa",
  folder: "carpeta",
  email: "correo",
  telegram: "telegram",
  parse: "parsea",
  classify: "clasifica",
  chunk: "fragmenta",
  extract: "extrae",
  "sql rows": "filas SQL",
  organize: "organiza",
  pipeline: "pipeline",
  "who is connected": "quién conecta",
  ask: "pregunta",
  "how does this work": "cómo funciona",
  "sync prompts": "sincroniza prompts",
  "file arrives": "llega archivo",
  attachment: "adjunto",
  letter: "carta",
  "stored letter": "carta guardada",
  "who is this": "quién es",
  brief: "brief",
  alert: "alerta",
  "shared inbox": "bandeja compartida",
  update: "actualiza",
  "saved file": "archivo guardado",
  handoff: "pasa",
  saved: "guardado",
  manage: "gestiona",
  "run line": "ejecuta línea",
  text: "texto",
  file: "archiva",
  upsert: "upsert",
  write: "escribe",
  neighbors: "vecinos",
  "1-hop": "1 salto",
  fields: "campos",
  "low confidence": "poca confianza",
  "ask a human": "pide un humano",
  similar: "similar",
  complete: "completa",
  embed: "embebe",
  "MENTIONS / RELATES": "MENCIONA / RELACIONA",
  lookup: "busca",
  context: "contexto",
  HAS_CHUNK: "TIENE_FRAG",
  MENTIONS: "MENCIONA",
  RELATES: "RELACIONA",
  CO_OCCURS: "CO-OCURRE",
  RELATED: "RELACIONADO",
  SQL: "SQL",
  USES: "USA",
  CALLS: "LLAMA",
  MANAGES: "GESTIONA",
  ROUTES: "ENRUTA",
};

const STORES_ES = {
  postgres: "catálogo de apps/herramientas/agentes + filas SQL extraídas",
  qdrant: "vectores de fragmentos de documentos para RAG",
  neo4j: "GraphRAG: documentos y entidades (los fragmentos viven en Qdrant)",
  disabled: "desactivado",
};

const DETAIL_ES: Record<string, string> = {
  document: "documento",
  entity: "entidad",
  kind: "entidad",
  invoice: "factura",
  contract: "contrato",
  policy: "política",
  report: "informe",
  spreadsheet: "hoja",
  presentation: "presentación",
  form: "formulario",
  other: "otro",
};

function localizeNode(node: GraphNode): GraphNode {
  const extra = NODE_ES[node.id] || {};
  let label = extra.label || node.label;
  let detail = extra.detail || node.detail;
  if (node.kind === "chunk" && /^chunk\s/i.test(node.label)) {
    label = node.label.replace(/^chunk/i, "fragmento");
  }
  if (detail && DETAIL_ES[detail.toLowerCase()]) {
    detail = DETAIL_ES[detail.toLowerCase()];
  }
  if (node.detail && /\bpages\b/i.test(node.detail)) {
    detail = node.detail.replace(/\b1 pages\b/i, "1 página").replace(/\bpages\b/i, "páginas");
  }
  if (node.detail && /entities/i.test(node.detail)) {
    detail = (detail || node.detail)
      .replace(/\bentities\b/g, "entidades")
      .replace(/\bfragments\b/g, "fragmentos");
  }
  return { ...node, label, detail };
}

function localizeGraph(graph: GraphData): GraphData {
  return {
    nodes: graph.nodes.map(localizeNode),
    edges: graph.edges.map((edge) => ({
      ...edge,
      label: edge.label ? EDGE_ES[edge.label] || edge.label : edge.label,
    })),
  };
}

function localizeExplain(text: string): string {
  return text
    .replace("Atrium is a multi-agent platform, not a single chatbot.", "Atrium es una plataforma multiagente, no un chatbot.")
    .replace("Agents (LangGraph runtime):", "Agentes (runtime LangGraph):")
    .replace("Tools:", "Herramientas:")
    .replace(
      "Data: Postgres = catalog + extracted SQL rows, Qdrant = chunk vectors, Neo4j = document graph.",
      "Datos: Postgres = catálogo + filas SQL, Qdrant = vectores, Neo4j = grafo de documentos.",
    )
    .replace("Document pipeline:", "Línea de documentos:")
    .replace("Chat flow:", "Flujo de chat:")
    .replaceAll("(specialist)", "(especialista)")
    .replaceAll("(router)", "(enrutador)")
    .replaceAll("[admin/live]", "[admin/activo]")
    .replaceAll("[experience/live]", "[experiencia/activo]")
    .replaceAll("[tool/planned]", "[herramienta/previsto]")
    .replaceAll("tools=", "herramientas=")
    .replaceAll(" none", " ninguna");
}

export function localizeGraphPayload<T extends {
  architecture: GraphData;
  detail: GraphData;
  rag: { method: GraphData; knowledge: GraphData };
  runtime: GraphData;
  pipeline: GraphData;
  platform: GraphData;
  knowledge: GraphData;
  stores: Record<string, string>;
  explain: string;
}>(data: T, locale: Locale): T {
  if (locale !== "es") {
    return data;
  }
  return {
    ...data,
    architecture: localizeGraph(data.architecture),
    detail: localizeGraph(data.detail),
    runtime: localizeGraph(data.runtime),
    pipeline: localizeGraph(data.pipeline),
    platform: localizeGraph(data.platform),
    knowledge: localizeGraph(data.knowledge),
    rag: {
      method: localizeGraph(data.rag.method),
      knowledge: localizeGraph(data.rag.knowledge),
    },
    stores: {
      postgres: STORES_ES.postgres,
      qdrant: STORES_ES.qdrant,
      neo4j: data.stores.neo4j === "disabled" ? STORES_ES.disabled : STORES_ES.neo4j,
    },
    explain: localizeExplain(data.explain),
  };
}
