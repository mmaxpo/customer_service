"use client";

import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
  addMissionStart: () => void;
  addUnderstandingAgent: () => void;
  addHumanApproval: () => void;
  addFinalOutput: () => void;
  buildRefundMission: () => void;
  buildOrderStatusMission: () => void;
  buildEscalationMission: () => void;
};

type Suggestion = {
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  actionKey?: "mission_start" | "understanding_agent" | "human_approval" | "final_output";
};

function buildSuggestions(nodes: ComposerNodeType[], edges: ComposerEdge[]): Suggestion[] {
  const suggestions: Suggestion[] = [];

  const hasTrigger = nodes.some((node) => node.data.category === "trigger");
  const hasAgent = nodes.some((node) => node.data.category === "agent");
  const hasAction = nodes.some((node) => node.data.category === "action");
  const hasApproval = nodes.some((node) => node.data.category === "approval");
  const hasResponse = nodes.some((node) => node.data.category === "response");
  const hasRefundLikeStep = nodes.some((node) =>
    `${node.data.label} ${node.data.description}`.toLowerCase().includes("refund"),
  );

  if (!hasTrigger) {
    suggestions.push({
      priority: "high",
      title: "Add a mission start",
      description: "Every AI workforce needs a clear starting event, such as a customer message.",
      actionKey: "mission_start",
    });
  }

  if (hasTrigger && !hasAgent) {
    suggestions.push({
      priority: "high",
      title: "Add an understanding agent",
      description: "After the mission starts, add an agent that understands intent, urgency, and needed context.",
      actionKey: "understanding_agent",
    });
  }

  if (hasRefundLikeStep && !hasApproval) {
    suggestions.push({
      priority: "high",
      title: "Add human approval",
      description: "Refund missions should include a human decision checkpoint before money-related actions.",
      actionKey: "human_approval",
    });
  }

  if (hasAgent && !hasAction) {
    suggestions.push({
      priority: "medium",
      title: "Connect a capability",
      description: "Agents become more powerful when they can use tools such as Shopify, knowledge search, or web search.",
    });
  }

  if (!hasResponse) {
    suggestions.push({
      priority: "medium",
      title: "Add a final output",
      description: "A mission should end with a clear result, such as a customer reply or internal decision.",
      actionKey: "final_output",
    });
  }

  if (nodes.length > 1 && edges.length === 0) {
    suggestions.push({
      priority: "high",
      title: "Connect the mission steps",
      description: "Your agents and tools exist, but the mission path is not connected yet.",
    });
  }

  if (suggestions.length === 0) {
    suggestions.push({
      priority: "low",
      title: "Mission structure looks strong",
      description: "Next improvement: run the mission and inspect the live execution proof.",
    });
  }

  return suggestions;
}

function priorityClass(priority: Suggestion["priority"]) {
  if (priority === "high") return "border-red-100 bg-red-50 text-red-700";
  if (priority === "medium") return "border-amber-100 bg-amber-50 text-amber-700";
  return "border-emerald-100 bg-emerald-50 text-emerald-700";
}

export default function MissionArchitectSuggestions({
  nodes,
  edges,
  addMissionStart,
  addUnderstandingAgent,
  addHumanApproval,
  addFinalOutput,
  buildRefundMission,
  buildOrderStatusMission,
  buildEscalationMission,
}: Props) {
  const suggestions = buildSuggestions(nodes, edges);

  const actionByKey = {
    mission_start: addMissionStart,
    understanding_agent: addUnderstandingAgent,
    human_approval: addHumanApproval,
    final_output: addFinalOutput,
  };

  return (
    <section className="mb-4 overflow-hidden rounded-3xl border border-purple-100 bg-white shadow-sm shadow-purple-100/70">
      <div className="bg-gradient-to-br from-purple-700 to-ai-950 p-4 text-white">
        <div className="text-xs font-bold uppercase tracking-wide text-purple-100">
          Mission Architect
        </div>
        <div className="mt-1 text-lg font-extrabold tracking-tight">
          Suggested next improvements
        </div>
        <div className="mt-2 text-xs leading-5 text-purple-100">
          Tajeran reviews the mission structure and suggests what should be added next.
        </div>
      </div>

      <div className="space-y-3 p-4">
        <div className="grid grid-cols-1 gap-2">
          <button
            type="button"
            onClick={buildRefundMission}
            className="rounded-2xl border border-tajeran-100 bg-gradient-to-br from-white to-tajeran-50 p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="text-sm font-extrabold text-slate-950">Build Refund Mission</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">
              Customer message → understand request → check order → approval → reply.
            </div>
          </button>

          <button
            type="button"
            onClick={buildOrderStatusMission}
            className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-white to-emerald-50 p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="text-sm font-extrabold text-slate-950">Build Order Status Mission</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">
              Customer message → check Shopify order → support reply → final output.
            </div>
          </button>

          <button
            type="button"
            onClick={buildEscalationMission}
            className="rounded-2xl border border-purple-100 bg-gradient-to-br from-white to-purple-50 p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="text-sm font-extrabold text-slate-950">Build Escalation Mission</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">
              Customer message → sentiment agent → decision → manager approval → reply.
            </div>
          </button>
        </div>
        {suggestions.slice(0, 4).map((suggestion) => (
          <div
            key={suggestion.title}
            className={["rounded-2xl border p-3", priorityClass(suggestion.priority)].join(" ")}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-extrabold">{suggestion.title}</div>
              <span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-extrabold uppercase">
                {suggestion.priority}
              </span>
            </div>

            <div className="mt-1 text-xs leading-5 opacity-80">
              {suggestion.description}
            </div>

            {suggestion.actionKey && (
              <button
                type="button"
                onClick={actionByKey[suggestion.actionKey]}
                className="mt-3 rounded-xl bg-white/80 px-3 py-1.5 text-xs font-extrabold shadow-sm transition hover:bg-white"
              >
                Add this step
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
