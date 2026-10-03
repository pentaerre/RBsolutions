"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiSend, type LibraryDocument, type LibraryPayload, type TaxonomyNode } from "@/lib/api";
import { DocumentCard, MethodBadge, PhaseBadge } from "@/components/document-card";
import { ModelBadge } from "@/components/model-badge";
import { ClassDot, ClassPills } from "@/components/class-pills";
import { useI18n } from "@/lib/i18n";
import { formatClassifyNote, localizeSource, localizeTaxonomy } from "@/lib/catalog-i18n";

export default function LibraryPage() {
  const { t, locale } = useI18n();
  const [all, setAll] = useState<LibraryDocument[]>([]);
  const [tree, setTree] = useState<TaxonomyNode[]>([]);
  const [cadence, setCadence] = useState("hour");
  const [name, setName] = useState("E&P");
  const [taxonomist, setTaxonomist] = useState("taxonomist");
  const [model, setModel] = useState("");
  const [l1, setL1] = useState("");
  const [l2, setL2] = useState("");
  const [q, setQ] = useState("");
  const [rag, setRag] = useState("");
  const [source, setSource] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const payload = await apiGet<LibraryPayload>("/library");
    setAll(payload.documents);
    setTree(payload.tree);
    setCadence(payload.cadence);
    setName(payload.taxonomy_name);
    setTaxonomist(payload.taxonomist || "taxonomist");
    setModel(payload.taxonomists?.[0]?.model || "");
  }

  useEffect(() => {
    load().catch((err: Error) => setMessage(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const docs = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter((doc) => {
      if (l1 && doc.taxonomy_l1 !== l1) return false;
      if (l2 && doc.taxonomy_l2 !== l2) return false;
      if (source && doc.source !== source) return false;
      if (rag === "yes" && !doc.rag_selected) return false;
      if (rag === "no" && doc.rag_selected) return false;
      if (!needle) return true;
      const blob = `${doc.filename} ${doc.rel_path} ${doc.summary} ${(doc.keywords || []).join(" ")} ${doc.taxonomy_l1} ${doc.taxonomy_l2}`.toLowerCase();
      return blob.includes(needle);
    });
  }, [all, l1, l2, q, rag, source]);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const doc of all) {
      if (doc.taxonomy_l1) {
        map.set(doc.taxonomy_l1, (map.get(doc.taxonomy_l1) || 0) + 1);
      }
      if (doc.taxonomy_l2) {
        map.set(`${doc.taxonomy_l1}/${doc.taxonomy_l2}`, (map.get(`${doc.taxonomy_l1}/${doc.taxonomy_l2}`) || 0) + 1);
      }
    }
    return map;
  }, [all]);

  const open = docs.find((doc) => doc.id === openId) || null;

  async function run() {
    setBusy(true);
    setMessage("");
    try {
      const result = await apiSend<{ classified: number; read: number; registered: number }>(
        "/library/run",
        "POST",
      );
      setMessage(t("lib.ran", { classified: result.classified, read: result.read, registered: result.registered }));
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("lib.runFailed"));
    } finally {
      setBusy(false);
    }
  }

  async function saveCadence(next: string) {
    setCadence(next);
    await apiSend("/library/cadence", "PATCH", { cadence: next, taxonomist });
  }

  async function promote(ids: string[]) {
    if (!ids.length) {
      return;
    }
    setBusy(true);
    try {
      await apiSend("/library/promote", "POST", { ids });
      setPicked([]);
      await load();
    } finally {
      setBusy(false);
    }
  }

  function toggle(id: string) {
    setPicked((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("lib.title")}</h1>
          <p>{t("lib.lead", { name })}</p>
        </div>
        <div className="actions">
          <ModelBadge name={model} />
          <select value={cadence} onChange={(event) => saveCadence(event.target.value)}>
            <option value="hour">{t("lib.hourly")}</option>
            <option value="day">{t("lib.daily")}</option>
            <option value="week">{t("lib.weekly")}</option>
          </select>
          <button className="btn secondary" type="button" onClick={run} disabled={busy}>
            {busy ? t("docs.running") : t("lib.runNow")}
          </button>
          <button className="btn" type="button" onClick={() => promote(picked)} disabled={busy || picked.length === 0}>
            {t("lib.promote")}
          </button>
        </div>
      </div>
      {message ? <p className="muted">{message}</p> : null}
      <div className="library-layout">
        <div className="card">
          <h2>{t("lib.tree")}</h2>
          <button type="button" className={`tree-item${!l1 ? " active" : ""}`} onClick={() => { setL1(""); setL2(""); }}>
            <span className="tree-label">{t("lib.all")}</span>
            <em>{all.length}</em>
          </button>
          {tree.map((group) => (
            <div key={group.id}>
              <button
                type="button"
                className={`tree-item${l1 === group.id && !l2 ? " active" : ""}`}
                onClick={() => {
                  setL1(group.id);
                  setL2("");
                }}
              >
                <ClassDot l1={group.id} />
                <span className="tree-label">{localizeTaxonomy(group.id, locale, group.label)}</span>
                <em>{counts.get(group.id) || 0}</em>
              </button>
              {group.children.map((child) => (
                <button
                  key={child.id}
                  type="button"
                  className={`tree-item nested${l2 === child.id ? " active" : ""}`}
                  onClick={() => {
                    setL1(group.id);
                    setL2(child.id);
                  }}
                >
                  <ClassDot l1={group.id} l2={child.id} />
                  <span className="tree-label">{localizeTaxonomy(child.id, locale, child.label)}</span>
                  <em>{counts.get(`${group.id}/${child.id}`) || 0}</em>
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="card">
          <div className="filter-row">
            <input value={q} onChange={(event) => setQ(event.target.value)} placeholder={t("lib.search")} />
            <select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="">{t("lib.anySource")}</option>
              <option value="email">{localizeSource("email", locale)}</option>
              <option value="folder">{localizeSource("folder", locale)}</option>
              <option value="telegram">{localizeSource("telegram", locale)}</option>
            </select>
            <select value={rag} onChange={(event) => setRag(event.target.value)}>
              <option value="">{t("lib.anyRag")}</option>
              <option value="yes">{t("lib.inRag")}</option>
              <option value="no">{t("lib.notRag")}</option>
            </select>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th />
                <th>{t("docs.file")}</th>
                <th>{t("lib.class")}</th>
                <th>{t("docs.status")}</th>
                <th>{t("docs.how")}</th>
              </tr>
            </thead>
            <tbody>
              {docs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted">
                    {t("lib.empty")}
                  </td>
                </tr>
              ) : (
                docs.map((doc) => (
                  <tr key={doc.id} className={doc.id === openId ? "row-active" : ""}>
                    <td>
                      <input type="checkbox" checked={picked.includes(doc.id)} onChange={() => toggle(doc.id)} />
                    </td>
                    <td onClick={() => setOpenId(doc.id)}>{doc.filename}</td>
                    <td onClick={() => setOpenId(doc.id)}>
                      <ClassPills l1={doc.taxonomy_l1} l2={doc.taxonomy_l2} empty={t("lib.unclassified")} />
                    </td>
                    <td onClick={() => setOpenId(doc.id)}>
                      <PhaseBadge status={doc.status} />
                    </td>
                    <td onClick={() => setOpenId(doc.id)}>
                      <MethodBadge method={doc.classify_method} />
                      {doc.classify_note ? (
                        <p className="muted" style={{ margin: "4px 0 0" }}>
                          {formatClassifyNote(doc.classify_method || "", doc.classify_note, t)}
                        </p>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div>{open ? <DocumentCard doc={open} onPromote={(id) => promote([id])} /> : <p className="muted">{t("lib.pick")}</p>}</div>
      </div>
    </>
  );
}
