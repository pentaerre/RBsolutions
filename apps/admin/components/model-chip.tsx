"use client";

import { shortModelName, type OllamaModel } from "@/lib/models";

export function ModelChip({
  value,
  models,
  onChange,
  label,
}: {
  value: string;
  models: OllamaModel[];
  onChange?: (name: string) => void;
  label: string;
}) {
  const display = shortModelName(value) || "—";
  if (!onChange) {
    return (
      <span className="badge model" title={value || undefined}>
        {display}
      </span>
    );
  }
  const names = new Set(models.map((item) => item.name));
  return (
    <select
      className="badge model"
      aria-label={label}
      title={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onClick={(event) => event.stopPropagation()}
    >
      {value && !names.has(value) ? <option value={value}>{display}</option> : null}
      {models.map((item) => (
        <option key={item.name} value={item.name}>
          {shortModelName(item.name)}
        </option>
      ))}
    </select>
  );
}
