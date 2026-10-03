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
  indexed: "en Cerebro",
  pending: "pendiente",
  classified: "clasificado",
  processed: "listo",
  failed: "fallido",
  filed: "archivado",
  received: "recibido",
  read: "leído",
  missing: "ausente",
};

const DOC_STATUS_EN: Record<string, string> = {
  indexed: "in Cerebro",
  pending: "pending",
  classified: "classified",
  processed: "ready",
  failed: "failed",
  filed: "filed",
  received: "received",
  read: "read",
  missing: "missing",
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

const TAXONOMY_ES: Record<string, string> = {
  subsurface: "Subsuelo",
  geology: "Geología",
  geophysics: "Geofísica",
  reservoir: "Yacimiento",
  wells: "Pozos",
  drilling: "Perforación",
  completions: "Completaciones",
  production: "Producción",
  hse: "HSE",
  incidents: "Incidentes",
  procedures: "Procedimientos",
  commercial: "Comercial",
  contracts: "Contratos",
  invoices: "Facturas",
  reports: "Informes",
  corporate: "Corporativo",
  hr: "RRHH",
  it: "IT",
  other: "Otro",
  engineering: "Ingeniería",
  airworthiness: "Aeronavegabilidad",
  maintenance: "Mantenimiento",
  ad_sb: "AD / SB",
  records: "Registros",
  operations: "Operaciones",
  flight: "Vuelo",
  crew: "Tripulación",
  dispatch: "Despacho",
  structures: "Estructuras",
  avionics: "Aviónica",
  engines: "Motores",
  powertrain: "Powertrain",
  chassis: "Chasis",
  body: "Carrocería",
  manufacturing: "Manufactura",
  stamping: "Prensas",
  assembly: "Ensamble",
  quality: "Calidad",
  aftersales: "Postventa",
  warranty: "Garantía",
  service: "Servicio",
  parts: "Refacciones",
  production: "Producción",
  planning: "Planeación",
  lines: "Líneas",
  downtime: "Paros",
  ncr: "NCR",
  inspection: "Inspección",
  calibration: "Calibración",
  pm: "Preventivo",
  breakdown: "Correctivo",
  spare_parts: "Repuestos",
  accounts: "Cuentas",
  bars: "Bares",
  chains: "Cadenas",
  venues: "Locales",
  catalog: "Catálogo",
  beer: "Cerveza",
  wine: "Vino",
  spirits: "Destilados",
  mixers: "Mixers",
  orders: "Pedidos",
  capture: "Captura",
  delivery: "Entrega",
  returns: "Devoluciones",
  warehouse: "Almacén",
  stock: "Stock",
  picking: "Picking",
  empties: "Vacíos",
  trade: "Comercial HORECA",
  pricing: "Tarifas",
  promotions: "Promociones",
  compliance: "Cumplimiento",
  licenses: "Licencias",
  labor: "Laboral",
  payroll: "Nóminas",
  time: "Tiempo",
  disputes: "Conflictos",
  tax: "Fiscal",
  vat: "IVA",
  income: "IRPF",
  corp_tax: "Sociedades",
  filings: "Modelos",
  accounting: "Contabilidad",
  books: "Libros",
  bills: "Facturas",
  closing: "Cierre",
  clients: "Clientes",
  companies: "Sociedades",
  onboarding: "Alta",
  mandates: "Mandatos",
  deadlines: "Plazos",
  calendar: "Calendario",
  notices: "Requerimientos",
  inspections: "Inspecciones",
};

const AGENT_SUMMARY_ES: Record<string, string> = {
  orchestrator: "Pasa cada petición al especialista adecuado.",
  watchman: "Vigila la carpeta de entrada y anota las llegadas. No las manda a Cerebro.",
  mailroom: "Mira el correo y trae adjuntos a la bandeja.",
  parser: "Lee PDF, Excel, PowerPoint, Word y texto por páginas.",
  reader: "Lee las primeras páginas, escribe un resumen y palabras clave.",
  taxonomist: "Pone cada archivo en una clase y una subclase. No lo envía a Cerebro.",
  "taxonomist-aircraft": "Archiva archivos de aeronaves en su propio árbol.",
  "taxonomist-car": "Archiva archivos de automoción en su propio árbol.",
  "taxonomist-factory": "Archiva archivos de fábrica en su propio árbol.",
  "taxonomist-bars": "Archiva la papelería de un distribuidor de bares (cuentas, catálogo, pedidos).",
  "taxonomist-advice": "Archiva expedientes de asesoría laboral y fiscal.",
  triage: "Decide si un archivo va al libro o puede ir a Cerebro.",
  chunker: "Parte el texto para que Cerebro pueda recordarlo.",
  extractor: "Saca números y campos al libro.",
  recorder: "Lee las filas del libro (facturas, hojas).",
  clerk: "Crea el árbol classified y mueve ahí lo etiquetado.",
  ingestor: "Recorre toda la línea: leer, clasificar, libro y, si lo pides, Cerebro.",
  librarian: "Responde con lo que Cerebro ya recuerda.",
  graphsmith: "Anota quién aparece en cada archivo y cómo se relacionan.",
  pathfinder: "Busca en Cerebro quién está conectado con quién.",
  courier: "Telegram: recibe archivos y avisa cuando termina el trabajo.",
  reviewer: "Para lo que necesita a una persona: sin clase, fallos, facturas flojas.",
  architect: "Explica el mapa vivo de cómo se reparte el trabajo.",
  scribe: "Mantiene al día la lista de especialistas.",
};

const AGENT_SUMMARY_EN: Record<string, string> = {
  orchestrator: "Hands each request to the right specialist.",
  watchman: "Watches the drop folder and logs arrivals. Does not send them to Cerebro.",
  mailroom: "Checks mail and brings attachments to the drop folder.",
  parser: "Reads PDF, Excel, PowerPoint, Word, and plain text by page.",
  reader: "Reads the first pages, writes a summary and keywords.",
  taxonomist: "Puts each file in a class and subclass. Does not send it to Cerebro.",
  "taxonomist-aircraft": "Files aircraft documents in their own tree.",
  "taxonomist-car": "Files automotive documents in their own tree.",
  "taxonomist-factory": "Files factory documents in their own tree.",
  "taxonomist-bars": "Files a bar distributor's paperwork (accounts, catalog, orders).",
  "taxonomist-advice": "Files labor and tax advisory dossiers.",
  triage: "Decides if a file goes to the ledger or can go to Cerebro.",
  chunker: "Breaks text so Cerebro can remember it.",
  extractor: "Pulls numbers and fields into the ledger.",
  recorder: "Reads ledger rows (invoices, spreadsheets).",
  clerk: "Creates the classified tree and moves labeled files into it.",
  ingestor: "Runs the whole line: read, file, ledger, and Cerebro if you ask.",
  librarian: "Answers with what Cerebro already remembers.",
  graphsmith: "Notes who appears in each file and how they connect.",
  pathfinder: "Looks in Cerebro for who is connected to whom.",
  courier: "Telegram: receives files and pings when work is done.",
  reviewer: "Holds what needs a person: unfiled, failed, weak invoices.",
  architect: "Explains the live map of how work is handed off.",
  scribe: "Keeps the specialist roster in sync.",
};

const APP_SUMMARY_ES: Record<string, string> = {
  workspace: "El instituto: diario de llegadas, archivo, taller y Cerebro.",
  admin: "Plano de control de salas, habilidades y especialistas.",
};

const APP_SUMMARY_EN: Record<string, string> = {
  workspace: "The institute: daily arrivals, archives, workshop, and Cerebro.",
  admin: "Control plane for rooms, abilities, and specialists.",
};

const APP_NAME_ES: Record<string, string> = {
  workspace: "Instituto",
  admin: "Admin",
};

const APP_NAME_EN: Record<string, string> = {
  workspace: "Institute",
  admin: "Admin",
};

const TOOL_ES: Record<string, { name: string; summary: string }> = {
  "intake.list": {
    name: "Ver carpeta de entrada",
    summary: "Lista los archivos que esperan en la carpeta de entrada.",
  },
  "intake.register": {
    name: "Registrar llegadas",
    summary: "Anota archivos nuevos de la bandeja. No los envía a Cerebro.",
  },
  "intake.poll_mail": {
    name: "Consultar buzón",
    summary: "Descarga adjuntos de correo admitidos a la carpeta de entrada.",
  },
  "documents.parse": {
    name: "Leer archivos",
    summary: "Saca el texto de PDF, Excel, PowerPoint, Word y texto plano.",
  },
  "documents.read": {
    name: "Leer primeras páginas",
    summary: "Lee las primeras páginas y escribe un resumen y palabras clave.",
  },
  "documents.classify": {
    name: "Ordenar por tipo",
    summary: "Factura, contrato, política, informe, hoja y el resto.",
  },
  "taxonomy.run": {
    name: "Archivar por clase",
    summary: "Pone cada archivo en clase y subclase, al ritmo que elijas.",
  },
  "taxonomy.list": {
    name: "Ver el archivo",
    summary: "Lista archivos del archivo con filtros.",
  },
  "taxonomy.get": {
    name: "Ficha de archivo",
    summary: "Muestra resumen, tamaño, fecha, ruta y palabras clave.",
  },
  "documents.chunk": {
    name: "Preparar recuerdos",
    summary: "Parte el texto para que Cerebro pueda recordarlo.",
  },
  "documents.file": {
    name: "Guardar en su clase",
    summary: "Clerk mueve lo etiquetado a classified/{clase}/{subclase}.",
  },
  "folders.ensure": {
    name: "Crear carpetas clasificadas",
    summary: "Crea classified/{clase}/{subclase} desde el árbol vivo. No mueve archivos.",
  },
  "folders.list": {
    name: "Ver carpetas clasificadas",
    summary: "Lee el árbol organizado classified/ en el servidor.",
  },
  "documents.list": {
    name: "Ver archivos",
    summary: "Lista archivos y dónde van en la línea.",
  },
  "knowledge.ingest": {
    name: "Ejecutar la línea",
    summary: "Lee, clasifica, pasa al libro y, si lo pides, envía a Cerebro.",
  },
  "knowledge.promote": {
    name: "Enviar a Cerebro",
    summary: "Cerebro solo recuerda los archivos que eliges. El archivo no manda todo.",
  },
  "knowledge.search": {
    name: "Preguntar a Cerebro",
    summary: "Busca en lo que ya elegiste recordar.",
  },
  "knowledge.graph_build": {
    name: "Anotar conexiones",
    summary: "Anota quién aparece en cada archivo y cómo se relacionan.",
  },
  "knowledge.graph_search": {
    name: "Buscar quién conoce a quién",
    summary: "Pregunta a Cerebro por personas, sitios y cómo se conectan.",
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
    name: "Ver excepciones",
    summary: "Muestra lo que todavía necesita a una persona.",
  },
  "records.extract": {
    name: "Pasar al libro",
    summary: "Convierte facturas y hojas en filas del libro.",
  },
  "records.list": {
    name: "Ver el libro",
    summary: "Lee las filas que ya están en el libro.",
  },
  "models.list": {
    name: "Listar voces",
    summary: "Lista las voces disponibles en esta máquina.",
  },
  "platform.explain": {
    name: "Explicar el instituto",
    summary: "Describe salas, especialistas, habilidades y cómo se reparte el trabajo.",
  },
  "docs.sync": {
    name: "Sincronizar el equipo",
    summary: "Mantiene al día la lista de especialistas.",
  },
};

const TOOL_EN: Record<string, { name: string; summary: string }> = {
  "intake.list": { name: "See drop folder", summary: "Lists files waiting in the drop folder." },
  "intake.register": { name: "Log arrivals", summary: "Logs new files from the drop folder. Does not send them to Cerebro." },
  "intake.poll_mail": { name: "Check mailbox", summary: "Brings allowed mail attachments into the drop folder." },
  "documents.parse": { name: "Read files", summary: "Pulls text from PDF, Excel, PowerPoint, Word, CSV, and TXT." },
  "documents.read": { name: "Read first pages", summary: "Reads the first pages and writes a summary and keywords." },
  "documents.classify": { name: "Sort by type", summary: "Invoice, contract, policy, report, spreadsheet, and the rest." },
  "taxonomy.run": { name: "File by class", summary: "Puts each file in a class and subclass on the cadence you set." },
  "taxonomy.list": { name: "List the archives", summary: "Lists archived files with filters." },
  "taxonomy.get": { name: "File card", summary: "Shows summary, size, created date, full path, and keywords." },
  "documents.chunk": { name: "Prepare memories", summary: "Breaks the text so Cerebro can remember it." },
  "documents.file": { name: "Put away", summary: "Clerk moves labeled files into classified/{class}/{subclass}." },
  "folders.ensure": { name: "Create classified folders", summary: "Creates classified/{class}/{subclass} from the live tree. Does not move files." },
  "folders.list": { name: "See classified folders", summary: "Reads the organized classified/ tree on the server." },
  "documents.list": { name: "See files", summary: "Lists files and where they are in the line." },
  "knowledge.ingest": { name: "Run the line", summary: "Reads, files, writes the ledger, and sends to Cerebro if you ask." },
  "knowledge.promote": { name: "Send to Cerebro", summary: "Cerebro only remembers the files you choose. The archives do not dump everything." },
  "knowledge.search": { name: "Ask Cerebro", summary: "Looks through what you already chose to remember." },
  "knowledge.graph_build": { name: "Note connections", summary: "Notes who appears in each file and how they relate." },
  "knowledge.graph_search": { name: "Who knows whom", summary: "Asks Cerebro about people, places, and how they connect." },
  "telegram.poll": { name: "Check Telegram", summary: "Brings in files sent to the bot and lists recent texts." },
  "telegram.send": { name: "Send Telegram", summary: "Sends a status ping to the configured Telegram chat." },
  "review.list": { name: "List exceptions", summary: "Shows files that still need a person." },
  "records.extract": { name: "Pull ledger rows", summary: "Turns invoices and spreadsheets into rows." },
  "records.list": { name: "List ledger rows", summary: "Reads structured rows already in the ledger." },
  "models.list": { name: "List voices", summary: "Lists the voices available on this machine." },
  "platform.explain": { name: "Explain the institute", summary: "Describes rooms, specialists, abilities, and how work is handed off." },
  "docs.sync": { name: "Sync the roster", summary: "Keeps the specialist list in sync." },
};

function pick(locale: Locale, esMap: Record<string, string>, key: string, fallback: string, enMap?: Record<string, string>): string {
  if (!key) {
    return fallback;
  }
  if (locale === "es") {
    return esMap[key] || fallback;
  }
  return (enMap && enMap[key]) || fallback;
}

export function localizeRole(role: string, locale: Locale): string {
  return pick(locale, ROLE_ES, role, role);
}

export function localizeKind(kind: string, locale: Locale): string {
  return pick(locale, KIND_ES, kind, kind);
}

export function localizeAgentSummary(slug: string, fallback: string, locale: Locale): string {
  return pick(locale, AGENT_SUMMARY_ES, slug, fallback, AGENT_SUMMARY_EN);
}

export function localizeAppSummary(slug: string, fallback: string, locale: Locale): string {
  return pick(locale, APP_SUMMARY_ES, slug, fallback, APP_SUMMARY_EN);
}

export function localizeAppName(slug: string, fallback: string, locale: Locale): string {
  return pick(locale, APP_NAME_ES, slug, fallback, APP_NAME_EN);
}

export function localizeToolName(slug: string, fallback: string, locale: Locale): string {
  const overlay = locale === "es" ? TOOL_ES : TOOL_EN;
  return overlay[slug]?.name || fallback;
}

export function localizeToolSummary(slug: string, fallback: string, locale: Locale): string {
  const overlay = locale === "es" ? TOOL_ES : TOOL_EN;
  return overlay[slug]?.summary || fallback;
}

export function localizeDocStatus(status: string, locale: Locale): string {
  return pick(locale, DOC_STATUS_ES, status, status, DOC_STATUS_EN);
}

export function workshopPhase(status: string): "queued" | "classified" | "error" {
  if (["failed", "missing", "error"].includes(status || "")) {
    return "error";
  }
  if (["classified", "filed", "indexed", "processed"].includes(status || "")) {
    return "classified";
  }
  return "queued";
}

export function classifyNoteKey(method: string, note: string): { key: string; model?: string } {
  const raw = (note || "").trim();
  if (raw === "missing" || raw.endsWith(":missing")) {
    return { key: "docs.reason.missing" };
  }
  if (method === "llm") {
    return { key: "docs.reason.llm", model: raw || "LLM" };
  }
  if (raw.includes("timeout")) {
    return { key: "docs.reason.timeout" };
  }
  if (raw.includes("filename")) {
    return { key: "docs.reason.filename" };
  }
  if (raw.includes("keywords")) {
    return { key: "docs.reason.keywords" };
  }
  if (raw.startsWith("off")) {
    return { key: "docs.reason.off" };
  }
  return { key: "" };
}

export function formatClassifyNote(
  method: string,
  note: string,
  t: (key: string, vars?: Record<string, string | number>) => string,
): string {
  const parsed = classifyNoteKey(method, note);
  if (!parsed.key) {
    return note || "—";
  }
  return parsed.model ? t(parsed.key, { model: parsed.model }) : t(parsed.key);
}

export function localizeDocType(docType: string, locale: Locale): string {
  return pick(locale, DOC_TYPE_ES, docType, docType);
}

export function localizeSource(source: string, locale: Locale): string {
  return pick(locale, SOURCE_ES, source, source);
}

export function localizeTaxonomy(slug: string, locale: Locale, fallback?: string): string {
  return pick(locale, TAXONOMY_ES, slug, fallback || slug);
}
