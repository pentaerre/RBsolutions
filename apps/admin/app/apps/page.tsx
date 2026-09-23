"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiSend, type AppItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeKind } from "@/lib/catalog-i18n";

export default function AppsPage() {
  const { t, locale } = useI18n();
  const [apps, setApps] = useState<AppItem[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    slug: "",
    name: "",
    kind: "tool",
    base_url: "http://localhost:3100",
    status: "planned",
    summary: "",
  });

  async function load() {
    const payload = await apiGet<{ apps: AppItem[] }>("/apps");
    setApps(payload.apps);
  }

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await apiSend("/apps", "POST", form);
      setForm({ ...form, slug: "", name: "", summary: "" });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("apps.failed"));
    }
  }

  async function setStatus(app: AppItem, status: string) {
    await apiSend(`/apps/${app.id}`, "PATCH", { status });
    await load();
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("apps.title")}</h1>
          <p>{t("apps.lead")}</p>
        </div>
      </div>
      {message ? <p className="warn">{message}</p> : null}
      <div className="card" style={{ marginBottom: 20 }}>
        <table className="table">
          <thead>
            <tr>
              <th>{t("apps.name")}</th>
              <th>{t("apps.kind")}</th>
              <th>{t("apps.url")}</th>
              <th>{t("apps.status")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {apps.map((app) => (
              <tr key={app.id}>
                <td>
                  {app.name}
                  <div className="muted">{app.slug}</div>
                </td>
                <td>{localizeKind(app.kind, locale)}</td>
                <td>
                  {app.base_url ? (
                    <a href={app.base_url} target="_blank" rel="noreferrer">
                      {app.base_url}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  <span className={`badge ${app.status}`}>{t(`status.${app.status}`)}</span>
                </td>
                <td>
                  {app.status === "live" ? (
                    <button className="btn secondary" onClick={() => setStatus(app, "disabled")}>
                      {t("apps.disable")}
                    </button>
                  ) : (
                    <button className="btn secondary" onClick={() => setStatus(app, "live")}>
                      {t("apps.enable")}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h2>{t("apps.registerTitle")}</h2>
        <form className="form" onSubmit={onSubmit} style={{ marginTop: 12 }}>
          <label>
            {t("apps.slug")}
            <input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} required />
          </label>
          <label>
            {t("apps.name")}
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            {t("apps.kind")}
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="experience">{t("apps.kindExperience")}</option>
              <option value="admin">{t("apps.kindAdmin")}</option>
              <option value="tool">{t("apps.kindTool")}</option>
            </select>
          </label>
          <label>
            {t("apps.baseUrl")}
            <input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          </label>
          <label>
            {t("apps.summary")}
            <textarea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
          </label>
          <button className="btn" type="submit">
            {t("apps.register")}
          </button>
        </form>
      </div>
    </>
  );
}
