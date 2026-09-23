import type { Locale } from "./locale";

const ROLE_ES: Record<string, string> = {
  router: "enrutador",
  specialist: "especialista",
};

const KIND_ES: Record<string, string> = {
  experience: "experiencia",
  admin: "admin",
  tool: "herramienta",
  builtin: "incluida",
  http: "HTTP",
};

const DOC_STATUS_ES: Record<string, string> = {
  indexed: "indexado",
  pending: "pendiente",
  classified: "clasificado",
  processed: "procesado",
  failed: "fallido",
  filed: "archivado",
};

const DOC_TYPE_ES: Record<string, string> = {
  invoice: "factura",
  contract: "contrato",
  policy: "política",
  report: "informe",
  spreadsheet: "hoja de cálculo",
  presentation: "presentación",
  form: "formulario",
  other: "otro",
};

const SOURCE_ES: Record<string, string> = {
  folder: "carpeta",
  email: "correo",
  telegram: "telegram",
  inbox: "bandeja",
  drop: "carpeta",
};

const AGENT_SUMMARY_ES: Record<string, string> = {
  orchestrator: "Enruta cada petición a un agente especialista.",
  watchman: "Vigila la carpeta de entrada e informa de los archivos que llegan.",
  mailroom: "Consulta IMAP y descarga adjuntos PDF/XLSX/PPTX a la bandeja del servidor.",
  parser: "Lee PDF, Excel, PowerPoint y Word y los pasa a texto.",
  triage: "Clasifica cada archivo para RAG o para extraerlo a SQL.",
  chunker: "Parte el texto y envía fragmentos a Qdrant. Graphsmith cuelga entidades de esos fragmentos.",
  extractor: "Pide campos estructurados al LLM (o a heurísticas) y los escribe en Postgres.",
  recorder: "Lee la tabla SQL de filas extraídas (facturas, líneas de hoja de cálculo).",
  clerk: "Archiva documentos procesados en carpetas classified/{type}.",
  ingestor: "Ejecuta toda la línea: parsear → clasificar → fragmentar → grafo GraphRAG → extraer/SQL → archivar.",
  librarian: "Responde con GraphRAG: fragmentos similares más entidades relacionadas de Neo4j.",
  graphsmith: "Convierte fragmentos en un grafo de conocimiento: entidades, menciones y relaciones en Neo4j.",
  pathfinder: "Recuperación GraphRAG: quién está conectado con quién y qué archivos mencionan una entidad.",
  courier: "Canal Telegram: recibe archivos en la bandeja y avisa cuando termina el trabajo.",
  reviewer: "Puerta humana: archivos sin clasificar, ingestas fallidas, filas de factura débiles.",
  architect: "Explica el grafo vivo de la plataforma para que humanos y agentes vean cómo se enruta el trabajo.",
  scribe: "Mantiene el roster de AGENTS.md y HOW_IT_WORKS alineado con el catálogo vivo de Postgres.",
};

const APP_SUMMARY_ES: Record<string, string> = {
  workspace: "Portal para operadores: documentos, chat de conocimiento y filas extraídas.",
  admin: "Plano de control de apps, herramientas y agentes.",
};

