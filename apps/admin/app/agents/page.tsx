"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, type AgentItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeAgentSummary, localizeRole } from "@/lib/catalog-i18n";

export default function AgentsPage() {
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
          <h1>{t("agents.title")}</h1>
          <p>{t("agents.lead")}</p>
        </div>
      </div>
      <div className="tool-list">
        {agents.map((agent) => (
          <article className="card" key={agent.id}>
            <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
            <h3 style={{ marginTop: 10 }}>
              <Link href={`/agents/${agent.id}`}>{agent.name}</Link>
            </h3>
            <p>{localizeAgentSummary(agent.slug, agent.summary, locale)}</p>
            <p className="muted">
              {localizeRole(agent.role, locale)} · {agent.model || t("agents.defaultModel")}
            </p>
            <p className="muted">{agent.tools.join(", ") || t("agents.noTools")}</p>
          </article>
        ))}
      </div>
    </>
  );
}
