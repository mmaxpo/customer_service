import { useCallback } from "react";
import type { Node } from "@xyflow/react";
import type { AgentToolCatalogItem } from "@/platform/api";

export function useWorkflowToolNodes(
  setNodes: React.Dispatch<React.SetStateAction<Node[]>>
) {
  const addToolNode = useCallback(
    (tool: AgentToolCatalogItem) => {
      const id = crypto.randomUUID();

      setNodes((current) => [
        ...current,
        {
          id,
          type: "editable",
          position: {
            x: 120 + current.length * 40,
            y: 120 + current.length * 40,
          },
          data: {
            label: tool.title,
            nodeType: "tool.reference",
            name: tool.title,
            tool_name: tool.name,
            tool_title: tool.title,
            tool_description: tool.description,
            save_as: `${tool.name}_result`,
          },
        },
      ]);
    },
    [setNodes]
  );

  return {
    addToolNode,
  };
}
