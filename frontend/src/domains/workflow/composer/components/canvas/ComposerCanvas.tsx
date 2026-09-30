"use client";

import {
  Background,
  Panel,
  ReactFlow,
  type Connection,
  type Edge,
  type EdgeTypes,
  type NodeTypes,
  type OnEdgesChange,
  type OnNodesChange,
  type OnSelectionChangeParams,
} from "@xyflow/react";

import MissionMapOverlay from "@/domains/workflow/composer/components/canvas/MissionMapOverlay";
import MissionMapLegend from "@/domains/workflow/composer/components/canvas/MissionMapLegend";
import MissionMapHealthBadge from "@/domains/workflow/composer/components/canvas/MissionMapHealthBadge";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
  nodeTypes: NodeTypes;
  edgeTypes: EdgeTypes;
  onConnect: (connection: Connection) => void;
  onNodesChange: OnNodesChange<ComposerNodeType>;
  onEdgesChange: OnEdgesChange<ComposerEdge>;
  onInit: (instance: unknown) => void;
  onSelectionChange: (params: OnSelectionChangeParams) => void;
  onEdgesDelete: (edges: Edge[]) => void;
  emptyState: React.ReactNode;
};

export default function ComposerCanvas({
  nodes,
  edges,
  nodeTypes,
  edgeTypes,
  onConnect,
  onNodesChange,
  onEdgesChange,
  onInit,
  onSelectionChange,
  onEdgesDelete,
  emptyState,
}: Props) {
  return (
    <div className="relative h-full w-full">
      <MissionMapOverlay nodesCount={nodes.length} edgesCount={edges.length} />
      <MissionMapLegend />
      <MissionMapHealthBadge nodes={nodes} edges={edges} />

      <ReactFlow
      className="workflow-merchant-flow rounded-[28px]"
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onConnect={onConnect}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onInit={onInit}
      onSelectionChange={onSelectionChange}
      fitView
      deleteKeyCode={["Delete", "Backspace"]}
      onEdgesDelete={onEdgesDelete}
    >
      {nodes.length === 0 && (
        <Panel position="top-center">{emptyState}</Panel>
      )}

      <Background color="#94a3b8" gap={22} size={1.2} />
      </ReactFlow>
    </div>
  );
}
