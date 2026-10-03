"use client";

import { useEffect, useState } from "react";
import { apiGet, type DocumentFile, type ExtractedRow } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatClassifyNote, localizeDocType, localizeSource } from "@/lib/catalog-i18n";
import { MethodBadge, PhaseBadge } from "@/components/document-card";

export default function DocumentsPage() {
  const { t, locale } = useI18n();
  const [files, setFiles] = useState<DocumentFile[]>([]);
  const [records, setRecords] = useState<ExtractedRow[]>([]);
  const [dir, setDir] = useState("");
  const [inbox, setInbox] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const payload = await apiGet<{ documents_dir: string; inbox?: string; files: DocumentFile[] }>("/documents");
    setDir(payload.documents_dir);
    setInbox(payload.inbox || "");
    setFiles(payload.files);
    const extracted = await apiGet<{ records: ExtractedRow[] }>("/records");
    setRecords(extracted.records);
  }

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
  }, []);

  async function ingest() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/documents/ingest", { method: "POST" });
      const payload = await response.json();
      setMessage(
        t("docs.pipeline", {
          files: payload.files,
          chunks: payload.chunks,
          records: payload.records || 0,
        }),
      );
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("docs.pipelineFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function pollMail() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/documents/mail", { method: "POST" });
      const payload = await response.json();
      setMessage(payload.message || t("docs.downloaded", { count: payload.count || 0 }));
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("docs.mailFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("docs.title")}</h1>
          <p>{t("docs.lead", { folder: inbox || dir || t("docs.inboxFallback") })}</p>
        </div>
        <div className="actions">
          <button className="btn secondary" onClick={pollMail} disabled={busy}>
            {t("docs.poll")}
          </button>
          <button className="btn" onClick={ingest} disabled={busy}>
            {busy ? t("docs.running") : t("docs.run")}
          </button>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>{t("docs.file")}</th>
              <th>{t("docs.status")}</th>
              <th>{t("docs.how")}</th>
              <th>{t("docs.note")}</th>
              <th>{t("docs.type")}</th>
              <th>{t("docs.source")}</th>
            </tr>
          </thead>
          <tbody>
            {files.length === 0 ? (
              <tr>
                <td colSpan={6} className="muted">
                  {t("docs.empty")}
                </td>
              </tr>
            ) : (
              files.map((file) => (
                <tr key={file.filename + (file.path || "")}>
                  <td>{file.filename}</td>
                  <td>
                    <PhaseBadge status={file.status || (file.indexed ? "indexed" : "received")} />
                  </td>
                  <td>
                    <MethodBadge method={file.classify_method} />
                  </td>
                  <td className="muted">
                    {formatClassifyNote(file.classify_method || "", file.classify_note || file.error || "", t)}
                  </td>
                  <td>{file.doc_type ? localizeDocType(file.doc_type, locale) : "—"}</td>
                  <td>{file.source ? localizeSource(file.source, locale) : "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="card" style={{ marginTop: 20 }}>
        <h2>{t("docs.sqlTitle")}</h2>
        <p className="muted">{t("docs.sqlLead")}</p>
        <table className="table">
          <thead>
            <tr>
              <th>{t("docs.type")}</th>
              <th>{t("docs.file")}</th>
              <th>{t("docs.payload")}</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan={3} className="muted">
                  {t("docs.noRows")}
                </td>
              </tr>
            ) : (
              records.map((row) => (
                <tr key={row.id}>
                  <td>{localizeDocType(row.kind, locale)}</td>
                  <td>{row.filename}</td>
                  <td className="muted">{JSON.stringify(row.payload)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
