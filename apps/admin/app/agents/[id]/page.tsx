"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiSend, type AgentItem, type ToolItem } from "@/lib/api";
import { KnobFields, setNested } from "@/components/knob-fields";
import { ModelChip } from "@/components/model-chip";
import { useI18n } from "@/lib/i18n";
import type { OllamaModel } from "@/lib/models";

export default function AgentDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [agent, setAgent] = useState<AgentItem | null>(null);
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [config, setConfig] = useState("{}");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<AgentItem>(`/agents/${params.id}`),
      apiGet<{ tools: ToolItem[] }>("/tools"),
      apiGet<{ models: OllamaModel[] }>("/models").catch(() => ({ models: [] as OllamaModel[] })),
    ])
      .then(([nextAgent, catalog, ollama]) => {
        setAgent(nextAgent);
        setTools(catalog.tools);
        setModels(ollama.models || []);
        setConfig(JSON.stringify(nextAgent.config || {}, null, 2));
      })
      .catch((err: Error) => setMessage(err.message));
  }, [params.id]);

  function toggleTool(slug: string) {
    if (!agent) {
      return;
    }
    const next = agent.tools.includes(slug)
      ? agent.tools.filter((item) => item !== slug)
      : [...agent.tools, slug];
    setAgent({ ...agent, tools: next });
  }

  async function pickModel(model: string) {
    if (!agent) {
      return;
    }
    const previous = agent.model;
    setAgent({ ...agent, model });
    setMessage("");
    try {
      const saved = await apiSend<AgentItem>(`/agents/${agent.id}`, "PATCH", { model });
      setAgent((current) => (current ? { ...current, model: saved.model } : saved));
    } catch (err) {
      setAgent({ ...agent, model: previous });
      setMessage(err instanceof Error ? err.message : t("agents.saveFailed"));
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!agent) {
      return;
    }
    setMessage("");
    try {
      const parsed = JSON.parse(config);
      for (const field of agent.knobs || []) {
        setNested(parsed, field.key, field.value);
      }
      const saved = await apiSend<AgentItem>(`/agents/${agent.id}`, "PATCH", {
        name: agent.name,
        status: agent.status,
        summary: agent.summary,
        model: agent.model,
        system_prompt: agent.system_prompt,
        config: parsed,
        tools: agent.tools,
      });
      setAgent(saved);
      setConfig(JSON.stringify(saved.config || {}, null, 2));
      setMessage(t("agents.saved"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("agents.saveFailed"));
    }
  }

  if (!agent) {
    return <p className="muted">{message || t("agents.loading")}</p>;
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{agent.name}</h1>
          <p>
            {agent.role} · {agent.slug}
          </p>
          <div className="chip-row" style={{ marginTop: 10 }}>
            <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
            {agent.uses_llm ? (
              <ModelChip
                value={agent.model}
                models={models}
                onChange={models.length ? pickModel : undefined}
                label={t("agents.model")}
              />
            ) : null}
          </div>
        </div>
        <button className="btn secondary" onClick={() => router.push("/agents")}>
          {t("agents.back")}
        </button>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <form className="form" onSubmit={onSubmit}>
        <label>
          {t("agents.name")}
          <input value={agent.name} onChange={(e) => setAgent({ ...agent, name: e.target.value })} />
        </label>
        <label>
          {t("agents.status")}
          <select value={agent.status} onChange={(e) => setAgent({ ...agent, status: e.target.value })}>
            <option value="live">{t("status.live")}</option>
            <option value="planned">{t("status.planned")}</option>
            <option value="disabled">{t("status.disabled")}</option>
          </select>
        </label>
        <label>
          {t("agents.summary")}
          <textarea value={agent.summary} onChange={(e) => setAgent({ ...agent, summary: e.target.value })} />
        </label>
        <label>
          {t("agents.prompt")}
          <textarea value={agent.system_prompt} onChange={(e) => setAgent({ ...agent, system_prompt: e.target.value })} />
        </label>
        {(agent.knobs || []).length ? (
          <div>
            <div className="muted" style={{ marginBottom: 8 }}>
              {t("knobs.title")}
            </div>
            <KnobFields
              knobs={agent.knobs || []}
              onChange={(key, value) => {
                const nextKnobs = (agent.knobs || []).map((field) => (field.key === key ? { ...field, value } : field));
                let parsed: Record<string, unknown> = {};
                try {
                  parsed = JSON.parse(config);
                } catch {
                  parsed = { ...(agent.config || {}) };
                }
                setNested(parsed, key, value);
                setAgent({ ...agent, knobs: nextKnobs, config: parsed });
                setConfig(JSON.stringify(parsed, null, 2));
              }}
            />
          </div>
        ) : null}
        <details>
          <summary>{t("agents.config")}</summary>
          <textarea value={config} onChange={(e) => setConfig(e.target.value)} />
        </details>
        <div>
          <div className="muted" style={{ marginBottom: 8 }}>
            {t("agents.tools")}
          </div>
          <div className="checks">
            {tools.map((tool) => (
              <label key={tool.id}>
                <input
                  type="checkbox"
                  checked={agent.tools.includes(tool.slug)}
                  onChange={() => toggleTool(tool.slug)}
                />
                {tool.name} <span className="muted">({tool.slug})</span>
              </label>
            ))}
          </div>
        </div>
        <button className="btn" type="submit">
          {t("agents.save")}
        </button>
      </form>
    </>
  );
}
