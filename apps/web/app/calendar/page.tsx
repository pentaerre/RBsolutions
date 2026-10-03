"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiSend, type LibraryDocument, type LibraryPayload } from "@/lib/api";
import { DocumentCard, MethodBadge, PhaseBadge } from "@/components/document-card";
import { ClassPills } from "@/components/class-pills";
import { useI18n } from "@/lib/i18n";

function ymd(date: Date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function monthCells(cursor: Date) {
  const start = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const pad = (start.getDay() + 6) % 7;
  const days = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
  const cells: (Date | null)[] = [...Array(pad).fill(null)];
  for (let day = 1; day <= days; day += 1) {
    cells.push(new Date(cursor.getFullYear(), cursor.getMonth(), day));
  }
  while (cells.length % 7) {
    cells.push(null);
  }
  return cells;
}

export default function CalendarPage() {
  const { t, locale } = useI18n();
  const [cursor, setCursor] = useState(() => new Date());
  const [selected, setSelected] = useState(() => ymd(new Date()));
  const [docs, setDocs] = useState<LibraryDocument[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  async function load() {
    const payload = await apiGet<LibraryPayload>("/library");
    setDocs(payload.documents);
  }

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
  }, []);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const doc of docs) {
      const key = (doc.file_created_at || doc.created_at || "").slice(0, 10);
      if (!key) {
        continue;
      }
      map.set(key, (map.get(key) || 0) + 1);
    }
    return map;
  }, [docs]);

  const todayDocs = docs.filter((doc) => (doc.file_created_at || doc.created_at || "").startsWith(selected));
  const open = todayDocs.find((doc) => doc.id === openId) || null;

  async function run() {
    setBusy(true);
    setMessage("");
    try {
      const result = await apiSend<{ classified: number; read: number; registered: number }>("/library/run", "POST");
      setMessage(t("lib.ran", { classified: result.classified, read: result.read, registered: result.registered }));
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("lib.runFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function promote(id: string) {
    await apiSend("/library/promote", "POST", { ids: [id] });
    await load();
  }

  const weekdays = locale === "es" ? ["L", "M", "X", "J", "V", "S", "D"] : ["M", "T", "W", "T", "F", "S", "S"];
  const monthLabel = cursor.toLocaleDateString(locale === "es" ? "es" : "en", { month: "long", year: "numeric" });

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("cal.title")}</h1>
          <p>{t("cal.lead")}</p>
        </div>
        <div className="actions">
          <button className="btn" type="button" onClick={run} disabled={busy}>
            {busy ? t("docs.running") : t("lib.runNow")}
          </button>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="library-split">
        <div className="card">
          <div className="cal-nav">
            <button
              className="btn secondary"
              type="button"
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
            >
              ←
            </button>
            <strong style={{ textTransform: "capitalize" }}>{monthLabel}</strong>
            <button
              className="btn secondary"
              type="button"
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
            >
              →
            </button>
          </div>
          <div className="cal-grid">
            {weekdays.map((day, index) => (
              <div key={`${day}-${index}`} className="cal-dow">
                {day}
              </div>
            ))}
            {monthCells(cursor).map((day, index) => {
              if (!day) {
                return <div key={`empty-${index}`} />;
              }
              const key = ymd(day);
              const count = counts.get(key) || 0;
              return (
                <button
                  key={key}
                  type="button"
                  className={`cal-day${key === selected ? " active" : ""}${count ? " has-docs" : ""}`}
                  onClick={() => {
                    setSelected(key);
                    setOpenId(null);
                  }}
                >
                  <span>{day.getDate()}</span>
                  {count ? <em>{count}</em> : null}
                </button>
              );
            })}
          </div>
        </div>
        <div>
          <div className="card">
            <h2>{t("cal.forDay", { day: selected })}</h2>
            {todayDocs.length === 0 ? (
              <p className="muted">{t("cal.empty")}</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>{t("docs.file")}</th>
                    <th>{t("lib.class")}</th>
                    <th>{t("docs.status")}</th>
                    <th>{t("docs.how")}</th>
                  </tr>
                </thead>
                <tbody>
                  {todayDocs.map((doc) => (
                    <tr key={doc.id} className={doc.id === openId ? "row-active" : ""} onClick={() => setOpenId(doc.id)}>
                      <td>{doc.filename}</td>
                      <td>
                        <ClassPills l1={doc.taxonomy_l1} l2={doc.taxonomy_l2} empty={t("lib.unclassified")} />
                      </td>
                      <td>
                        <PhaseBadge status={doc.status} />
                      </td>
                      <td>
                        <MethodBadge method={doc.classify_method} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {open ? <div style={{ marginTop: 16 }}><DocumentCard doc={open} onPromote={promote} /></div> : null}
        </div>
      </div>
    </>
  );
}
