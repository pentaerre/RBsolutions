"use client";

import { useEffect, useState } from "react";
import { apiGet, type AgentItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeAgentSummary, localizeRole } from "@/lib/catalog-i18n";
import { ModelBadge } from "@/components/model-badge";
import { onRoster } from "@/lib/roster";

export default function ToolsPage() {
  const { t, locale } = useI18n();
  const [agents, setAgents] = useState<AgentItem[]>([]);

  useEffect(() => {
    apiGet<{ agents: AgentItem[] }>("/agents")
      .then((payload) => setAgents(payload.agents))
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
        {agents.filter(onRoster).map((agent) => (
          <article className="card" key={agent.id}>
            <div className="chip-row">
              <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
              {agent.uses_llm ? <ModelBadge name={agent.model} /> : null}
            </div>
            <h3 style={{ marginTop: 10 }}>{agent.name}</h3>
            <p>{localizeAgentSummary(agent.slug, agent.summary, locale)}</p>
            <p className="muted">
              {localizeRole(agent.role, locale)}
              {agent.tools.length ? ` · ${agent.tools.join(", ")}` : ""}
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
