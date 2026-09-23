"use client";

import { useEffect, useState } from "react";
import { apiGet, type Health } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function OverviewPage() {
  const { t } = useI18n();
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Health>("/health")
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

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
          <h2>{t("home.database")}</h2>
          <p className={health ? "ok" : "muted"}>{health?.platform.database || "…"}</p>
        </article>
        <article className="card">
          <h2>{t("home.apps")}</h2>
          <p>{health ? health.platform.apps : "…"}</p>
          <p className="muted">{t("home.appsHint")}</p>
        </article>
        <article className="card">
          <h2>{t("home.tools")}</h2>
          <p>{health ? health.platform.tools : "…"}</p>
          <p className="muted">{t("home.toolsHint")}</p>
        </article>
        <article className="card">
          <h2>{t("home.agents")}</h2>
          <p>{health ? health.platform.agents : "…"}</p>
          <p className="muted">{t("home.agentsHint")}</p>
        </article>
        <article className="card">
          <h2>{t("home.ollama")}</h2>
          <p className={health?.ollama.ok ? "ok" : "warn"}>
            {health?.ollama.ok ? t("home.connected") : health?.ollama.error || "…"}
          </p>
          <p className="muted">{health?.ollama.models.join(", ")}</p>
        </article>
        <article className="card">
          <h2>{t("home.index")}</h2>
          <p>{health ? t("home.chunks", { count: health.index.chunks }) : "…"}</p>
        </article>
      </div>
    </>
  );
}
