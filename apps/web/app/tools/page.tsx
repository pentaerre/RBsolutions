"use client";

import { useEffect, useState } from "react";
import { apiGet, type ToolItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeKind, localizeToolName, localizeToolSummary } from "@/lib/catalog-i18n";

export default function ToolsPage() {
  const { t, locale } = useI18n();
  const [tools, setTools] = useState<ToolItem[]>([]);

  useEffect(() => {
    apiGet<{ tools: ToolItem[] }>("/tools")
      .then((payload) => setTools(payload.tools))
      .catch(() => undefined);
  }, []);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("tools.title")}</h1>
          <p>{t("tools.lead")}</p>
        </div>
      </div>
      <div className="tool-list">
        {tools.map((tool) => (
          <article className="card" key={tool.id}>
            <span className={`badge ${tool.status}`}>{t(`status.${tool.status}`)}</span>
            <h3 style={{ marginTop: 10 }}>{localizeToolName(tool.slug, tool.name, locale)}</h3>
            <p>{localizeToolSummary(tool.slug, tool.summary, locale)}</p>
            <p className="muted">
              {localizeKind(tool.kind, locale)} · {tool.slug}
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