const TOOL_ES: Record<string, { name: string; summary: string }> = {
  "intake.list": {
    name: "Ver carpeta de entrada",
    summary: "Lista los archivos que esperan en la carpeta de entrada.",
  },
  "intake.poll_mail": {
    name: "Consultar buzón",
    summary: "Descarga adjuntos de correo admitidos a la carpeta de entrada.",
  },
  "documents.parse": {
    name: "Parsear documentos",
    summary: "Extrae texto de PDF, XLSX, PPTX, DOCX y CSV.",
  },
  "documents.classify": {
    name: "Clasificar documentos",
    summary: "Triage: factura, contrato, política, informe, hoja, presentación, formulario, otro.",
  },
  "documents.chunk": {
    name: "Fragmentar para RAG",
    summary: "Parte el texto parseado y guarda fragmentos en Qdrant.",
  },
  "documents.file": {
    name: "Archivar documentos",
    summary: "Mueve archivos procesados a carpetas classified/{type}.",
  },
  "documents.list": {
    name: "Listar documentos",
    summary: "Lista archivos y el estado de su pipeline.",
  },
  "knowledge.ingest": {
    name: "Ejecutar pipeline",
    summary: "Parsea, clasifica, fragmenta, extrae a SQL, indexa y archiva cada documento pendiente.",
  },
  "knowledge.search": {
    name: "Búsqueda GraphRAG",
    summary: "Recuperación híbrida: vectores Qdrant más vecinos de entidades en Neo4j.",
  },
  "knowledge.graph_build": {
    name: "Construir grafo de conocimiento",
    summary: "Extrae entidades y relaciones de documentos a Neo4j (Graphsmith).",
  },
  "knowledge.graph_search": {
    name: "Buscar entidades",
    summary: "Consulta entidades y vecinos a 1 salto en Neo4j (Pathfinder).",
  },
  "telegram.poll": {
    name: "Consultar Telegram",
    summary: "Descarga archivos que enviaron al bot y lista textos recientes.",
  },
  "telegram.send": {
    name: "Enviar Telegram",
    summary: "Envía un mensaje de estado al chat de Telegram configurado.",
  },
  "review.list": {
    name: "Listar excepciones",
    summary: "Muestra archivos y extractos que necesitan a una persona (Reviewer).",
  },
  "records.extract": {
    name: "Extraer registros",
    summary: "Convierte facturas y hojas de cálculo en filas estructuradas (heurística, LLM opcional).",
  },
  "records.list": {
    name: "Listar filas SQL",
    summary: "Lee las filas estructuradas escritas en Postgres.",
  },
  "models.list": {
    name: "Listar modelos",
    summary: "Lista los modelos de Ollama disponibles en este servidor.",
  },
  "platform.explain": {
    name: "Explicar plataforma",
    summary: "Describe apps, agentes, herramientas y cómo se enruta el trabajo.",
  },
  "docs.sync": {
    name: "Sincronizar prompt de contexto",
    summary: "Reescribe el roster de AGENTS.md y HOW_IT_WORKS desde el catálogo vivo (Scribe).",
  },
};

function pick(locale: Locale, map: Record<string, string>, key: string, fallback: string): string {
  if (locale !== "es" || !key) {
    return fallback;
  }
  return map[key] || fallback;
}

export function localizeRole(role: string, locale: Locale): string {
  return pick(locale, ROLE_ES, role, role);
}

export function localizeKind(kind: string, locale: Locale): string {
  return pick(locale, KIND_ES, kind, kind);
}

export function localizeAgentSummary(slug: string, fallback: string, locale: Locale): string {
  return pick(locale, AGENT_SUMMARY_ES, slug, fallback);
}

export function localizeAppSummary(slug: string, fallback: string, locale: Locale): string {
  return pick(locale, APP_SUMMARY_ES, slug, fallback);
}

export function localizeToolName(slug: string, fallback: string, locale: Locale): string {
  if (locale !== "es") {
    return fallback;
  }
  return TOOL_ES[slug]?.name || fallback;
}

export function localizeToolSummary(slug: string, fallback: string, locale: Locale): string {
  if (locale !== "es") {
    return fallback;
  }
  return TOOL_ES[slug]?.summary || fallback;
}

export function localizeDocStatus(status: string, locale: Locale): string {
  return pick(locale, DOC_STATUS_ES, status, status);
}

export function localizeDocType(docType: string, locale: Locale): string {
  return pick(locale, DOC_TYPE_ES, docType, docType);
}

export function localizeSource(source: string, locale: Locale): string {
  return pick(locale, SOURCE_ES, source, source);
}
