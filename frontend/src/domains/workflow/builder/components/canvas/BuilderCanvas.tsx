"use client";

import {
  Background,
  ConnectionLineType,
  Controls,
  Panel,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
} from "@xyflow/react";

type BuilderCanvasProps = {
  nodes: Node[];
  edges: Edge[];
  nodeTypes: Record<string, any>;
  edgeTypes: Record<string, any>;
  onNodesChange: OnNodesChange<Node>;
  onEdgesChange: OnEdgesChange<Edge>;
  onConnect: (connection: Connection) => void;
  onSelectionChange: (params: OnSelectionChangeParams) => void;
  isValidConnection: (connection: Connection) => boolean;
  connectionStatus?: string;
};

export default function BuilderCanvas({
  nodes,
  edges,
  nodeTypes,
  edgeTypes,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onSelectionChange,
  isValidConnection,
  connectionStatus,
}: BuilderCanvasProps) {
  return (
    <ReactFlow
      className="workflow-builder-flow"
      nodes={nodes}
      edges={edges}
      edgeTypes={edgeTypes}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onSelectionChange={onSelectionChange}
      deleteKeyCode={["Backspace", "Delete"]}
      connectionLineType={ConnectionLineType.SmoothStep}
      defaultEdgeOptions={{
        type: "gradient",
        animated: true,
        style: { strokeWidth: 2 },
      }}
      defaultViewport={{ x: 80, y: 80, zoom: 0.75 }}
      minZoom={0.35}
      maxZoom={1.4}
      isValidConnection={isValidConnection}
    >
      <svg>
        <defs>
          <linearGradient id="tajeran-edge-gradient">
            <stop offset="0%" stopColor="#e92a67" />
            <stop offset="50%" stopColor="#a853ba" />
            <stop offset="100%" stopColor="#2a8af6" />
          </linearGradient>

          <marker
            id="tajeran-edge-circle"
            viewBox="-5 -5 10 10"
            refX="0"
            refY="0"
            markerUnits="strokeWidth"
            markerWidth="10"
            markerHeight="10"
            orient="auto"
          >
            <circle stroke="#2a8af6" strokeOpacity="0.8" r="2" cx="0" cy="0" />
          </marker>
        </defs>
      </svg>

      <Background />
      <Controls />

      {connectionStatus && (
        <Panel position="bottom-center">
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs font-medium text-amber-800 shadow-sm">
            {connectionStatus}
          </div>
        </Panel>
      )}
    </ReactFlow>
  );
}
