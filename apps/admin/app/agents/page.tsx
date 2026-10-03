"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ModelChip } from "@/components/model-chip";
import { apiGet, apiSend, type AgentItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeAgentSummary, localizeRole } from "@/lib/catalog-i18n";
import type { OllamaModel } from "@/lib/models";

export default function AgentsPage() {
  const { t, locale } = useI18n();
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<{ agents: AgentItem[] }>("/agents"),
      apiGet<{ models: OllamaModel[] }>("/models").catch(() => ({ models: [] as OllamaModel[] })),
    ])
      .then(([payload, ollama]) => {
        setAgents(payload.agents);
        setModels(ollama.models || []);
      })
      .catch(() => undefined);
  }, []);

  async function pickModel(agent: AgentItem, model: string) {
    const previous = agent.model;
    setAgents((rows) => rows.map((row) => (row.id === agent.id ? { ...row, model } : row)));
    setNotice("");
    try {
      const saved = await apiSend<AgentItem>(`/agents/${agent.id}`, "PATCH", { model });
      setAgents((rows) => rows.map((row) => (row.id === saved.id ? { ...row, model: saved.model } : row)));
    } catch (err) {
      setAgents((rows) => rows.map((row) => (row.id === agent.id ? { ...row, model: previous } : row)));
      setNotice(err instanceof Error ? err.message : t("agents.saveFailed"));
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("agents.title")}</h1>
          <p>{t("agents.lead")}</p>
        </div>
      </div>
      {notice ? <p className="warn">{notice}</p> : null}
      <div className="tool-list">
        {agents.map((agent) => (
          <article className="card" key={agent.id}>
            <div className="chip-row">
              <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
              {agent.uses_llm ? (
                <ModelChip
                  value={agent.model}
                  models={models}
                  onChange={models.length ? (model) => pickModel(agent, model) : undefined}
                  label={t("agents.model")}
                />
              ) : null}
            </div>
            <h3 style={{ marginTop: 10 }}>
              <Link href={`/agents/${agent.id}`}>{agent.name}</Link>
            </h3>
            <p>{localizeAgentSummary(agent.slug, agent.summary, locale)}</p>
            <p className="muted">
              {localizeRole(agent.role, locale)}
              {agent.tools.length ? ` · ${agent.tools.join(", ")}` : ` · ${t("agents.noTools")}`}
            </p>
          </article>
        ))}
      </div>
    </>
  );
}
