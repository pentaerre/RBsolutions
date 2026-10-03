"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet, apiSend } from "@/lib/api";
import { CrossAppLink, useI18n } from "@/lib/i18n";
import { localizeGraphPayload } from "@/lib/graph-i18n";

type GraphNode = {
  id: string;
  label: string;
  kind: string;
  detail?: string;
  layer?: number;
  row?: number;
  count?: number;
  hot?: boolean;
  model?: string;
};
type GraphEdge = { from: string; to: string; label?: string };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };
type FlowHop = {
  id: string;
  agent: string;
  status: string;
  label: string;
  summary: string;
  count: number;
  model?: string;
  files: { id: string; filename: string; rel_path: string; status: string; taxonomy_l1?: string; taxonomy_l2?: string }[];
};
type FlowPayload = {
  hops: FlowHop[];
  counts: Record<string, number>;
  total: number;
  line: GraphData;
  documents: FlowHop["files"];
};
type GraphPayload = {
  architecture: GraphData;
  detail: GraphData;
  rag: { method: GraphData; knowledge: GraphData };
  runtime: GraphData;
  pipeline: GraphData;
  platform: GraphData;
  knowledge: GraphData;
  explain: string;
  stores: Record<string, string>;
  flow?: FlowPayload;
};

type ViewId = "architecture" | "flow" | "rag";

const VIEW_KEYS: { id: ViewId; title: string; help: string }[] = [
  { id: "architecture", title: "graph.architecture", help: "graph.architectureHelp" },
  { id: "flow", title: "graph.flow", help: "graph.flowHelp" },
  { id: "rag", title: "graph.rag", help: "graph.ragHelp" },
];

const KINDS: Record<string, { fill: string; stroke: string; text: string }> = {
  start: { fill: "#38bdf8", stroke: "#7dd3fc", text: "#082028" },
  router: { fill: "#f5a524", stroke: "#fcd34d", text: "#1a1408" },
  agent: { fill: "#a78bfa", stroke: "#ddd6fe", text: "#1a1028" },
  tool: { fill: "#fb923c", stroke: "#fdba74", text: "#1a1008" },
  app: { fill: "#22d3ee", stroke: "#67e8f9", text: "#082028" },
  store: { fill: "#34d399", stroke: "#6ee7b7", text: "#062018" },
  entity: { fill: "#facc15", stroke: "#fde047", text: "#1a1608" },
  document: { fill: "#f472b6", stroke: "#f9a8d4", text: "#1a0814" },
  chunk: { fill: "#64748b", stroke: "#94a3b8", text: "#f8fafc" },
};

const HOP_KIND: Record<string, string> = {
  watchman: "start",
  reader: "agent",
  taxonomist: "agent",
  clerk: "agent",
  chunker: "store",
  reviewer: "tool",
};

