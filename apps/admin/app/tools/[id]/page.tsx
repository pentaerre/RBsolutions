"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiSend, type AgentItem, type ToolItem } from "@/lib/api";
import { KnobFields, setNested } from "@/components/knob-fields";
import { ModelChip } from "@/components/model-chip";
import { useI18n } from "@/lib/i18n";

export default function ToolDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [tool, setTool] = useState<ToolItem | null>(null);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [config, setConfig] = useState("{}");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([apiGet<{ tools: ToolItem[] }>("/tools"), apiGet<{ agents: AgentItem[] }>("/agents")])
      .then(([payload, catalog]) => {
        const found = payload.tools.find((item) => item.id === params.id) || null;
        setTool(found);
        setAgents(catalog.agents);
        setConfig(JSON.stringify(found?.config || {}, null, 2));
      })
      .catch((err: Error) => setMessage(err.message));
  }, [params.id]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!tool) {
      return;
    }
    setMessage("");
    try {
      const parsed = JSON.parse(config);
      for (const field of tool.knobs || []) {
        setNested(parsed, field.key, field.value);
      }
      const saved = await apiSend<ToolItem>(`/tools/${tool.id}`, "PATCH", {
        name: tool.name,
        status: tool.status,
        summary: tool.summary,
        kind: tool.kind,
        entrypoint: tool.entrypoint,
        config: parsed,
      });
      setTool(saved);
      setConfig(JSON.stringify(saved.config || {}, null, 2));
      setMessage(t("tools.saved"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("tools.saveFailed"));
    }
  }

  if (!tool) {
    return <p className="muted">{message || t("tools.loading")}</p>;
  }

  const linked = agents.filter((agent) => tool.agents.includes(agent.slug));

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{tool.name}</h1>
          <p>{tool.slug}</p>
        </div>
        <button className="btn secondary" onClick={() => router.push("/tools")}>
          {t("tools.back")}
        </button>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <form className="form" onSubmit={onSubmit}>
        <label>
          {t("tools.name")}
          <input value={tool.name} onChange={(e) => setTool({ ...tool, name: e.target.value })} />
        </label>
        <label>
          {t("tools.status")}
          <select value={tool.status} onChange={(e) => setTool({ ...tool, status: e.target.value })}>
            <option value="live">{t("status.live")}</option>
            <option value="planned">{t("status.planned")}</option>
            <option value="disabled">{t("status.disabled")}</option>
          </select>
        </label>
        <label>
          {t("tools.kind")}
          <select value={tool.kind} onChange={(e) => setTool({ ...tool, kind: e.target.value })}>
            <option value="builtin">builtin</option>
            <option value="http">http</option>
          </select>
        </label>
        <label>
          {t("tools.entrypoint")}
          <input value={tool.entrypoint} onChange={(e) => setTool({ ...tool, entrypoint: e.target.value })} />
        </label>
        <label>
          {t("tools.summary")}
          <textarea value={tool.summary} onChange={(e) => setTool({ ...tool, summary: e.target.value })} />
        </label>
        <div>
          <div className="muted" style={{ marginBottom: 8 }}>
            {t("tools.agents")}
          </div>
          {linked.length ? (
            <div className="chip-row" style={{ flexDirection: "column", alignItems: "flex-start" }}>
              {linked.map((agent) => (
                <p key={agent.id} className="chip-row" style={{ margin: 0 }}>
                  <Link href={`/agents/${agent.id}`}>{agent.name}</Link>
                  {agent.uses_llm ? <ModelChip value={agent.model} models={[]} label={t("agents.model")} /> : null}
                </p>
              ))}
            </div>
          ) : (
            <p className="muted">{t("tools.noAgents")}</p>
          )}
        </div>
        {(tool.knobs || []).length ? (
          <div>
            <div className="muted" style={{ marginBottom: 8 }}>
              {t("knobs.title")}
            </div>
            <KnobFields
              knobs={tool.knobs || []}
              onChange={(key, value) => {
                const nextKnobs = (tool.knobs || []).map((field) => (field.key === key ? { ...field, value } : field));
                let parsed: Record<string, unknown> = {};
                try {
                  parsed = JSON.parse(config);
                } catch {
                  parsed = { ...(tool.config || {}) };
                }
                setNested(parsed, key, value);
                setTool({ ...tool, knobs: nextKnobs, config: parsed });
                setConfig(JSON.stringify(parsed, null, 2));
              }}
            />
          </div>
        ) : null}
        <details>
          <summary>{t("tools.config")}</summary>
          <textarea value={config} onChange={(e) => setConfig(e.target.value)} />
        </details>
        <button className="btn" type="submit">
          {t("tools.save")}
        </button>
      </form>
    </>
  );
}
