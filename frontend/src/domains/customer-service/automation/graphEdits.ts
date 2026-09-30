import type { Graph, LibraryItem, RawNode, RawWorkflow } from "./api";

// Steps every workflow needs; the editor never removes these.
export const FIXED_NODE_TYPES = new Set(["trigger.message", "response"]);

const ENGINE_KEYS = new Set(["nodeType", "node_type", "name"]);

export function humanizeId(id: string) {
  const words = id.replace(/[_\-.]+/g, " ").trim();
  return words ? words[0].toUpperCase() + words.slice(1) : id;
}

export function nodeLabel(node: RawNode) {
  return typeof node.data.label === "string" && node.data.label ? node.data.label : humanizeId(node.id);
}

export function toGraph(workflow: RawWorkflow, library: LibraryItem[]): Graph {
  const byType = new Map(library.map((item) => [item.node_type, item]));
  return {
    nodes: workflow.nodes.map((node) => {
      const item = byType.get(node.data.nodeType);
      return {
        id: node.id,
        type: node.data.nodeType,
        label: nodeLabel(node),
        type_title: item?.name ?? node.data.nodeType,
        category: item?.group ?? null,
        risk: item?.needs_approval ? "sensitive" : null,
      };
    }),
    edges: workflow.edges.map((edge) => ({ source: edge.source, target: edge.target, condition: edge.condition ?? null })),
  };
}

function uniqueId(workflow: RawWorkflow, nodeType: string) {
  const stem = nodeType.split(".").pop()!.replace(/[^a-z0-9]+/gi, "_").toLowerCase();
  const taken = new Set(workflow.nodes.map((n) => n.id));
  let index = 1;
  while (taken.has(`${stem}_${index}`)) index += 1;
  return `${stem}_${index}`;
}

/** Insert a library step on an existing connection: A → new → B. */
export function insertOnEdge(workflow: RawWorkflow, edgeIndex: number, item: LibraryItem) {
  const edge = workflow.edges[edgeIndex];
  const id = uniqueId(workflow, item.node_type);
  const defaults = Object.fromEntries(
    Object.entries(item.default_config).filter(([key]) => !ENGINE_KEYS.has(key)),
  );
  const data: RawNode["data"] = { ...defaults, nodeType: item.node_type, label: item.name };

  // A condition continues along its default branch until the admin adds rules.
  const isRouter = item.node_type === "router.rules";
  if (isRouter) Object.assign(data, { rules: [], default_route: "continue" });

  const edges = [...workflow.edges];
  edges.splice(
    edgeIndex,
    1,
    { ...edge, target: id },
    { source: id, target: edge.target, ...(isRouter ? { condition: "continue" } : {}) },
  );

  return { workflow: { ...workflow, nodes: [...workflow.nodes, { id, data }], edges }, id };
}

/** Remove a step and connect everything before it to everything after it. */
export function removeNode(workflow: RawWorkflow, id: string): RawWorkflow {
  const incoming = workflow.edges.filter((e) => e.target === id);
  const outgoing = workflow.edges.filter((e) => e.source === id);
  const kept = workflow.edges.filter((e) => e.source !== id && e.target !== id);
  const seen = new Set(kept.map((e) => `${e.source}>${e.target}`));

  for (const parent of incoming) {
    for (const child of outgoing) {
      const key = `${parent.source}>${child.target}`;
      if (seen.has(key)) continue;
      seen.add(key);
      kept.push({ source: parent.source, target: child.target, ...(parent.condition ? { condition: parent.condition } : {}) });
    }
  }
  return { ...workflow, nodes: workflow.nodes.filter((n) => n.id !== id), edges: kept };
}

export function updateNodeData(workflow: RawWorkflow, id: string, data: RawNode["data"]): RawWorkflow {
  return { ...workflow, nodes: workflow.nodes.map((n) => (n.id === id ? { ...n, data } : n)) };
}

export function countChanges(base: RawWorkflow, next: RawWorkflow) {
  const before = new Map(base.nodes.map((n) => [n.id, JSON.stringify(n.data)]));
  const after = new Set(next.nodes.map((n) => n.id));
  const added = next.nodes.filter((n) => !before.has(n.id)).length;
  const changed = next.nodes.filter((n) => before.has(n.id) && before.get(n.id) !== JSON.stringify(n.data)).length;
  const removed = base.nodes.filter((n) => !after.has(n.id)).length;
  return { added, changed, removed, total: added + changed + removed };
}