export default function GraphPage() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<GraphPayload | null>(null);
  const [flow, setFlow] = useState<FlowPayload | null>(null);
  const [view, setView] = useState<ViewId>("architecture");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<GraphPayload>("/graph")
      .then((payload) => {
        setData(payload);
        if (payload.flow) {
          setFlow(payload.flow);
        }
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (view !== "flow") {
      return;
    }
    const tick = () => {
      apiGet<FlowPayload>("/flow?taxonomist=taxonomist")
        .then(setFlow)
        .catch(() => undefined);
    };
    tick();
    const id = window.setInterval(tick, 4000);
    return () => window.clearInterval(id);
  }, [view]);

  const picture = useMemo(() => (data ? localizeGraphPayload(data, locale) : null), [data, locale]);

  const legendKinds = useMemo(() => {
    if (!picture) {
      return Object.keys(KINDS);
    }
    const graphs =
      view === "architecture"
        ? [picture.architecture]
        : view === "flow"
          ? [flow?.line || picture.pipeline]
          : [picture.rag.method, picture.rag.knowledge];
    const present = new Set(graphs.flatMap((graph) => graph.nodes.map((node) => node.kind)));
    return Object.keys(KINDS).filter((kind) => present.has(kind));
  }, [picture, view, flow]);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("graph.title")}</h1>
          <p>{t("graph.lead")}</p>
        </div>
        {view === "flow" ? (
          <div className="actions">
            <CrossAppLink port={3000} path="/library?taxonomist=taxonomist">
              {t("graph.openLibrary")}
            </CrossAppLink>
            <button
              className="btn"
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await apiSend("/library/run?taxonomist=taxonomist", "POST");
                  const next = await apiGet<FlowPayload>("/flow?taxonomist=taxonomist");
                  setFlow(next);
                } catch (err) {
                  setError(err instanceof Error ? err.message : t("graph.runFailed"));
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? t("graph.running") : t("graph.runLine")}
            </button>
          </div>
        ) : null}
      </div>
      {error ? <p className="warn">{error}</p> : null}
      <div className="tabs">
        {VIEW_KEYS.map((item) => (
          <button
            key={item.id}
            className={view === item.id ? "btn" : "btn secondary"}
            onClick={() => setView(item.id)}
          >
            {t(item.title)}
          </button>
        ))}
      </div>
      <p className="muted" style={{ marginTop: -8, marginBottom: 16 }}>
        {t(VIEW_KEYS.find((item) => item.id === view)?.help || "")}
      </p>
      {loading || !picture ? (
        <p className="muted">{t("graph.loading")}</p>
      ) : view === "architecture" ? (
        <GraphCanvas nodes={picture.architecture.nodes} edges={picture.architecture.edges} markerId="arch" />
      ) : view === "flow" ? (
        <FlowBoard flow={flow} t={t} />
      ) : (
        <>
          <GraphSection title={t("graph.method")}>
            <GraphCanvas nodes={picture.rag.method.nodes} edges={picture.rag.method.edges} markerId="rag-method" />
          </GraphSection>
          <GraphSection title={t("graph.live")}>
            <GraphCanvas nodes={picture.rag.knowledge.nodes} edges={picture.rag.knowledge.edges} markerId="rag-live" />
          </GraphSection>
        </>
      )}
      <div className="graph-legend">
        {legendKinds.map((kind) => {
          const color = KINDS[kind];
          return (
            <span
              key={kind}
              className="legend-chip"
              style={{
                background: color.fill,
                color: color.text,
                borderColor: color.stroke,
              }}
            >
              <span className="legend-swatch" style={{ background: color.fill, boxShadow: `0 0 0 2px ${color.stroke}` }} />
              {t(`kind.${kind}`)}
            </span>
          );
        })}
      </div>
      {picture && view !== "flow" ? (
        <div className="card" style={{ marginTop: 20 }}>
          <h2>{t("graph.stores")}</h2>
          <p className="muted">
            {t("graph.storesLine", {
              postgres: picture.stores.postgres,
              qdrant: picture.stores.qdrant,
              neo4j: picture.stores.neo4j,
            })}
          </p>
          <details>
            <summary>{t("graph.catalog")}</summary>
            <pre className="explain">{picture.explain}</pre>
          </details>
        </div>
      ) : null}
    </>
  );
}

