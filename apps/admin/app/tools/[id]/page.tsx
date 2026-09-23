"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiSend, type ToolItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function ToolDetailPage() {
  const { t } = useI18n();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [tool, setTool] = useState<ToolItem | null>(null);
  const [config, setConfig] = useState("{}");
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiGet<{ tools: ToolItem[] }>("/tools")
      .then((payload) => {
        const found = payload.tools.find((item) => item.id === params.id) || null;
        setTool(found);
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
      const saved = await apiSend<ToolItem>(`/tools/${tool.id}`, "PATCH", {
        name: tool.name,
        status: tool.status,
        summary: tool.summary,
        kind: tool.kind,
        entrypoint: tool.entrypoint,
        config: parsed,
      });
      setTool(saved);
      setMessage(t("tools.saved"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("tools.saveFailed"));
    }
  }

  if (!tool) {
    return <p className="muted">{message || t("tools.loading")}</p>;
  }

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
        <label>
          {t("tools.config")}
          <textarea value={config} onChange={(e) => setConfig(e.target.value)} />
        </label>
        <button className="btn" type="submit">
          {t("tools.save")}
        </button>
      </form>
    </>
  );
}
