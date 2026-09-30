"use client";

import { Plus } from "lucide-react";

import { cn } from "@/platform/utils";

import type { Graph, GraphNode } from "./api";

export type NodeTone = "default" | "new" | "changed" | "removed" | "skipped" | "cause" | "error";

export type NodeDecoration = { tone?: NodeTone; tag?: string; sub?: string };

const NODE_W = 232;
const NODE_H = 60;
const GAP_X = 36;
const GAP_Y = 52;

const toneClass: Record<NodeTone, string> = {
  default: "border-border bg-surface",
  new: "border-dashed border-warning bg-warning/5",
  changed: "border-primary bg-primary/5",
  removed: "border-dashed border-border bg-muted opacity-60",
  skipped: "border-dashed border-border bg-surface text-text-secondary",
  cause: "border-warning bg-warning/10",
  error: "border-danger bg-danger/5",
};

const tagClass: Record<NodeTone, string> = {
  default: "text-text-secondary",
  new: "text-warning",
  changed: "text-primary",
  removed: "text-text-secondary",
  skipped: "text-text-secondary",
  cause: "text-warning",
  error: "text-danger",
};

// Longest-path layering from the entry nodes; enough for the small DAGs
// customer-service workflows use. Loops are cut by the iteration cap.
export function layoutGraph(graph: Graph) {
  const incoming = new Map<string, string[]>();
  graph.nodes.forEach((n) => incoming.set(n.id, []));
  graph.edges.forEach((e) => incoming.get(e.target)?.push(e.source));

  const layer = new Map<string, number>();
  graph.nodes.forEach((n) => layer.set(n.id, 0));
  for (let pass = 0; pass < graph.nodes.length; pass += 1) {
    let changed = false;
    for (const e of graph.edges) {
      const next = (layer.get(e.source) ?? 0) + 1;
      if (layer.has(e.target) && next > (layer.get(e.target) ?? 0) && next < graph.nodes.length) {
        layer.set(e.target, next);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const rows: GraphNode[][] = [];
  graph.nodes.forEach((n) => {
    const index = layer.get(n.id) ?? 0;
    (rows[index] ??= []).push(n);
  });
  const dense = rows.filter(Boolean);
  const widest = Math.max(1, ...dense.map((row) => row.length));
  const width = widest * NODE_W + (widest - 1) * GAP_X;

  const position = new Map<string, { x: number; y: number }>();
  dense.forEach((row, rowIndex) => {
    const rowWidth = row.length * NODE_W + (row.length - 1) * GAP_X;
    const start = (width - rowWidth) / 2;
    row.forEach((node, col) => {
      position.set(node.id, { x: start + col * (NODE_W + GAP_X), y: rowIndex * (NODE_H + GAP_Y) });
    });
  });

  return { position, width, height: dense.length * NODE_H + (dense.length - 1) * GAP_Y, rows: dense };
}

type Point = { x: number; y: number };

// Path for one edge, plus the point in the gap just below its source where
// the "+" and branch label sit. Edges that skip layers run down a lane beside
// the steps in between instead of cutting through them.
function routeEdge(from: Point, to: Point, nodes: Point[]) {
  const x1 = from.x + NODE_W / 2;
  const y1 = from.y + NODE_H;
  const x2 = to.x + NODE_W / 2;
  const y2 = to.y - 2;
  const between = nodes.filter((p) => p.y > from.y && p.y < to.y);

  if (!between.length) {
    const mid = (y1 + y2) / 2;
    const targetY = Math.min(y1 + GAP_Y / 2, mid);
    let best = { x: (x1 + x2) / 2, y: mid, diff: Infinity };
    for (let i = 0; i <= 60; i += 1) {
      const t = i / 60;
      const u = 1 - t;
      // Cubic bezier with control points (x1, mid) and (x2, mid).
      const x = u * u * u * x1 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x2;
      const y = u * u * u * y1 + 3 * u * u * t * mid + 3 * u * t * t * mid + t * t * t * y2;
      const diff = Math.abs(y - targetY);
      if (diff < best.diff) best = { x, y, diff };
    }
    return {
      d: `M${x1},${y1} C${x1},${mid} ${x2},${mid} ${x2},${y2}`,
      anchor: { x: best.x, y: best.y, leftward: x2 < x1 },
    };
  }

  let lane = x1;
  for (let i = 0; i < between.length; i += 1) {
    const hit = between.find((p) => lane > p.x - 12 && lane < p.x + NODE_W + 12);
    if (!hit) break;
    lane = hit.x + NODE_W + GAP_X / 2;
  }
  const gapTop = y1 + GAP_Y / 2;
  const gapBottom = to.y - GAP_Y / 2;
  return {
    d: `M${x1},${y1} C${x1},${gapTop} ${lane},${gapTop} ${lane},${y1 + GAP_Y} L${lane},${to.y - GAP_Y} C${lane},${gapBottom} ${x2},${gapBottom} ${x2},${y2}`,
    anchor: { x: (x1 + lane) / 2, y: gapTop, leftward: lane < x1 || (lane === x1 && x2 < x1) },
  };
}

export function WorkflowGraph({
  graph,
  decorate,
  selectedId,
  onSelect,
  highlightEdge,
  onInsert,
  insertEdge,
}: {
  graph: Graph;
  decorate?: (node: GraphNode) => NodeDecoration;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  highlightEdge?: (source: string, target: string) => boolean;
  /** Edit mode: show a "+" on every connection; called with the edge index. */
  onInsert?: (edgeIndex: number) => void;
  insertEdge?: number | null;
}) {
  const { position, width, height } = layoutGraph(graph);
  const points = [...position.values()];
  const routes = graph.edges.map((edge) => {
    const from = position.get(edge.source);
    const to = position.get(edge.target);
    return from && to ? routeEdge(from, to, points) : null;
  });

  return (
    <div className="relative mx-auto" style={{ width, height }}>
      <svg className="absolute inset-0 overflow-visible" width={width} height={height} aria-hidden>
        <defs>
          <marker id="wf-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" className="fill-text-secondary" />
          </marker>
        </defs>
        {graph.edges.map((edge, index) => {
          const route = routes[index];
          if (!route) return null;
          const strong = highlightEdge?.(edge.source, edge.target) ?? false;
          return (
            <g key={`${edge.source}-${edge.target}-${index}`}>
              <path
                d={route.d}
                fill="none"
                strokeWidth={1.5}
                strokeDasharray={strong ? "5 4" : undefined}
                className={strong ? "stroke-warning" : "stroke-border"}
                markerEnd="url(#wf-arrow)"
              />
              {edge.condition ? (() => {
                const { anchor } = route;
                const offset = onInsert ? 16 : 6;
                return (
                <text
                  x={anchor.leftward ? anchor.x - offset : anchor.x + offset}
                  y={anchor.y + 4}
                  textAnchor={anchor.leftward ? "end" : "start"}
                  className="fill-text-secondary text-[11px]"
                >
                  {edge.condition.replaceAll("_", " ")}
                </text>
                );
              })() : null}
            </g>
          );
        })}
      </svg>

      {onInsert
        ? graph.edges.map((edge, index) => {
            const route = routes[index];
            if (!route) return null;
            const active = insertEdge === index;
            const fromLabel = graph.nodes.find((n) => n.id === edge.source)?.label ?? edge.source;
            const toLabel = graph.nodes.find((n) => n.id === edge.target)?.label ?? edge.target;
            return (
              <button
                key={`insert-${index}`}
                type="button"
                onClick={() => onInsert(index)}
                aria-pressed={active}
                aria-label={`Add a step between ${fromLabel} and ${toLabel}`}
                title="Add a step here"
                className={cn(
                  "absolute z-10 flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-surface text-text-secondary hover:border-primary hover:text-primary",
                )}
                style={{ left: route.anchor.x, top: route.anchor.y }}
              >
                <Plus size={13} aria-hidden />
              </button>
            );
          })
        : null}

      {graph.nodes.map((node) => {
        const pos = position.get(node.id)!;
        const deco = decorate?.(node) ?? {};
        const tone = deco.tone ?? "default";
        const selected = selectedId === node.id;
        const body = (
          <>
            <span className="flex items-baseline justify-between gap-2">
              <span className={cn("truncate text-[13.5px] font-semibold text-foreground", tone === "removed" && "line-through")}>
                {node.label}
              </span>
              {deco.tag ? (
                <span className={cn("shrink-0 text-[10.5px] font-semibold uppercase tracking-wide", tagClass[tone])}>{deco.tag}</span>
              ) : null}
            </span>
            <span className="mt-0.5 block truncate font-mono text-[11.5px] text-text-secondary">
              {deco.sub ?? node.type}
            </span>
          </>
        );
        const className = cn(
          "absolute flex flex-col justify-center rounded-container border px-3 text-left",
          toneClass[tone],
          selected && "ring-2 ring-primary ring-offset-2 ring-offset-background",
        );
        const style = { left: pos.x, top: pos.y, width: NODE_W, height: NODE_H };

        return onSelect ? (
          <button
            key={node.id}
            type="button"
            onClick={() => onSelect(node.id)}
            aria-pressed={selected}
            className={cn(className, "transition-colors hover:border-primary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus")}
            style={style}
          >
            {body}
          </button>
        ) : (
          <div key={node.id} className={className} style={style}>
            {body}
          </div>
        );
      })}
    </div>
  );
}

// Compact row of step dots for workflow cards, in execution order.
export function MiniGraph({ graph, draft = false }: { graph: Graph; draft?: boolean }) {
  const { rows } = layoutGraph(graph);
  return (
    <div className="flex items-center" aria-label={`${graph.nodes.length} steps`} role="img">
      {rows.map((row, index) => (
        <div key={index} className="flex items-center">
          {index > 0 ? <span className={cn("h-px w-3", draft ? "bg-warning/60" : "bg-border")} /> : null}
          <span className="flex flex-col gap-0.5">
            {row.map((node) => (
              <span
                key={node.id}
                title={node.label}
                className={cn(
                  "block h-2 w-2 rounded-full",
                  draft
                    ? "border border-warning"
                    : node.risk === "sensitive"
                      ? "bg-warning"
                      : node.category === "logic" || node.category === "control" || node.type.startsWith("router")
                        ? "bg-text-secondary/50"
                        : "bg-primary/70",
                )}
              />
            ))}
          </span>
        </div>
      ))}
    </div>
  );
}
