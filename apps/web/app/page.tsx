"use client";

import { useEffect, useState } from "react";
import { apiGet, type AgentItem, type AppItem, type Health } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeAgentSummary, localizeAppName, localizeAppSummary, localizeKind } from "@/lib/catalog-i18n";
import { ModelToggle, pickModel, readStoredModel } from "@/lib/model-select";
import { ModelBadge } from "@/components/model-badge";
import { onRoster } from "@/lib/roster";

export default function OverviewPage() {
  const { t, locale } = useI18n();
  const [health, setHealth] = useState<Health | null>(null);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [apps, setApps] = useState<AppItem[]>([]);
  const [error, setError] = useState("");
  const [chatModel, setChatModel] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<Health>("/health"),
      apiGet<{ agents: AgentItem[] }>("/agents"),
      apiGet<{ apps: AppItem[] }>("/apps"),
    ])
      .then(([nextHealth, nextAgents, nextApps]) => {
        setHealth(nextHealth);
        setAgents(nextAgents.agents);
        setApps(nextApps.apps);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!health?.ollama.models?.length) {
      return;
    }
    setChatModel(pickModel(health.ollama.models, health.ollama.default_model || "", readStoredModel()));
  }, [health]);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("home.title")}</h1>
          <p>{t("home.lead")}</p>
        </div>
      </div>
      {error ? <p className="warn">{error}</p> : null}
      <div className="grid">
        <article className="card">
          <h2>{t("home.ollama")}</h2>
          {health ? (
            <>
              <p className={health.ollama.ok ? "ok" : "warn"}>
                {health.ollama.ok ? t("home.connected") : health.ollama.error || t("home.unreachable")}
              </p>
              {health.ollama.models.length ? (
                <ModelToggle
                  models={health.ollama.models}
                  value={chatModel}
                  onChange={setChatModel}
                  label={t("chat.model")}
                />
              ) : (
                <p className="muted">{t("home.noModels")}</p>
              )}
            </>
          ) : (
            <p className="muted">{t("home.checking")}</p>
          )}
        </article>
        <article className="card">
          <h2>{t("home.index")}</h2>
          <p>{health ? t("home.chunks", { count: health.index.chunks }) : "…"}</p>
          <p className="muted">{t("home.embeddings", { backend: health?.embed_backend || "…" })}</p>
        </article>
        <article className="card">
          <h2>{t("home.platform")}</h2>
          <p>
            {health?.platform
              ? t("home.platformCounts", {
                  agents: health.platform.agents,
                  tools: health.platform.tools,
                  apps: health.platform.apps,
                })
              : "…"}
          </p>
        </article>
      </div>
      <div className="card" style={{ marginTop: 20 }}>
        <h2>{t("home.agents")}</h2>
        <div className="tool-list" style={{ marginTop: 12 }}>
          {agents.filter(onRoster).map((agent) => (
            <article className="card" key={agent.id} style={{ margin: 0 }}>
              <div className="chip-row">
                <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
                {agent.uses_llm ? <ModelBadge name={agent.model} /> : null}
              </div>
              <h3 style={{ marginTop: 8 }}>{agent.name}</h3>
              <p>{localizeAgentSummary(agent.slug, agent.summary, locale)}</p>
            </article>
          ))}
        </div>
      </div>
      <div className="card" style={{ marginTop: 20 }}>
        <h2>{t("home.webs")}</h2>
        <div className="tool-list" style={{ marginTop: 12 }}>
          {apps.map((app) => (
            <div key={app.id}>
              <span className={`badge ${app.status}`}>{localizeKind(app.kind, locale)}</span>
              <h3 style={{ marginTop: 8 }}>{localizeAppName(app.slug, app.name, locale)}</h3>
              <p>{localizeAppSummary(app.slug, app.summary, locale)}</p>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
