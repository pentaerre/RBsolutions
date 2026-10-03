from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Agent

# Sample two-level taxonomy for an exploration & production operator.
# Per-client trees live on the Taxonomist agent config_json.
DEFAULT_TAXONOMY: dict[str, Any] = {
    "name": "E&P",
    "cadence": "hour",
    "levels": [
        {
            "id": "subsurface",
            "label": "Subsurface",
            "keywords": ["subsurface", "geolog", "seismic", "reservor", "petrophys", "subsuelo"],
            "children": [
                {
                    "id": "geology",
                    "label": "Geology",
                    "keywords": ["geology", "geologia", "well log", "core", "formation", "stratig", "sediment"],
                },
                {
                    "id": "geophysics",
                    "label": "Geophysics",
                    "keywords": ["geophys", "geofis", "seismic", "sismica", "gravity", "magnet", "velocity"],
                },
                {
                    "id": "reservoir",
                    "label": "Reservoir",
                    "keywords": ["reservoir", "yacimiento", "porosity", "permeab", "pvt", "simulation", "ooip"],
                },
            ],
        },
        {
            "id": "wells",
            "label": "Wells",
            "keywords": ["well", "pozo", "drill", "perfor", "completion", "workover"],
            "children": [
                {
                    "id": "drilling",
                    "label": "Drilling",
                    "keywords": ["drill", "perforacion", "bha", "mud", "lodo", "casing", "bit", "wits", "td "],
                },
                {
                    "id": "completions",
                    "label": "Completions",
                    "keywords": ["completion", "completacion", "perforat", "frac", "packer", "stimulat"],
                },
                {
                    "id": "production",
                    "label": "Production",
                    "keywords": ["production", "produccion", "well test", "bopd", "gas rate", "alloct", "choke"],
                },
            ],
        },
        {
            "id": "hse",
            "label": "HSE",
            "keywords": ["hse", "safety", "seguridad", "environment", "ambiental", "incident"],
            "children": [
                {
                    "id": "incidents",
                    "label": "Incidents",
                    "keywords": ["incident", "near miss", "spill", "derrame", "injury", "accidente"],
                },
                {
                    "id": "procedures",
                    "label": "Procedures",
                    "keywords": ["procedure", "procedimiento", "permit", "jsa", "sop", "ptw"],
                },
            ],
        },
        {
            "id": "commercial",
            "label": "Commercial",
            "keywords": ["contract", "invoice", "commercial", "comercial", "farm-in", "partner"],
            "children": [
                {
                    "id": "contracts",
                    "label": "Contracts",
                    "keywords": ["contract", "contrato", "psa", "joa", "spa", "farmout"],
                },
                {
                    "id": "invoices",
                    "label": "Invoices",
                    "keywords": ["invoice", "factura", "afe", "cost", "billing", "po "],
                },
                {
                    "id": "reports",
                    "label": "Reports",
                    "keywords": ["report", "informe", "monthly", "board", "partner", "weekly"],
                },
            ],
        },
        {
            "id": "corporate",
            "label": "Corporate",
            "keywords": ["hr", "it", "policy", "corporate", "rrhh", "politica"],
            "children": [
                {
                    "id": "hr",
                    "label": "HR",
                    "keywords": ["hr", "rrhh", "leave", "payroll", "staff", "nomina", "personal"],
                },
                {
                    "id": "it",
                    "label": "IT",
                    "keywords": ["it", "network", "access", "software", "red", "servidor"],
                },
                {"id": "other", "label": "Other", "keywords": ["misc", "other", "otro", "general"]},
            ],
        },
    ],
}


