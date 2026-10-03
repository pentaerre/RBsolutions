"use client";

export type OllamaModel = {
  name: string;
  size?: number | null;
  family?: string | null;
  parameter_size?: string | null;
};

export function shortModelName(name: string) {
  return (name || "").replace(/:latest$/, "");
}

export function formatModelLabel(item: OllamaModel | string): string {
  if (typeof item === "string") {
    return shortModelName(item);
  }
  const short = shortModelName(item.name);
  return item.parameter_size ? `${short} · ${item.parameter_size}` : short;
}
