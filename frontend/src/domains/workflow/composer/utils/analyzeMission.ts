import type {
    ComposerEdge,
    ComposerNode,
} from "../types/composer";

export type MissionIssueLevel =
    | "info"
    | "warning"
    | "error";

export type MissionIssue = {
    level: MissionIssueLevel;
    title: string;
    description: string;
};

export type MissionHealth = {
    score: number;
    issues: MissionIssue[];
};

export function analyzeMission(
    nodes: ComposerNode[],
    edges: ComposerEdge[],
): MissionHealth {

    const issues: MissionIssue[] = [];

    if (nodes.length === 0) {
        issues.push({
            level: "error",
            title: "Mission is empty",
            description: "Add a trigger or an agent.",
        });

        return {
            score: 0,
            issues,
        };
    }

    const triggerCount = nodes.filter(
        n => n.data.category === "trigger",
    ).length;

    if (triggerCount === 0) {
        issues.push({
            level: "error",
            title: "No mission start",
            description: "Every mission needs a trigger.",
        });
    }

    const responseCount = nodes.filter(
        n => n.data.category === "response",
    ).length;

    if (responseCount === 0) {
        issues.push({
            level: "warning",
            title: "No final output",
            description: "Nothing produces a customer-visible result.",
        });
    }

    const connected = new Set<string>();

    edges.forEach(edge => {
        connected.add(edge.source);
        connected.add(edge.target);
    });

    nodes.forEach(node => {
        if (!connected.has(node.id)) {
            issues.push({
                level: "warning",
                title: `"${node.data.label}" is isolated`,
                description: "It never participates in the mission.",
            });
        }
    });

    nodes
        .filter(n => n.data.category === "agent")
        .forEach(agent => {
            const responsibility =
                String(agent.data.config?.responsibility ?? "").trim();

            if (!responsibility) {
                issues.push({
                    level: "warning",
                    title: `"${agent.data.label}" has no responsibility`,
                    description:
                        "Describe exactly what this agent should accomplish.",
                });
            }
        });

    const score =
        Math.max(
            0,
            100 -
            issues.filter(i => i.level === "error").length * 30 -
            issues.filter(i => i.level === "warning").length * 8,
        );

    return {
        score,
        issues,
    };
}
