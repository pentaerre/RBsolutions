"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiSend, type KnobField, type UtilityItem } from "@/lib/api";
import { KnobFields } from "@/components/knob-fields";
import { ModelChip } from "@/components/model-chip";
import { CrossAppLink, useI18n } from "@/lib/i18n";
import { localizeAgentSummary } from "@/lib/catalog-i18n";
import type { OllamaModel } from "@/lib/models";

export default function UtilityDetailPage() {
  const { t, locale } = useI18n();
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [item, setItem] = useState<UtilityItem | null>(null);
  const [knobs, setKnobs] = useState<Record<string, KnobField[]>>({});
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<UtilityItem>(`/utilities/${params.slug}`),
      apiGet<{ models: OllamaModel[] }>("/models").catch(() => ({ models: [] as OllamaModel[] })),
    ])
      .then(([payload, ollama]) => {
        setItem(payload);
        setModels(ollama.models || []);
        const next: Record<string, KnobField[]> = {};
        for (const agent of payload.agents) {
          next[agent.slug] = agent.knobs || [];
        }
        setKnobs(next);
      })
      .catch((err: Error) => setMessage(err.message));
  }, [params.slug]);

  async function pickModel(agentId: string, model: string) {
    if (!item) {
      return;
    }
    const previous = item.agents.find((agent) => agent.id === agentId)?.model;
    setItem({
      ...item,
      agents: item.agents.map((agent) => (agent.id === agentId ? { ...agent, model } : agent)),
    });
    setMessage("");
    try {
      const saved = await apiSend<UtilityItem["agents"][number]>(`/agents/${agentId}`, "PATCH", { model });
      setItem((current) =>
        current
          ? { ...current, agents: current.agents.map((agent) => (agent.id === saved.id ? { ...agent, model: saved.model } : agent)) }
          : current,
      );
    } catch (err) {
      setItem({
        ...item,
        agents: item.agents.map((agent) => (agent.id === agentId ? { ...agent, model: previous || "" } : agent)),
      });
      setMessage(err instanceof Error ? err.message : t("agents.saveFailed"));
    }
  }

  function changeKnob(slug: string, key: string, value: string | number | boolean) {
    setKnobs((current) => ({
      ...current,
      [slug]: (current[slug] || []).map((field) => (field.key === key ? { ...field, value } : field)),
    }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!item) {
      return;
    }
    setMessage("");
    const values: Record<string, Record<string, string | number | boolean>> = {};
    for (const [slug, fields] of Object.entries(knobs)) {
      if (!fields.length) {
        continue;
      }
      values[slug] = {};
      for (const field of fields) {
        values[slug][field.key] = field.value as string | number | boolean;
      }
    }
    try {
      const saved = await apiSend<UtilityItem>(`/utilities/${item.slug}`, "PATCH", { values });
      setItem(saved);
      const next: Record<string, KnobField[]> = {};
      for (const agent of saved.agents) {
        next[agent.slug] = agent.knobs || [];
      }
      setKnobs(next);
      setMessage(t("util.saved"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("util.saveFailed"));
    }
  }

  if (!item) {
    return <p className="muted">{message || t("util.loading")}</p>;
  }

  const title = t(`util.${item.slug}.name`);
  const summary = t(`util.${item.slug}.summary`);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{title.startsWith("util.") ? item.name : title}</h1>
          <p>{summary.startsWith("util.") ? item.summary : summary}</p>
        </div>
        <div className="actions">
          <CrossAppLink port={3000} path={item.workspace_path}>
            {t("util.openWorkspace")}
          </CrossAppLink>
          <button className="btn secondary" type="button" onClick={() => router.push("/utilities")}>
            {t("util.back")}
          </button>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <form className="form wide" onSubmit={onSubmit}>
        {item.agents.map((agent) => (
          <section className="card" key={agent.id} style={{ maxWidth: "none" }}>
            <div className="chip-row">
              {agent.uses_llm ? (
                <ModelChip
                  value={agent.model}
                  models={models}
                  onChange={models.length ? (model) => pickModel(agent.id, model) : undefined}
                  label={t("agents.model")}
                />
              ) : null}
            </div>
            <h2>
              <Link href={`/agents/${agent.id}`}>{agent.name}</Link>
              <span className="muted"> · {agent.slug}</span>
              <span className={`badge ${agent.status}`}>{t(`status.${agent.status}`)}</span>
            </h2>
            <p className="muted">{localizeAgentSummary(agent.slug, agent.summary, locale)}</p>
            <p className="muted">
              {t("agents.tools")}: {agent.tools.join(", ") || t("agents.noTools")}
            </p>
            {(knobs[agent.slug] || []).length ? (
              <KnobFields knobs={knobs[agent.slug] || []} onChange={(key, value) => changeKnob(agent.slug, key, value)} />
            ) : (
              <p className="muted">{t("knobs.none")}</p>
            )}
          </section>
        ))}
        <button className="btn" type="submit">
          {t("util.save")}
        </button>
      </form>
    </>
  );
}
