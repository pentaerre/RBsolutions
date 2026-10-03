"use client";

export function ModelBadge({ name }: { name?: string | null }) {
  const display = (name || "").replace(/:latest$/, "");
  if (!display) {
    return null;
  }
  return (
    <span className="badge model" title={name || undefined}>
      {display}
    </span>
  );
}
