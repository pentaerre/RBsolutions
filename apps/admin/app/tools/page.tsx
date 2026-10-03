"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiSend, type AgentItem, type ToolItem } from "@/lib/api";
import { ModelChip } from "@/components/model-chip";
import { useI18n } from "@/lib/i18n";
import { localizeKind, localizeToolName } from "@/lib/catalog-i18n";
import type { OllamaModel } from "@/lib/models";

export default function ToolsPage() {
  const { t, locale } = useI18n();
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    slug: "",
    name: "",
    url: "",
    summary: "",
  });

  async function load() {
    const [toolPayload, agentPayload, ollama] = await Promise.all([
      apiGet<{ tools: ToolItem[] }>("/tools"),
      apiGet<{ agents: AgentItem[] }>("/agents"),
      apiGet<{ models: OllamaModel[] }>("/models").catch(() => ({ models: [] as OllamaModel[] })),
    ]);
    setTools(toolPayload.tools);
    setAgents(agentPayload.agents);
    setModels(ollama.models || []);
  }

  async function pickModel(agent: AgentItem, model: string) {
    const previous = agent.model;
    setAgents((rows) => rows.map((row) => (row.id === agent.id ? { ...row, model } : row)));
    try {
      const saved = await apiSend<AgentItem>(`/agents/${agent.id}`, "PATCH", { model });
      setAgents((rows) => rows.map((row) => (row.id === saved.id ? { ...row, model: saved.model } : row)));
    } catch (err) {
      setAgents((rows) => rows.map((row) => (row.id === agent.id ? { ...row, model: previous } : row)));
      setMessage(err instanceof Error ? err.message : t("agents.saveFailed"));
    }
  }

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
  }, []);

  async function toggle(tool: ToolItem) {
    const status = tool.status === "live" ? "disabled" : "live";
    await apiSend(`/tools/${tool.id}`, "PATCH", { status });
    await load();
  }

  async function registerHttp(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await apiSend("/tools", "POST", {
        slug: form.slug,
        name: form.name,
        kind: "http",
        status: "planned",
        summary: form.summary,
        entrypoint: form.url,
        config: { url: form.url, method: "POST" },
      });
      setForm({ slug: "", name: "", url: "", summary: "" });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("tools.failed"));
    }
  }

  async function invokeIngest() {
    setMessage("");
    try {
      const result = await apiSend<{ files: number; chunks: number }>("/tools/knowledge.ingest/invoke", "POST", {
        payload: {},
      });
      setMessage(t("tools.indexed", { files: result.files, chunks: result.chunks }));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("tools.invokeFailed"));
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("tools.title")}</h1>
          <p>{t("tools.lead")}</p>
        </div>
        <button className="btn secondary" onClick={invokeIngest}>
          {t("tools.ingest")}
        </button>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>{t("tools.col")}</th>
              <th>{t("tools.kind")}</th>
              <th>{t("tools.agents")}</th>
              <th>{t("tools.status")}</th>
              <th>{t("agents.model")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => {
              const owners = agents.filter((agent) => tool.agents.includes(agent.slug) && agent.uses_llm);
              const owner = owners[0];
              return (
              <tr key={tool.id}>
                <td>
                  <Link href={`/tools/${tool.id}`}>{localizeToolName(tool.slug, tool.name, locale)}</Link>
                  <div className="muted">{tool.slug}</div>
                </td>
                <td>{localizeKind(tool.kind, locale)}</td>
                <td className="muted">{tool.agents.join(", ") || "—"}</td>
                <td>
                  <span className={`badge ${tool.status}`}>{t(`status.${tool.status}`)}</span>
                </td>
                <td>
                  {owner ? (
                    <ModelChip
                      value={owner.model}
                      models={models}
                      onChange={owners.length === 1 && models.length ? (model) => pickModel(owner, model) : undefined}
                      label={t("agents.model")}
                    />
                  ) : null}
                </td>
                <td>
                  <button className="btn secondary" onClick={() => toggle(tool)}>
                    {tool.status === "live" ? t("tools.disable") : t("tools.enable")}
                  </button>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="card" style={{ marginTop: 20 }}>
        <h2>{t("tools.httpTitle")}</h2>
        <p className="muted">{t("tools.httpLead")}</p>
        <form className="form" onSubmit={registerHttp} style={{ marginTop: 12 }}>
          <label>
            {t("tools.slug")}
            <input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} required />
          </label>
          <label>
            {t("tools.name")}
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            {t("tools.endpoint")}
            <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required />
          </label>
          <label>
            {t("tools.summary")}
            <textarea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
          </label>
          <button className="btn" type="submit">
            {t("tools.register")}
          </button>
        </form>
      </div>
    </>
  );
}
