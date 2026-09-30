"use client";

import type { WorkflowTemplate } from "@/domains/customer-service/api/customer-service";
import { ComposerPreviewPanel } from "@/domains/workflow/composer/components/ComposerPreviewPanel";
import MissionProcessOverview from "@/domains/workflow/composer/components/mission/MissionProcessOverview";
import MissionHealth from "@/domains/workflow/composer/components/mission/MissionHealth";
import MissionStepInspector from "@/domains/workflow/composer/components/mission/MissionStepInspector";
import MissionDataFlow from "@/domains/workflow/composer/components/mission/MissionDataFlow";
import MissionArchitectSuggestions from "@/domains/workflow/composer/components/mission/MissionArchitectSuggestions";
import MissionRuntimeProof from "@/domains/workflow/composer/components/mission/MissionRuntimeProof";
import MissionRuntimeSummary from "@/domains/workflow/composer/components/mission/MissionRuntimeSummary";
import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import type {
  ComposerEdge,
  ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";

type Props = {
  selectedNode: ComposerNodeType | null;
  updateNodeLabel: (nodeId: string, label: string) => void;
  updateNodeConfig: (nodeId: string, patch: Record<string, unknown>) => void;

  loadedTemplate: WorkflowTemplate | null;
  nodes: ComposerNodeType[];
  edges: ComposerEdge[];
  runStatus: string;
  workflowRunId: string;
  runAnswer: string;
  runResult: unknown;
  runtime: unknown;

  addMissionStart: () => void;
  addUnderstandingAgent: () => void;
  addHumanApproval: () => void;
  addFinalOutput: () => void;
  buildRefundMission: () => void;
  buildOrderStatusMission: () => void;
  buildEscalationMission: () => void;
};

export default function ComposerSidePanel({
  selectedNode,
  updateNodeLabel,
  updateNodeConfig,
  loadedTemplate,
  nodes,
  edges,
  runStatus,
  workflowRunId,
  runAnswer,
  runResult,
  runtime,
  addMissionStart,
  addUnderstandingAgent,
  addHumanApproval,
  addFinalOutput,
  buildRefundMission,
  buildOrderStatusMission,
  buildEscalationMission,
}: Props) {
  const nodeStatus = useRunStore((state) => state.nodeStatus);

  return (
    <aside className="w-[420px] overflow-y-auto border-l border-tajeran-100 bg-white p-4">
      <div className="mb-4 rounded-2xl border border-tajeran-100 bg-gradient-to-br from-tajeran-50 to-white p-4">
        <div className="text-xs font-extrabold uppercase tracking-wide text-tajeran-700">
          Safe support automation
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Tajeran reads the customer message, checks Shopify, follows your policy,
          and drafts the reply. Refunds and cancellations always stop here for approval.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-600">
          <span className="rounded-full bg-white px-2.5 py-1">Shopify context</span>
          <span className="rounded-full bg-white px-2.5 py-1">Human approval</span>
          <span className="rounded-full bg-white px-2.5 py-1">Run history</span>
        </div>
      </div>

      <MissionStepInspector
        selectedNode={selectedNode}
        updateNodeLabel={updateNodeLabel}
        updateNodeConfig={updateNodeConfig}
      />

      <MissionHealth nodes={nodes} edges={edges} />

      <MissionArchitectSuggestions
        nodes={nodes}
        edges={edges}
        addMissionStart={addMissionStart}
        addUnderstandingAgent={addUnderstandingAgent}
        addHumanApproval={addHumanApproval}
        addFinalOutput={addFinalOutput}
        buildRefundMission={buildRefundMission}
        buildOrderStatusMission={buildOrderStatusMission}
        buildEscalationMission={buildEscalationMission}
      />

      <MissionRuntimeSummary nodeStatus={nodeStatus} />

      <MissionRuntimeProof
        runStatus={runStatus}
        workflowRunId={workflowRunId}
        runAnswer={runAnswer}
      />

      <ComposerPreviewPanel
        loadedTemplate={loadedTemplate}
        nodes={nodes}
        edges={edges}
        runStatus={runStatus}
        workflowRunId={workflowRunId}
        runAnswer={runAnswer}
        runResult={runResult}
        runtime={runtime}
      />

      <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
        <summary className="cursor-pointer text-sm font-bold text-slate-800">
          Advanced workflow details
        </summary>
        <div className="mt-3">
          <MissionProcessOverview nodes={nodes} edges={edges} />
          <MissionDataFlow nodes={nodes} edges={edges} />
        </div>
      </details>
    </aside>
  );
}
