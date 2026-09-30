"use client";

import type { Node } from "@xyflow/react";
import type { CatalogItem } from "@/domains/workflow/builder/types/catalog";
import type { AgentToolCatalogItem } from "@/platform/api";
import NodeInspectorPanel from "@/domains/workflow/builder/components/panels/NodeInspectorPanel";

type Props = {
  selectedNode: Node | null;
  catalogByType: Map<string, CatalogItem>;
  updateSelectedNodeField: (key: string, value: unknown) => void;
  agentTools: AgentToolCatalogItem[];
  agentToolsStatus: string;
};

export default function BuilderInspectorContainer({
  selectedNode,
  catalogByType,
  updateSelectedNodeField,
  agentTools,
  agentToolsStatus,
}: Props) {
  return (
    <NodeInspectorPanel
      selectedNode={selectedNode}
      catalogByType={catalogByType}
      updateSelectedNodeField={updateSelectedNodeField}
      agentTools={agentTools}
      agentToolsStatus={agentToolsStatus}
    />
  );
}
