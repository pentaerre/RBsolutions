"use client";

import { useI18n } from "@/lib/i18n";
import type { KnobField } from "@/lib/api";

export function KnobFields({
  knobs,
  onChange,
}: {
  knobs: KnobField[];
  onChange: (key: string, value: string | number | boolean) => void;
}) {
  const { t } = useI18n();
  if (!knobs.length) {
    return <p className="muted">{t("knobs.none")}</p>;
  }
  return (
    <div className="knob-list">
      {knobs.map((field) => (
        <label key={field.key}>
          {t(field.label_key)}
          {field.help_key ? <span className="knob-help">{t(field.help_key)}</span> : null}
          {field.type === "bool" ? (
            <input
              type="checkbox"
              checked={Boolean(field.value)}
              onChange={(event) => onChange(field.key, event.target.checked)}
            />
          ) : field.type === "select" ? (
            <select value={String(field.value ?? field.default ?? "")} onChange={(event) => onChange(field.key, event.target.value)}>
              {(field.options || []).map((option) => (
                <option key={option.value} value={option.value}>
                  {t(option.label_key)}
                </option>
              ))}
            </select>
          ) : (
            <input
              type={field.type === "number" ? "number" : "text"}
              value={field.value === undefined || field.value === null ? "" : String(field.value)}
              onChange={(event) =>
                onChange(field.key, field.type === "number" ? Number(event.target.value) : event.target.value)
              }
            />
          )}
        </label>
      ))}
    </div>
  );
}

export function setNested(target: Record<string, unknown>, key: string, value: unknown) {
  const parts = key.split(".");
  let cursor: Record<string, unknown> = target;
  for (const part of parts.slice(0, -1)) {
    const next = cursor[part];
    if (!next || typeof next !== "object" || Array.isArray(next)) {
      cursor[part] = {};
    }
    cursor = cursor[part] as Record<string, unknown>;
  }
  cursor[parts[parts.length - 1]] = value;
}
