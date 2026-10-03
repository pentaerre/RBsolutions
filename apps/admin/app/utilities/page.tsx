"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, type UtilityItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function UtilitiesPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<UtilityItem[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiGet<{ utilities: UtilityItem[] }>("/utilities")
      .then((payload) => setItems(payload.utilities))
      .catch((err: Error) => setMessage(err.message));
  }, []);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("util.title")}</h1>
          <p>{t("util.lead")}</p>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="tool-list">
        {items.map((item) => (
          <article className="card" key={item.slug}>
            <h3>
              <Link href={`/utilities/${item.slug}`}>{t(`util.${item.slug}.name`) === `util.${item.slug}.name` ? item.name : t(`util.${item.slug}.name`)}</Link>
            </h3>
            <p>{t(`util.${item.slug}.summary`) === `util.${item.slug}.summary` ? item.summary : t(`util.${item.slug}.summary`)}</p>
            <p className="muted">{item.agents.map((agent) => agent.name).join(" · ")}</p>
          </article>
        ))}
      </div>
    </>
  );
}