def _g(node_id: str, label: str, keywords: list[str], children: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": node_id, "label": label, "keywords": keywords, "children": children}


def _c(node_id: str, label: str, keywords: list[str]) -> dict[str, Any]:
    return {"id": node_id, "label": label, "keywords": keywords}


AIRCRAFT_TAXONOMY: dict[str, Any] = {
    "name": "Aircraft",
    "levels": [
        _g("airworthiness", "Airworthiness", ["airworth", "aeronaveg", "camo", "part 145"], [
            _c("maintenance", "Maintenance", ["maintenance", "mantenimiento", "mro", "hangar", "work order"]),
            _c("ad_sb", "AD / SB", ["airworthiness directive", "service bulletin", "ad ", "sb "]),
            _c("records", "Records", ["logbook", "bitacora", "crs", "release to service", "hours cycles"]),
        ]),
        _g("operations", "Operations", ["operations", "operacion", "flight ops"], [
            _c("flight", "Flight", ["flight", "vuelo", "ofp", "loadsheet", "fuel"]),
            _c("crew", "Crew", ["crew", "tripul", "roster", "fdtl", "pilot"]),
            _c("dispatch", "Dispatch", ["dispatch", "despacho", "notam", "mel", "weather"]),
        ]),
        _g("engineering", "Engineering", ["engineering", "ingenier", "design"], [
            _c("structures", "Structures", ["structure", "estructura", "fatigue", "corrosion"]),
            _c("avionics", "Avionics", ["avionic", "avionica", "fms", "transponder"]),
            _c("engines", "Engines", ["engine", "motor", "apu", "thrust", "ehm"]),
        ]),
        _g("commercial", "Commercial", ["contract", "invoice", "lease", "comercial"], [
            _c("contracts", "Contracts", ["contract", "contrato", "lease", "power by the hour"]),
            _c("invoices", "Invoices", ["invoice", "factura", "billing"]),
        ]),
        _g("corporate", "Corporate", ["hr", "policy", "corporate"], [
            _c("hr", "HR", ["hr", "rrhh", "training", "sms"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
    ],
}

CAR_TAXONOMY: dict[str, Any] = {
    "name": "Car",
    "levels": [
        _g("engineering", "Engineering", ["engineering", "ingenier", "design", "cad"], [
            _c("powertrain", "Powertrain", ["engine", "motor", "gearbox", "ev", "battery", "powertrain"]),
            _c("chassis", "Chassis", ["chassis", "chasis", "suspension", "brake", "steering"]),
            _c("body", "Body", ["body", "carroceria", "styling", "interior", "nvh"]),
        ]),
        _g("manufacturing", "Manufacturing", ["manufactur", "plant", "factory", "produccion"], [
            _c("stamping", "Stamping", ["stamp", "prensa", "body in white", "weld"]),
            _c("assembly", "Assembly", ["assembly", "ensamble", "line", "andons"]),
            _c("quality", "Quality", ["quality", "calidad", "ppap", "fmea", "ncr"]),
        ]),
        _g("aftersales", "Aftersales", ["aftersales", "postventa", "dealer"], [
            _c("warranty", "Warranty", ["warranty", "garantia", "claim", "recall"]),
            _c("service", "Service", ["service", "taller", "repair", "diagnostic"]),
            _c("parts", "Parts", ["spare", "parts", "repuesto", "catalog"]),
        ]),
        _g("commercial", "Commercial", ["contract", "invoice", "oem", "comercial"], [
            _c("contracts", "Contracts", ["contract", "contrato", "supplier", "rfq"]),
            _c("invoices", "Invoices", ["invoice", "factura", "billing"]),
        ]),
        _g("corporate", "Corporate", ["hr", "policy", "corporate"], [
            _c("hr", "HR", ["hr", "rrhh", "leave", "payroll"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
    ],
}

BARS_TAXONOMY: dict[str, Any] = {
    "name": "Bars",
    "levels": [
        _g("accounts", "Accounts", ["account", "cliente", "bar", "horeca", "on trade", "local"], [
            _c("bars", "Bars", ["bar", "bares", "cantina", "terraza", "pub", "cocteleria"]),
            _c("chains", "Chains", ["cadena", "grupo", "franquicia", "multiunidad", "hosteleria"]),
            _c("venues", "Venues", ["hotel", "evento", "discoteca", "ocio", "sala", "catering"]),
        ]),
        _g("catalog", "Catalog", ["catalogo", "producto", "sku", "marca", "portfolio"], [
            _c("beer", "Beer", ["cerveza", "barril", "keg", "caña", "lager", "ipa"]),
            _c("wine", "Wine", ["vino", "cava", "bodega", "denominacion", "rioja"]),
            _c("spirits", "Spirits", ["licor", "destilado", "gin", "ron", "whisky", "vodka", "tequila"]),
            _c("mixers", "Mixers", ["mixer", "refresco", "sin alcohol", "agua", "tonica", "soft"]),
        ]),
        _g("orders", "Orders", ["pedido", "order", "preventa", "comanda"], [
            _c("capture", "Capture", ["toma de pedido", "preventa", "captura", "handheld", "ruta comercial"]),
            _c("delivery", "Delivery", ["entrega", "albaran", "reparto", "ruta", "drop"]),
            _c("returns", "Returns", ["devolucion", "vacios", "envases", "cascos", "rotura"]),
        ]),
        _g("warehouse", "Warehouse", ["almacen", "warehouse", "logistica", "stock"], [
            _c("stock", "Stock", ["inventario", "existencias", "stock", "rotacion"]),
            _c("picking", "Picking", ["picking", "carga", "muelle", "camion"]),
            _c("empties", "Empties", ["vacios", "barriles", "botellas", "keg vacio", "envase"]),
        ]),
        _g("trade", "Trade", ["comercial", "tarifa", "rappel", "promo"], [
            _c("pricing", "Pricing", ["tarifa", "precio", "descuento", "rappel", "rappel"]),
            _c("invoices", "Invoices", ["factura", "abono", "albaran valorado", "iva"]),
            _c("promotions", "Promotions", ["promo", "campaña", "pos", "material", "impulsar"]),
        ]),
        _g("compliance", "Compliance", ["licencia", "sanidad", "alcohol", "cumplimiento"], [
            _c("licenses", "Licenses", ["licencia", "alcohol", "sanidad", "apertura", "horeca"]),
            _c("quality", "Quality", ["caducidad", "lote", "calidad", "frio", "rotura cadena"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
    ],
}

ADVICE_TAXONOMY: dict[str, Any] = {
    "name": "Advice",
    "levels": [
        _g("labor", "Labor", ["laboral", "trabajo", "ss", "seguridad social", "contrato"], [
            _c("contracts", "Contracts", ["contrato", "alta", "baja", "ss", "afiliacion", "tgss"]),
            _c("payroll", "Payroll", ["nomina", "irpf", "cotizacion", "salario", "finiquito"]),
            _c("time", "Time", ["fichaje", "horas", "ausencia", "erte", "vacaciones", "baja medica"]),
            _c("disputes", "Disputes", ["despido", "smac", "demanda", "inspeccion de trabajo", "sancion laboral"]),
        ]),
        _g("tax", "Tax", ["fiscal", "impuesto", "hacienda", "aeat", "tribut"], [
            _c("vat", "VAT", ["iva", "303", "390", "recargo de equivalencia", "repercutido"]),
            _c("income", "Income tax", ["irpf", "111", "115", "130", "131", "retencion"]),
            _c("corp_tax", "Corporate tax", ["impuesto de sociedades", "is ", "200", "202", "pagos fraccionados"]),
            _c("filings", "Filings", ["modelo", "presentacion", "borrador", "telematica", "certificado digital"]),
        ]),
        _g("accounting", "Accounting", ["contab", "asiento", "pgc", "cuenta"], [
            _c("books", "Books", ["diario", "mayor", "asiento", "plan contable"]),
            _c("bills", "Bills", ["factura", "ticket", "gasto", "proveedor", "ingreso"]),
            _c("closing", "Closing", ["cierre", "amortizacion", "inventario", "balances"]),
        ]),
        _g("clients", "Clients", ["cliente", "expediente", "mandat", "asesoria"], [
            _c("companies", "Companies", ["sociedad", "sl", "autonomo", "comunidad", "cif"]),
            _c("onboarding", "Onboarding", ["alta cliente", "escritura", "poder", "kyc", "documentacion"]),
            _c("mandates", "Mandates", ["representacion", "apoderamiento", "certificado", "clave pin"]),
        ]),
        _g("deadlines", "Deadlines", ["plazo", "vencimiento", "calendario", "requerimiento"], [
            _c("calendar", "Calendar", ["plazo", "vencimiento", "calendario fiscal", "fecha limite"]),
            _c("notices", "Notices", ["requerimiento", "notificacion", "sancion", "providencia"]),
            _c("inspections", "Inspections", ["inspeccion", "hacienda", "comprobacion", "acta"]),
        ]),
        _g("corporate", "Corporate", ["interno", "despacho", "rrhh"], [
            _c("hr", "HR", ["rrhh", "despacho", "honorarios", "encargo"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
    ],
}

FACTORY_TAXONOMY: dict[str, Any] = {
    "name": "Factory",
    "levels": [
        _g("production", "Production", ["production", "produccion", "mes", "oee"], [
            _c("planning", "Planning", ["plan", "schedule", "mrp", "work order"]),
            _c("lines", "Lines", ["line", "linea", "shift", "throughput"]),
            _c("downtime", "Downtime", ["downtime", "parada", "breakdown", "oee"]),
        ]),
        _g("quality", "Quality", ["quality", "calidad", "iso"], [
            _c("ncr", "NCR", ["ncr", "nonconformance", "defect", "scrap"]),
            _c("inspection", "Inspection", ["inspect", "inspeccion", "incoming", "spc"]),
            _c("calibration", "Calibration", ["calibrat", "gauge", "metrology"]),
        ]),
        _g("maintenance", "Maintenance", ["maintenance", "mantenimiento", "cmms"], [
            _c("pm", "Preventive", ["preventive", "pm ", "lubricat"]),
            _c("breakdown", "Breakdown", ["breakdown", "corrective", "repair", "mttr"]),
            _c("spare_parts", "Spare parts", ["spare", "repuesto", "stores"]),
        ]),
        _g("hse", "HSE", ["hse", "safety", "seguridad", "incident"], [
            _c("incidents", "Incidents", ["incident", "near miss", "injury", "accidente"]),
            _c("procedures", "Procedures", ["procedure", "loto", "permit", "jsa"]),
        ]),
        _g("commercial", "Commercial", ["invoice", "po ", "supplier", "comercial"], [
            _c("invoices", "Invoices", ["invoice", "factura", "billing"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
        _g("corporate", "Corporate", ["hr", "policy", "corporate"], [
            _c("hr", "HR", ["hr", "rrhh", "leave", "payroll"]),
            _c("other", "Other", ["misc", "other", "otro", "general"]),
        ]),
    ],
}

# Same oficio, different client trees. Bound on each Taxonomist instance.
PACKS: dict[str, dict[str, Any]] = {
    "ep": {"scope_path": "inbox", "taxonomy": DEFAULT_TAXONOMY},
    "aircraft": {"scope_path": "inbox/aircraft", "taxonomy": AIRCRAFT_TAXONOMY},
    "car": {"scope_path": "inbox/car", "taxonomy": CAR_TAXONOMY},
    "factory": {"scope_path": "inbox/factory", "taxonomy": FACTORY_TAXONOMY},
    "bars": {"scope_path": "inbox/bars", "taxonomy": BARS_TAXONOMY},
    "advice": {"scope_path": "inbox/advice", "taxonomy": ADVICE_TAXONOMY},
}

INSTANCES: list[dict[str, str]] = [
    {"slug": "taxonomist", "pack": "ep", "name": "E&P Taxonomist", "status": "live"},
    {"slug": "taxonomist-aircraft", "pack": "aircraft", "name": "Aircraft Taxonomist", "status": "disabled"},
    {"slug": "taxonomist-car", "pack": "car", "name": "Car Taxonomist", "status": "disabled"},
    {"slug": "taxonomist-factory", "pack": "factory", "name": "Factory Taxonomist", "status": "disabled"},
    {"slug": "taxonomist-bars", "pack": "bars", "name": "Bars Taxonomist", "status": "disabled"},
    {"slug": "taxonomist-advice", "pack": "advice", "name": "Advice Taxonomist", "status": "disabled"},
]


def instance_status(slug: str) -> str:
    return "live" if slug == "taxonomist" else "disabled"


def instance_config(pack: str) -> dict[str, Any]:
    spec = PACKS[pack]
    taxonomy = dict(spec["taxonomy"])
    payload = {
        "specialist": "taxonomist",
        "cadence": settings.taxonomy_cadence or "hour",
        "scope_path": spec["scope_path"],
        "taxonomy": taxonomy,
    }
    return payload


def default_config() -> dict[str, Any]:
    return instance_config("ep")


def is_taxonomist(slug: str, config: dict[str, Any] | None = None) -> bool:
    if slug == "taxonomist" or slug.startswith("taxonomist-"):
        return True
    return (config or {}).get("specialist") == "taxonomist"


def list_agents(db: Session, live_only: bool = False) -> list[Agent]:
    rows = db.query(Agent).order_by(Agent.name).all()
    agents = [row for row in rows if is_taxonomist(row.slug, _parse(row.config_json))]
    if live_only:
        agents = [row for row in agents if row.status == "live"]
    return agents


def active_slug(db: Session | None = None) -> str:
    if db is None:
        return "taxonomist"
    live = list_agents(db, live_only=True)
    if not live:
        return "taxonomist"
    for row in live:
        if row.slug == "taxonomist":
            return row.slug
    return live[0].slug


def nested_scopes() -> list[str]:
    return [str(PACKS[item["pack"]]["scope_path"]) for item in INSTANCES if item["slug"] != "taxonomist"]


def exclusive_live(db: Session, slug: str) -> None:
    """One Taxonomist instance at a time. The sold tree is the live one."""
    for agent in list_agents(db):
        agent.status = "live" if agent.slug == slug else "disabled"


def resolve_slug(db: Session, slug: str | None = None, *, must_live: bool = True) -> str:
    wanted = (slug or "").strip()
    if wanted:
        agent = db.query(Agent).filter(Agent.slug == wanted).first()
        if agent is not None and is_taxonomist(agent.slug, _parse(agent.config_json)):
            if not must_live or agent.status == "live":
                return agent.slug
    return active_slug(db)


def load_config(db: Session | None = None, slug: str = "taxonomist") -> dict[str, Any]:
    payload = default_config()
    if db is None:
        return payload
    agent = db.query(Agent).filter(Agent.slug == slug).first()
    if agent is None and slug != "taxonomist":
        agent = db.query(Agent).filter(Agent.slug == "taxonomist").first()
    if agent is None:
        return payload
    stored = _parse(agent.config_json)
    taxonomy = stored.get("taxonomy") or payload["taxonomy"]
    cadence = stored.get("cadence") or taxonomy.get("cadence") or payload["cadence"]
    scope_path = stored.get("scope_path") or payload.get("scope_path") or "inbox"
    return {
        "specialist": "taxonomist",
        "cadence": cadence,
        "scope_path": scope_path,
        "taxonomy": taxonomy,
        "slug": agent.slug,
        "name": agent.name,
    }


def in_scope(rel_path: str, scope_path: str | None) -> bool:
    rel = (rel_path or "").replace("\\", "/").lstrip("/")
    scope = (scope_path or "").replace("\\", "/").strip("/")
    if not scope:
        return True
    return rel == scope or rel.startswith(scope + "/")


def owner_slug(rel_path: str, agents: list[tuple[str, str]]) -> str:
    """Longest matching scope wins so inbox/aircraft is not stolen by E&P's inbox."""
    best_slug = "taxonomist"
    best_len = -1
    for slug, scope in agents:
        if in_scope(rel_path, scope) and len((scope or "").strip("/")) > best_len:
            best_slug = slug
            best_len = len((scope or "").strip("/"))
    return best_slug


def _parse(raw: str | None) -> dict[str, Any]:
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def cadence_seconds(cadence: str | None) -> int:
    mapping = {"hour": 3600, "day": 86400, "week": 604800}
    return mapping.get((cadence or "hour").strip().lower(), 3600)


def tree(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    taxonomy = (config or default_config()).get("taxonomy") or DEFAULT_TAXONOMY
    levels = []
    for group in taxonomy.get("levels") or []:
        levels.append(
            {
                "id": group.get("id"),
                "label": group.get("label") or group.get("id"),
                "children": [
                    {"id": child.get("id"), "label": child.get("label") or child.get("id")}
                    for child in group.get("children") or []
                ],
            }
        )
    return levels


def classify_document(
    rel_path: str,
    filename: str,
    text: str,
    config: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, str]:
    taxonomy = (config or default_config()).get("taxonomy") or DEFAULT_TAXONOMY
    levels = taxonomy.get("levels") or []
    voice = (model or settings.ollama_chat_model or "qwen").strip()
    placed = _llm_place(rel_path, filename, text, levels, model=model)
    if placed:
        return {**placed, "method": "llm", "note": voice}
    hinted = _filename_type_hint(filename, rel_path, levels)
    reason = "off" if not settings.file_llm else "timeout"
    if hinted:
        return {**hinted, "method": "heuristic", "note": f"{reason}:filename"}
    fallback = _heuristic_place(rel_path, filename, text, levels)
    return {**fallback, "method": "heuristic", "note": f"{reason}:keywords"}


def _heuristic_place(rel_path: str, filename: str, text: str, levels: list[dict[str, Any]]) -> dict[str, str]:
    haystack = _haystack(rel_path, filename, text)
    best_l1 = None
    best_l1_score = 0.0
    for group in levels:
        score = _score_node(group, haystack)
        for child in group.get("children") or []:
            score += 0.6 * _score_node(child, haystack)
        if score > best_l1_score:
            best_l1 = group
            best_l1_score = score
    if best_l1 is None or best_l1_score <= 0:
        best_l1 = _fallback_group(levels)
    children = best_l1.get("children") or []
    best_l2 = None
    best_l2_score = 0.0
    for child in children:
        score = _score_node(child, haystack)
        if score > best_l2_score:
            best_l2 = child
            best_l2_score = score
    if best_l2 is None:
        best_l2 = children[-1] if children else {"id": "other", "label": "Other"}
    return _placement(best_l1, best_l2)


def _fallback_group(levels: list[dict[str, Any]]) -> dict[str, Any]:
    for group in levels:
        if group.get("id") == "corporate":
            return group
    return levels[-1] if levels else {"id": "corporate", "label": "Corporate", "children": []}


def _score_node(node: dict[str, Any], haystack: dict[str, Any]) -> float:
    tokens = [str(node.get("id") or ""), str(node.get("label") or ""), *(node.get("keywords") or [])]
    score = 0.0
    seen: set[str] = set()
    for raw in tokens:
        needle = _normalize(raw)
        if len(needle) < 2 or needle in seen:
            continue
        seen.add(needle)
        if _has_word(haystack["name"], needle):
            score += 6.0
        if _has_word(haystack["leaf"], needle):
            score += 4.0
        if any(_has_word(folder, needle) for folder in haystack["ancestors"]):
            score += 0.8
        if _has_word(haystack["text"], needle):
            score += 2.5
    return score


def _haystack(rel_path: str, filename: str, text: str) -> dict[str, Any]:
    folders = _folder_names(rel_path)
    return {
        "name": _normalize(filename),
        "text": _normalize(text[:8000]),
        "leaf": _normalize(folders[-1]) if folders else "",
        "ancestors": [_normalize(part) for part in folders[:-1]],
    }


def _folder_names(rel_path: str) -> list[str]:
    from pathlib import Path

    parts = [part for part in Path(rel_path.replace("\\", "/")).parts if part not in {".", ""}]
    if parts and "." in parts[-1]:
        parts = parts[:-1]
    skip = {"inbox", "classified", "documents", "data"}
    return [part for part in parts if _normalize(part) not in skip]


def _has_word(haystack: str, needle: str) -> bool:
    if not needle or not haystack:
        return False
    pattern = r"(^|[^a-z0-9])" + re.escape(needle) + r"([^a-z0-9]|$)"
    return re.search(pattern, haystack) is not None


def _normalize(value: str) -> str:
    text = (value or "").lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text)


def _filename_type_hint(filename: str, rel_path: str, levels: list[dict[str, Any]]) -> dict[str, str] | None:
    blob = _normalize(f"{filename} {rel_path}")
    types = {"invoice", "invoices", "factura", "facturas"}
    if not any(_has_word(blob, token) for token in types):
        return None
    hits = []
    for group in levels:
        for child in group.get("children") or []:
            keys = [_normalize(str(child.get("id") or "")), _normalize(str(child.get("label") or ""))]
            keys.extend(_normalize(str(item)) for item in (child.get("keywords") or []))
            if types.intersection({key for key in keys if key}):
                hits.append((group, child))
    if len({(hit[0].get("id"), hit[1].get("id")) for hit in hits}) != 1:
        return None
    group, child = hits[0]
    return _placement(group, child)


def _placement(group: dict[str, Any], child: dict[str, Any]) -> dict[str, str]:
    return {
        "l1": str(group.get("id") or "corporate"),
        "l1_label": str(group.get("label") or group.get("id") or "Corporate"),
        "l2": str(child.get("id") or "other"),
        "l2_label": str(child.get("label") or child.get("id") or "Other"),
    }


def _llm_place(
    rel_path: str,
    filename: str,
    text: str,
    levels: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, str] | None:
    from app.services.llm import complete_json

    options = []
    by_l1: dict[str, dict[str, Any]] = {}
    for group in levels:
        l1 = str(group.get("id") or "")
        children = list(group.get("children") or [])
        by_l1[l1] = group
        options.append({"l1": l1, "l2": [str(child.get("id") or "") for child in children]})
    excerpt = (text or "").strip()[:2500]
    data = complete_json(
        (
            "Two-level filing. Classify the DOCUMENT, not the drop folder. "
            "Filename and extracted text beat parent directories. "
            "An invoice (filename invoice/factura, an invoices folder, or invoice content) "
            "is commercial/invoices even if the path contains wells or a dump folder.\n"
            f"Path: {rel_path}\nFile: {filename}\n"
            f"Allowed: {json.dumps(options, ensure_ascii=False)}\n"
            f"Text:\n{excerpt or '(no extracted text yet; use filename and path)'}\n"
            'Return JSON {"l1":"...","l2":"..."} using only allowed ids.'
        ),
        model=model,
        timeout=75.0,
        num_predict=80,
        json_mode=True,
    )
    l1_id = str(data.get("l1") or "")
    group = by_l1.get(l1_id)
    if not group:
        return None
    children = list(group.get("children") or [])
    l2_id = str(data.get("l2") or "")
    child = next((item for item in children if str(item.get("id") or "") == l2_id), None)
    if child is None:
        child = children[-1] if children else {"id": "other", "label": "Other"}
    return _placement(group, child)
