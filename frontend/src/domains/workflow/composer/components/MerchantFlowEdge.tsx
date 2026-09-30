"use client";

import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "@xyflow/react";

function labelForEdge(sourceKind?: string, targetKind?: string, route?: string) {
  if (route === "approved") return "Approved";
  if (route === "rejected") return "Rejected";

  if (targetKind === "ai_agent") return "Analyze";
  if (targetKind === "human_approval") return "Approval";
  if (targetKind === "business_router") return "Decide";
  if (targetKind === "knowledge_answer") return "Find answer";
  if (targetKind === "send_response") return "Reply";

  return "Continue";
}

export default function MerchantFlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
  data,
}: EdgeProps) {
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const gradientId = `merchant-edge-gradient-${id}`;
  const glowId = `merchant-edge-glow-${id}`;
  const label = labelForEdge(
    String(data?.sourceKind || ""),
    String(data?.targetKind || ""),
    String(data?.route || ""),
  );

  return (
    <>
      <svg className="absolute h-0 w-0">
        <defs>
          <linearGradient id={gradientId} x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stopColor="#2563eb" />
            <stop offset="45%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>

          <filter id={glowId}>
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke: `url(#${gradientId})`,
          strokeWidth: selected ? 5 : 3,
          strokeLinecap: "round",
          opacity: selected ? 1 : 0.9,
          filter: `url(#${glowId})`,
        }}
      />

      <path
        d={path}
        className="merchant-flow-edge-pulse"
        fill="none"
        stroke="rgba(255,255,255,0.9)"
        strokeWidth="2"
        strokeDasharray="10 14"
        strokeLinecap="round"
      />

      <circle r="4" fill="#7c3aed" className="merchant-flow-edge-dot">
        <animateMotion dur="1.8s" repeatCount="indefinite" path={path} />
      </circle>

      <circle r="2.4" fill="white">
        <animateMotion dur="1.8s" repeatCount="indefinite" path={path} />
      </circle>

      <EdgeLabelRenderer>
        <div
          className="nodrag nopan flex items-center gap-1 rounded-full border border-white/80 bg-white/90 px-2 py-0.5 text-[10px] font-bold text-tajeran-700 shadow-lg shadow-tajeran-100/70 backdrop-blur"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: "all",
          }}
        >
          <span>{label}</span>
          {selected && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                window.dispatchEvent(new CustomEvent("tajeran:delete-merchant-edge", { detail: { edgeId: id } }));
              }}
              className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-50 text-[10px] font-black text-red-600 hover:bg-red-100"
              aria-label="Delete connection"
            >
              ×
            </button>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
