"use client";

import { formatClassifyNote, localizeSource, workshopPhase } from "@/lib/catalog-i18n";
import type { LibraryDocument } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { ClassPills } from "@/components/class-pills";

export function formatBytes(bytes: number) {
  if (!bytes) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value >= 10 || index === 0 ? Math.round(value) : value.toFixed(1)} ${units[index]}`;
}

export function formatStamp(value: string) {
  if (!value) {
    return "—";
  }
  return value.replace("T", " ").slice(0, 19);
}

export function PhaseBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const phase = workshopPhase(status);
  return <span className={`badge phase-${phase}`}>{t(`docs.phase.${phase}`)}</span>;
}

export function MethodBadge({ method }: { method?: string | null }) {
  const { t } = useI18n();
  const key = method || "none";
  return <span className={`badge method-${key}`}>{t(`docs.method.${key}`)}</span>;
}

export function DocumentCard({ doc, onPromote }: { doc: LibraryDocument; onPromote?: (id: string) => void }) {
  const { t, locale } = useI18n();
  return (
    <div className="card">
      <h2>{doc.filename}</h2>
      <p className="muted">{doc.rel_path}</p>
      <p>{doc.summary || t("lib.noSummary")}</p>
      <dl className="meta-list">
        <div>
          <dt>{t("lib.bytes")}</dt>
          <dd>{formatBytes(doc.size_bytes)}</dd>
        </div>
        <div>
          <dt>{t("lib.created")}</dt>
          <dd>{formatStamp(doc.file_created_at || doc.created_at)}</dd>
        </div>
        <div>
          <dt>{t("lib.absPath")}</dt>
          <dd className="path">{doc.abs_path || "—"}</dd>
        </div>
        <div>
          <dt>{t("lib.class")}</dt>
          <dd>
            <ClassPills l1={doc.taxonomy_l1} l2={doc.taxonomy_l2} empty={t("lib.unclassified")} />
          </dd>
        </div>
        <div>
          <dt>{t("docs.status")}</dt>
          <dd>
            <PhaseBadge status={doc.status} />
          </dd>
        </div>
        <div>
          <dt>{t("docs.how")}</dt>
          <dd>
            <MethodBadge method={doc.classify_method} />
          </dd>
        </div>
        {doc.classify_note || doc.error ? (
          <div>
            <dt>{t("docs.note")}</dt>
            <dd>{formatClassifyNote(doc.classify_method || "", doc.classify_note || doc.error || "", t)}</dd>
          </div>
        ) : null}
        <div>
          <dt>{t("docs.source")}</dt>
          <dd>{localizeSource(doc.source, locale)}</dd>
        </div>
      </dl>
      <div className="chip-row">
        {(doc.keywords || []).map((word) => (
          <span className="source" key={word}>
            {word}
          </span>
        ))}
        {doc.ocr_used ? <span className="badge live">OCR</span> : null}
        {doc.rag_selected ? <span className="badge live">{t("lib.inRag")}</span> : null}
      </div>
      {onPromote && !doc.rag_selected ? (
        <div className="actions" style={{ marginTop: 12 }}>
          <button className="btn" type="button" onClick={() => onPromote(doc.id)}>
            {t("lib.promoteOne")}
          </button>
        </div>
      ) : null}
    </div>
  );
}
