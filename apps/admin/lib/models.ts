"use client";

export type OllamaModel = {
  name: string;
  size?: number | null;
  family?: string | null;
  parameter_size?: string | null;
};

export function formatModelLabel(item: OllamaModel | string): string {
  if (typeof item === "string") {
    return item.replace(/:latest$/, "");
  }
  const short = item.name.replace(/:latest$/, "");
  return item.parameter_size ? `${short} · ${item.parameter_size}` : short;
}
