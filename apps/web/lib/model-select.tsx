"use client";

export type OllamaModel = {
  name: string;
  size?: number | null;
  family?: string | null;
  parameter_size?: string | null;
};

export const CHAT_MODEL_KEY = "atrium_chat_model";

export function readStoredModel(): string {
  try {
    return localStorage.getItem(CHAT_MODEL_KEY) || "";
  } catch {
    return "";
  }
}

export function writeStoredModel(name: string) {
  try {
    localStorage.setItem(CHAT_MODEL_KEY, name);
  } catch {
    /* ignore */
  }
}

export function pickModel(models: string[], preferred: string, stored: string): string {
  if (stored && models.includes(stored)) {
    return stored;
  }
  if (preferred && models.includes(preferred)) {
    return preferred;
  }
  return models[0] || preferred || "";
}

export function formatModelLabel(item: OllamaModel | string): string {
  if (typeof item === "string") {
    return item.replace(/:latest$/, "");
  }
  const short = item.name.replace(/:latest$/, "");
  return item.parameter_size ? `${short} · ${item.parameter_size}` : short;
}

export function ModelToggle({
  models,
  value,
  onChange,
  label,
}: {
  models: Array<OllamaModel | string>;
  value: string;
  onChange: (name: string) => void;
  label: string;
}) {
  const items: OllamaModel[] = models.map((item) => (typeof item === "string" ? { name: item } : item));
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="lang-select">
      <span>{label}</span>
      <div className="model-toggle" role="group" aria-label={label}>
        {items.map((item) => (
          <button
            type="button"
            key={item.name}
            className={value === item.name ? "btn" : "btn secondary"}
            onClick={() => {
              writeStoredModel(item.name);
              onChange(item.name);
            }}
            title={item.name}
          >
            {formatModelLabel(item)}
          </button>
        ))}
      </div>
    </div>
  );
}
