"use client";

import { useCallback, useEffect, useState } from "react";
import { apiSend } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Signal = {
  id: string;
  kind: string;
  severity: string;
  subject: string;
  sender: string;
  brief: string;
};

type SignalPayload = {
  ok?: boolean;
  signals?: Signal[];
  open?: Signal[];
  delivery?: string;
  notified?: number;
  channel?: string;
};

export default function BriefPage() {
  const { t } = useI18n();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    const payload = await apiSend<SignalPayload>("/tools/signals.list/invoke", "POST", { payload: {} });
    setSignals(payload.signals || []);
  }, []);

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
  }, [load]);

  async function scan() {
    setBusy(true);
    setMessage("");
    try {
      await apiSend("/tools/intake.store_letters/invoke", "POST", { payload: {} });
      const judged = await apiSend<SignalPayload>("/tools/signals.judge/invoke", "POST", { payload: {} });
      const ids = (judged.signals || []).map((item) => item.id);
      await apiSend("/tools/signals.graph/invoke", "POST", { payload: { ids } });
      await apiSend("/tools/signals.book/invoke", "POST", { payload: { ids } });
      await apiSend("/tools/review.hold/invoke", "POST", { payload: { ids } });
      const notified = await apiSend<SignalPayload>("/tools/signals.notify/invoke", "POST", { payload: { ids } });
      const open = await apiSend<SignalPayload>("/tools/signals.list/invoke", "POST", { payload: {} });
      setSignals(open.signals || []);
      if (notified.delivery) {
        setMessage(notified.delivery);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("brief.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("brief.title")}</h1>
          <p>{t("brief.lead")}</p>
        </div>
        <div className="actions">
          <button className="btn" type="button" onClick={scan} disabled={busy}>
            {busy ? t("brief.scanning") : t("brief.scan")}
          </button>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>{t("brief.subject")}</th>
              <th>{t("brief.from")}</th>
              <th>{t("brief.signal")}</th>
              <th>{t("brief.text")}</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
              <tr>
                <td colSpan={4} className="muted">
                  {t("brief.empty")}
                </td>
              </tr>
            ) : (
              signals.map((signal) => (
                <tr key={signal.id}>
                  <td>{signal.subject || "—"}</td>
                  <td>{signal.sender || "—"}</td>
                  <td>{t(`brief.kind.${signal.kind}`) === `brief.kind.${signal.kind}` ? signal.kind : t(`brief.kind.${signal.kind}`)}</td>
                  <td>{signal.brief}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
