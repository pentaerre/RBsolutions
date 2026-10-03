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
  watchman: "Vigila la carpeta de entrada (con subcarpetas) y registra llegadas. No las vuelca al RAG.",
  mailroom: "Consulta IMAP, descarga adjuntos (PDF, Office, texto) a la bandeja del servidor y guarda la carta para Sentinel.",
  sentinel: "Brief para dirección sobre bandejas compartidas. Marca riesgo legal, peticiones comerciales sin atender y fuga o incumplimiento de plazo. Cruza la parte con Neo4j y el libro SQL. Reviewer retiene el brief. No llama al modelo de 32b.",
  parser: "Lee PDF, Excel, PowerPoint, Word y texto plano por páginas. Reader luego hace OCR y resume.",
  reader: "OCR / extracción best-effort de las dos primeras páginas: PDF, PPT/PPTX, DOC/DOCX, TXT. Escribe resumen y palabras clave.",
  taxonomist: "Taxonomía de dos niveles E&P desde ruta + nombre + texto. Mismo oficio que Aircraft/Car/Factory; árbol distinto. No envía archivos al RAG.",
  "taxonomist-aircraft": "Taxonomía de dos niveles Aircraft. Solo archivos bajo inbox/aircraft. Mismo oficio que el Taxonomist E&P.",
  "taxonomist-car": "Taxonomía de dos niveles Car. Solo archivos bajo inbox/car. Mismo oficio que el Taxonomist E&P.",
  "taxonomist-factory": "Taxonomía de dos niveles Factory. Solo archivos bajo inbox/factory. Mismo oficio que el Taxonomist E&P.",
  "taxonomist-bars": "Taxonomía de dos niveles para distribuidores HORECA. Solo archivos bajo inbox/bars. Desactivada salvo que sea el árbol vendido.",
  "taxonomist-advice": "Taxonomía de dos niveles laboral + fiscal. Solo archivos bajo inbox/advice. Desactivada salvo que sea el árbol vendido.",
  triage: "Clasifica cada archivo para RAG o para extraerlo a SQL.",
  chunker: "Parte el texto y envía fragmentos a Qdrant. Graphsmith cuelga entidades de esos fragmentos.",
  extractor: "Pide campos estructurados al LLM (o a heurísticas) y los escribe en Postgres.",
  recorder: "Lee la tabla SQL de filas extraídas (facturas, líneas de hoja de cálculo).",
  clerk: "Crea classified/{clase}/{subclase} desde el Taxonomist vivo y mueve ahí lo etiquetado. También archiva la línea IDP por tipo.",
  ingestor: "Ejecuta toda la línea: parsear → clasificar → fragmentar → grafo GraphRAG → extraer/SQL → archivar.",
  librarian: "Responde con GraphRAG: fragmentos similares más entidades relacionadas de Neo4j.",
  graphsmith: "Convierte fragmentos en un grafo de conocimiento: entidades, menciones y relaciones en Neo4j.",
  pathfinder: "Recuperación GraphRAG: quién está conectado con quién y qué archivos mencionan una entidad.",
  courier: "Chatbot de Telegram: recibe archivos y entrega los briefs de Sentinel con asunto y remitente.",
  teams: "Worker de Teams para el mismo brief. Apagado hasta activarlo. El webhook va en TEAMS_WEBHOOK_URL y no entra en el grafo.",
  post: "Worker de correo saliente para el mismo brief. Apagado hasta activarlo. SMTP_HOST y SMTP_TO quedan en el entorno.",
  reviewer: "Puerta humana: archivos sin clasificar, ingestas fallidas, filas de factura débiles y briefs de dirección abiertos.",
  architect: "Explica el grafo vivo de la plataforma para que humanos y agentes vean cómo se enruta el trabajo.",
  scribe: "Mantiene el roster de AGENTS.md y HOW_IT_WORKS alineado con el catálogo vivo de Postgres.",
};

const APP_SUMMARY_ES: Record<string, string> = {
  workspace: "Portal para operadores: calendario de llegadas, biblioteca de taxonomía, documentos y chat de conocimiento.",
  admin: "Plano de control de apps, herramientas y agentes.",
};

const TOOL_ES: Record<string, { name: string; summary: string }> = {
  "intake.list": {
    name: "Ver carpeta de entrada",
    summary: "Lista los archivos que esperan en la carpeta de entrada.",
  },
  "intake.register": {
    name: "Registrar llegadas",
    summary: "Registra archivos nuevos de la bandeja (incluidas subcarpetas) sin enviarlos al RAG.",
  },
  "intake.poll_mail": {
    name: "Consultar buzón",
    summary: "Descarga adjuntos de correo admitidos a la carpeta de entrada.",
  },
  "signals.scan": {
    name: "Escanear bandejas compartidas",
    summary: "Juzga las cartas guardadas: riesgo legal, petición comercial sin atender y fuga. Cruza Neo4j y el libro SQL.",
  },
  "signals.list": {
    name: "Listar briefs de dirección",
    summary: "Lista las señales operativas abiertas que esperan a una persona.",
  },
  "teams.send": {
    name: "Enviar a Teams",
    summary: "Publica un brief en un canal de Teams. La URL del webhook queda en TEAMS_WEBHOOK_URL.",
  },
  "mail.send": {
    name: "Enviar correo",
    summary: "Envía un brief por correo. La configuración SMTP queda en el entorno del servidor.",
  },
  "documents.parse": {
    name: "Parsear documentos",
    summary: "Extrae texto de PDF, XLSX, PPTX, PPT, DOCX, DOC, CSV y TXT.",
  },
  "documents.read": {
    name: "Leer primeras páginas",
    summary: "OCR/extrae las dos primeras páginas, escribe resumen y palabras clave (Reader).",
  },
  "documents.classify": {
    name: "Clasificar documentos",
    summary: "Triage: factura, contrato, política, informe, hoja, presentación, formulario, otro.",
  },
  "taxonomy.run": {
    name: "Ejecutar taxonomía",
    summary: "Archivo de dos niveles desde ruta + nombre + texto, en la cadencia configurada.",
  },
  "taxonomy.list": {
    name: "Listar taxonomía",
    summary: "Lista documentos de la biblioteca con filtros.",
  },
  "taxonomy.get": {
    name: "Ficha de documento",
    summary: "Muestra resumen, bytes, fecha de creación, ruta absoluta y palabras clave.",
  },
  "documents.chunk": {
    name: "Fragmentar para RAG",
    summary: "Parte el texto parseado y guarda fragmentos en Qdrant.",
  },
  "documents.file": {
    name: "Archivar documentos",
    summary: "Clerk mueve lo clasificado a classified/{clase}/{subclase}. Lo de la línea IDP, por tipo.",
  },
  "folders.ensure": {
    name: "Crear carpetas clasificadas",
    summary: "Crea classified/{clase}/{subclase} desde el árbol del Taxonomist vivo. No mueve archivos.",
  },
  "folders.list": {
    name: "Listar carpetas clasificadas",
    summary: "Lee el árbol organizado classified/ en disco.",
  },
  "documents.list": {
    name: "Listar documentos",
    summary: "Lista archivos y el estado de su pipeline.",
  },
  "knowledge.ingest": {
    name: "Ejecutar pipeline",
    summary: "Parsea, clasifica, fragmenta, extrae a SQL, indexa y archiva cada documento pendiente.",
  },
  "knowledge.promote": {
    name: "Promover a GraphRAG",
    summary: "Indexa solo los documentos que eligió un operador. La biblioteca no vuelca todo al RAG.",
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