function FlowBoard({
  flow,
  t,
}: {
  flow: FlowPayload | null;
  t: (key: string, vars?: Record<string, string | number>) => string;
}) {
  if (!flow) {
    return <p className="muted">{t("graph.loading")}</p>;
  }
  return (
    <>
      <div className="hop-row">
        {flow.hops.map((hop) => (
          <article
            className={`card hop${hop.count ? " hot" : ""}`}
            key={hop.id}
            style={{ borderTop: `4px solid ${(KINDS[HOP_KIND[hop.id] || "agent"] || KINDS.agent).fill}` }}
          >
            <div className="chip-row">
              <p className="muted" style={{ margin: 0 }}>{t(`flow.agent.${hop.id}`)}</p>
              {hop.model ? <span className="badge model">{hop.model.replace(/:latest$/, "")}</span> : null}
            </div>
            <h2>{hop.count}</h2>
            <p>{t(`flow.hop.${hop.id}`)}</p>
            {hop.files.slice(0, 3).map((file) => (
              <p className="muted hop-file" key={file.id}>
                {file.filename}
              </p>
            ))}
          </article>
        ))}
      </div>
      <GraphSection title={t("graph.flowLine")}>
        <GraphCanvas nodes={flow.line.nodes} edges={flow.line.edges} markerId="flow-line" />
      </GraphSection>
      <div className="card" style={{ maxWidth: "none" }}>
        <h2>{t("graph.files", { count: flow.total })}</h2>
        <table className="table">
          <thead>
            <tr>
              <th>{t("graph.colFile")}</th>
              <th>{t("graph.colHop")}</th>
              <th>{t("graph.colClass")}</th>
            </tr>
          </thead>
          <tbody>
            {flow.documents.length === 0 ? (
              <tr>
                <td colSpan={3} className="muted">
                  {t("graph.noFiles")}
                </td>
              </tr>
            ) : (
              flow.documents.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    {doc.filename}
                    <div className="muted">{doc.rel_path}</div>
                  </td>
                  <td>{t(`flow.status.${doc.status}`) === `flow.status.${doc.status}` ? doc.status : t(`flow.status.${doc.status}`)}</td>
                  <td>{doc.taxonomy_l1 ? `${doc.taxonomy_l1} / ${doc.taxonomy_l2}` : "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

function GraphSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="graph-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

const NODE_W = 168;
const NODE_H = 56;

function GraphCanvas({
  nodes,
  edges,
  markerId,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  markerId: string;
}) {
  const { t } = useI18n();
  const layout = useMemo(() => layoutGraph(nodes, edges), [nodes, edges]);
  const xs = Object.values(layout).map((item) => item.x);
  const ys = Object.values(layout).map((item) => item.y);
  const width = Math.max(960, ...(xs.length ? xs.map((x) => x + NODE_W + 48) : [960]));
  const height = Math.max(380, ...(ys.length ? ys.map((y) => y + NODE_H + 48) : [380]));

  if (nodes.length === 0) {
    return (
      <p className="muted">
        {t("graph.empty")}
      </p>
    );
  }

  return (
    <div className="graph-wrap">
      <svg className="graph-canvas" viewBox={`0 0 ${width} ${height}`} width={width} height={height}>
        <defs>
          <marker id={markerId} markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L8,3 L0,6 z" fill="var(--accent)" />
          </marker>
        </defs>
        {edges.map((edge) => {
          const from = layout[edge.from];
          const to = layout[edge.to];
          if (!from || !to) {
            return null;
          }
          const points = edgePoints(from, to);
          const labelX = points.x1 + (points.x2 - points.x1) * 0.55;
          const labelY = points.y1 + (points.y2 - points.y1) * 0.55 - 6;
          return (
            <g key={`${edge.from}-${edge.to}-${edge.label || ""}`}>
              <line
                x1={points.x1}
                y1={points.y1}
                x2={points.x2}
                y2={points.y2}
                stroke="var(--line-strong)"
                strokeWidth="1.6"
                markerEnd={`url(#${markerId})`}
              />
              {edge.label ? (
                <text x={labelX} y={labelY} fill="var(--text)" fontSize="10" textAnchor="middle">
                  {edge.label}
                </text>
              ) : null}
            </g>
          );
        })}
        {nodes.map((node) => {
          const pos = layout[node.id];
          if (!pos) {
            return null;
          }
          const palette = KINDS[node.kind] || KINDS.agent;
          const stroke = node.hot ? "var(--text)" : palette.stroke;
          const subtitle = node.count != null
            ? String(node.count)
            : node.model
              ? node.model.replace(/:latest$/, "")
              : truncate(node.detail || t(`kind.${node.kind}`), 28);
          return (
            <g key={node.id}>
              <rect
                x={pos.x}
                y={pos.y}
                width={NODE_W}
                height={NODE_H}
                rx="10"
                fill={palette.fill}
                stroke={stroke}
                strokeWidth={node.hot ? 3 : 1.5}
              />
              <text x={pos.x + NODE_W / 2} y={pos.y + 24} fill={palette.text} fontSize="12" fontWeight="700" textAnchor="middle">
                {truncate(node.label, 22)}
              </text>
              <text x={pos.x + NODE_W / 2} y={pos.y + 42} fill={palette.text} fontSize="10" textAnchor="middle" opacity={0.85}>
                {subtitle}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function truncate(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function edgePoints(from: { x: number; y: number }, to: { x: number; y: number }) {
  const pad = 6;
  if (to.x > from.x + NODE_W / 2) {
    return {
      x1: from.x + NODE_W,
      y1: from.y + NODE_H / 2,
      x2: to.x - pad,
      y2: to.y + NODE_H / 2,
    };
  }
  if (to.x + NODE_W / 2 < from.x) {
    return {
      x1: from.x,
      y1: from.y + NODE_H / 2,
      x2: to.x + NODE_W + pad,
      y2: to.y + NODE_H / 2,
    };
  }
  if (to.y > from.y) {
    return {
      x1: from.x + NODE_W / 2,
      y1: from.y + NODE_H,
      x2: to.x + NODE_W / 2,
      y2: to.y - pad,
    };
  }
  return {
    x1: from.x + NODE_W / 2,
    y1: from.y,
    x2: to.x + NODE_W / 2,
    y2: to.y + NODE_H + pad,
  };
}

function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): Record<string, { x: number; y: number }> {
  const layered = nodes.length > 0 && nodes.every((node) => node.layer !== undefined && node.row !== undefined);
  if (layered) {
    const positions: Record<string, { x: number; y: number }> = {};
    for (const node of nodes) {
      positions[node.id] = { x: 40 + (node.layer || 0) * 200, y: 36 + (node.row || 0) * 88 };
    }
    return positions;
  }
  const ids = new Set(nodes.map((node) => node.id));
  const indegree: Record<string, number> = {};
  const children: Record<string, string[]> = {};
  for (const node of nodes) {
    indegree[node.id] = 0;
    children[node.id] = [];
  }
  for (const edge of edges) {
    if (!ids.has(edge.from) || !ids.has(edge.to) || edge.from === edge.to) {
      continue;
    }
    children[edge.from].push(edge.to);
    indegree[edge.to] += 1;
  }
  const rank: Record<string, number> = {};
  const queue = nodes.filter((node) => indegree[node.id] === 0).map((node) => node.id);
  for (const id of queue) {
    rank[id] = 0;
  }
  const remaining = { ...indegree };
  for (let index = 0; index < queue.length; index += 1) {
    const id = queue[index];
    for (const child of children[id]) {
      rank[child] = Math.max(rank[child] ?? 0, (rank[id] || 0) + 1);
      remaining[child] -= 1;
      if (remaining[child] === 0) {
        queue.push(child);
      }
    }
  }
  for (const node of nodes) {
    if (rank[node.id] === undefined) {
      rank[node.id] = 0;
    }
  }
  const columns: Record<number, GraphNode[]> = {};
  for (const node of nodes) {
    const column = rank[node.id];
    columns[column] = columns[column] || [];
    columns[column].push(node);
  }
  const positions: Record<string, { x: number; y: number }> = {};
  Object.keys(columns)
    .map(Number)
    .sort((a, b) => a - b)
    .forEach((column) => {
      columns[column].forEach((node, row) => {
        positions[node.id] = { x: 40 + column * 220, y: 36 + row * 92 };
      });
    });
  return positions;
}
