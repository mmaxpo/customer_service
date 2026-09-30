import type { WorkflowTemplate } from "@/domains/customer-service/api/customer-service";
import type { MissionModel } from "./missionTypes";

function nodeTypeToEntityType(nodeType: string) {
  if (nodeType.includes("agent") || nodeType.includes("llm")) return "agent";
  if (nodeType.includes("shopify") || nodeType.includes("tool")) return "tool";
  if (nodeType.includes("approval")) return "decision";
  if (nodeType.includes("router")) return "decision";
  if (nodeType.includes("kb") || nodeType.includes("knowledge")) return "knowledge";
  if (nodeType.includes("response") || nodeType.includes("reply")) return "response";
  if (nodeType.includes("trigger")) return "mission";
  return "variable";
}

function nodeLabel(node: any) {
  return String(
    node?.data?.name ||
      node?.data?.label ||
      node?.data?.nodeType ||
      node?.id ||
      "Mission step",
  );
}

function nodeDescription(node: any) {
  const data = node?.data || {};
  return String(
    data.system_prompt ||
      data.responsibility ||
      data.description ||
      data.question ||
      data.nodeType ||
      "Mission concept compiled from workflow.",
  );
}

export function compileMissionFromTemplate(template: WorkflowTemplate | null): MissionModel {
  const workflow = (template?.workflow_json || {}) as any;
  const nodes = Array.isArray(workflow.nodes) ? workflow.nodes : [];
  const edges = Array.isArray(workflow.edges) ? workflow.edges : [];

  const missionId = template?.id || "demo-mission";
  const missionName = template?.name || "Mission";
  const missionDescription =
    template?.description || "Compiled mission model from workflow JSON.";

  const entities = [
    {
      id: "mission",
      type: "mission" as const,
      label: missionName,
      description: missionDescription,
    },
    ...nodes.map((node: any) => {
      const nodeType = String(node?.data?.nodeType || node?.type || "");
      return {
        id: String(node.id),
        type: nodeTypeToEntityType(nodeType) as any,
        label: nodeLabel(node),
        description: nodeDescription(node),
      };
    }),
  ];

  const relationships = edges.map((edge: any) => ({
    id: String(edge.id || `${edge.source}-${edge.target}`),
    source: String(edge.source),
    target: String(edge.target),
    label: String(edge?.data?.label || "connects"),
  }));

  if (nodes.length > 0) {
    relationships.unshift({
      id: `mission-${nodes[0].id}`,
      source: "mission",
      target: String(nodes[0].id),
      label: "starts with",
    });
  }

  return {
    id: missionId,
    name: missionName,
    description: missionDescription,
    entities,
    relationships,
  };
}
