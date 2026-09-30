"use client";

import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";

export default function GradientEdge(props: any) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  } = props;

  const [path] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      <svg>
        <defs>
          <linearGradient id={`gradient-${id}`}>
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="50%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
      </svg>

      <BaseEdge
        path={path}
        style={{
          stroke: `url(#gradient-${id})`,
          strokeWidth: 3,
          strokeLinecap: "round",
        }}
      />

      <path
        d={path}
        fill="none"
        stroke="white"
        strokeWidth="2"
        strokeDasharray="12 12"
        opacity="0.8"
      >
        <animate
          attributeName="stroke-dashoffset"
          from="24"
          to="0"
          dur="1s"
          repeatCount="indefinite"
        />
      </path>

      <EdgeLabelRenderer>
        <div />
      </EdgeLabelRenderer>
    </>
  );
}
