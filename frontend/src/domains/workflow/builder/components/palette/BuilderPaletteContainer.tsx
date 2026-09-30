"use client";

import type { CatalogItem } from "@/domains/workflow/builder/types/catalog";
import type { AgentToolCatalogItem } from "@/platform/api";
import NodePalettePanel from "@/domains/workflow/builder/components/panels/NodePalettePanel";

type Props = {
  catalogStatus: string;
  groupedCatalog: Map<string, CatalogItem[]>;
  addNode: (item: CatalogItem) => void;
  agentTools: AgentToolCatalogItem[];
  addToolNode: (tool: AgentToolCatalogItem) => void;
};

export default function BuilderPaletteContainer({
  catalogStatus,
  groupedCatalog,
  addNode,
  agentTools,
  addToolNode,
}: Props) {
  return (
    <NodePalettePanel
      catalogStatus={catalogStatus}
      groupedCatalog={groupedCatalog}
      addNode={addNode}
      agentTools={agentTools}
      addToolNode={addToolNode}
    />
  );
}
