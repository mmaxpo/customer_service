import { useCallback } from "react";
import dagre from "@dagrejs/dagre";
import {
  ConnectionLineType,
  Position,
  type Edge,
  type Node,
} from "@xyflow/react";

const nodeWidth = 250;
const nodeHeight = 120;

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR" = "LR"
) {
  const dagreGraph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  const isHorizontal = direction === "LR";

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 60,
    ranksep: 90,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: nodeWidth,
      height: nodeHeight,
    });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  return {
    nodes: nodes.map((node) => {
      const position = dagreGraph.node(node.id);

      return {
        ...node,
        targetPosition: isHorizontal ? Position.Left : Position.Top,
        sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
        position: {
          x: position.x - nodeWidth / 2,
          y: position.y - nodeHeight / 2,
        },
      };
    }),
    edges,
  };
}

export function useWorkflowLayout(
  nodes: Node[],
  edges: Edge[],
  setNodes: (nodes: Node[]) => void,
  setEdges: (edges: Edge[]) => void
) {
  return useCallback(
    (direction: "TB" | "LR") => {
      const layouted = getLayoutedElements(nodes, edges, direction);

      setNodes([...layouted.nodes]);
      setEdges([
        ...layouted.edges.map((edge) => ({
          ...edge,
          type: ConnectionLineType.SmoothStep,
          animated: true,
          style: { strokeWidth: 2 },
        })),
      ]);
    },
    [nodes, edges, setNodes, setEdges]
  );
}
