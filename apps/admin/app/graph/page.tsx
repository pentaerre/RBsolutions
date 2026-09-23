"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { localizeGraphPayload } from "@/lib/graph-i18n";

type GraphNode = {
  id: string;
  label: string;
  kind: string;
  detail?: string;
  layer?: number;
  row?: number;
};
type GraphEdge = { from: string; to: string; label?: string };
type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] };
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
};

type ViewId = "architecture" | "detail" | "rag";

const VIEW_KEYS: { id: ViewId; title: string; help: string }[] = [
  { id: "architecture", title: "graph.architecture", help: "graph.architectureHelp" },
  { id: "detail", title: "graph.detail", help: "graph.detailHelp" },
  { id: "rag", title: "graph.rag", help: "graph.ragHelp" },
];

const KINDS: Record<string, { fill: string; label: string }> = {
  start: { fill: "#2a333d", label: "start" },
  router: { fill: "#3d4d3a", label: "router" },
  agent: { fill: "#3a3348", label: "agent" },
  tool: { fill: "#3d3a2a", label: "tool" },
  app: { fill: "#2a3a48", label: "app" },
  store: { fill: "#2a3330", label: "store" },
  entity: { fill: "#3a4030", label: "entity" },
  document: { fill: "#3a2e2a", label: "document" },
  chunk: { fill: "#2a2e2a", label: "chunk" },
};

export default function GraphPage() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<GraphPayload | null>(null);
  const [view, setView] = useState<ViewId>("architecture");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<GraphPayload>("/graph")
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const picture = useMemo(() => (data ? localizeGraphPayload(data, locale) : null), [data, locale]);

  const legendKinds = useMemo(() => {
    if (!picture) {
      return Object.keys(KINDS);
    }
    const graphs =
      view === "architecture"
        ? [picture.architecture]
        : view === "detail"
          ? [picture.detail, picture.runtime]
          : [picture.rag.method, picture.rag.knowledge];
    const present = new Set(graphs.flatMap((graph) => graph.nodes.map((node) => node.kind)));
    return Object.keys(KINDS).filter((kind) => present.has(kind));
  }, [picture, view]);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>{t("graph.title")}</h1>
          <p>{t("graph.lead")}</p>
        </div>
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
      ) : view === "detail" ? (
        <>
          <GraphSection title={t("graph.line")}>
            <GraphCanvas nodes={picture.detail.nodes} edges={picture.detail.edges} markerId="detail" />
          </GraphSection>
          <GraphSection title={t("graph.chat")}>
            <GraphCanvas nodes={picture.runtime.nodes} edges={picture.runtime.edges} markerId="runtime" />
          </GraphSection>
        </>
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
        {legendKinds.map((kind) => (
          <span key={kind}>
            <span
              style={{ display: "inline-block", width: 10, height: 10, background: KINDS[kind].fill, marginRight: 6 }}
            />
            {t(`kind.${kind}`)}
          </span>
        ))}
      </div>
      {picture ? (
        <div className="card" style={{ marginTop: 20 }}>
          <h2>{t("graph.stores")}</h2>
          <p className="muted">
            {t("graph.storesLine", {
              postgres: picture.stores.postgres,
              qdrant: picture.stores.qdrant,
              neo4j: picture.stores.neo4j,
            })}
          </p>
          <pre className="explain">{picture.explain}</pre>
        </div>
      ) : null}
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
            <path d="M0,0 L8,3 L0,6 z" fill="#5e7191" />
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
                stroke="#5e7191"
                strokeWidth="1.2"
                markerEnd={`url(#${markerId})`}
              />
              {edge.label ? (
                <text x={labelX} y={labelY} fill="#8b98a5" fontSize="10" textAnchor="middle">
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
          const fill = KINDS[node.kind]?.fill || "#2a333d";
          return (
            <g key={node.id}>
              <rect x={pos.x} y={pos.y} width={NODE_W} height={NODE_H} rx="10" fill={fill} stroke="#5e7191" />
              <text x={pos.x + NODE_W / 2} y={pos.y + 24} fill="#e6edf3" fontSize="12" textAnchor="middle">
                {node.label}
              </text>
              <text x={pos.x + NODE_W / 2} y={pos.y + 42} fill="#8b98a5" fontSize="10" textAnchor="middle">
                {truncate(node.detail || t(`kind.${node.kind}`), 28)}
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
