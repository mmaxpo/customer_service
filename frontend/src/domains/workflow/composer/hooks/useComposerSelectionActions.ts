import { useCallback } from "react";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  setSelectedEdgeId: (id: string | null) => void;
  setNodes: (
    updater: (current: ComposerNodeType[]) => ComposerNodeType[],
  ) => void;
  setEdges: (
    updater: (current: ComposerEdge[]) => ComposerEdge[],
  ) => void;
};

export function useComposerSelectionActions({
  selectedNodeId,
  selectedEdgeId,
  setSelectedNodeId,
  setSelectedEdgeId,
  setNodes,
  setEdges,
}: Props) {
  const deleteSelectedNode = useCallback(() => {
    if (!selectedNodeId) return;

    setNodes((current) =>
      current.filter((node) => node.id !== selectedNodeId),
    );

    setEdges((current) =>
      current.filter(
        (edge) =>
          edge.source !== selectedNodeId &&
          edge.target !== selectedNodeId,
      ),
    );

    setSelectedNodeId(null);
  }, [selectedNodeId, setNodes, setEdges, setSelectedNodeId]);

  const duplicateSelectedNode = useCallback(() => {
    if (!selectedNodeId) return;

    setNodes((current) => {
      const selected = current.find(
        (node) => node.id === selectedNodeId,
      );

      if (!selected) return current;

      const id = crypto.randomUUID();

      return [
        ...current,
        {
          ...selected,
          id,
          selected: false,
          position: {
            x: selected.position.x + 48,
            y: selected.position.y + 48,
          },
          data: {
            ...selected.data,
            label: `${selected.data.label} Copy`,
          },
        },
      ];
    });
  }, [selectedNodeId, setNodes]);

  const deleteSelectedEdge = useCallback(() => {
    if (!selectedEdgeId) return;

    setEdges((current) =>
      current.filter((edge) => edge.id !== selectedEdgeId),
    );

    setSelectedEdgeId(null);
  }, [selectedEdgeId, setEdges, setSelectedEdgeId]);

  return {
    deleteSelectedNode,
    duplicateSelectedNode,
    deleteSelectedEdge,
  };
}
