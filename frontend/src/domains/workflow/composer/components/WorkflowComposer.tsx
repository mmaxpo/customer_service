"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import dagre from "@dagrejs/dagre";
import {
    useEdgesState,
    useNodesState,
    type Connection,
    type NodeTypes,
} from "@xyflow/react";
import { workflowApi, ApiError } from "@/platform/api";
import { customerServiceApi, type WorkflowTemplate } from "@/domains/customer-service/api/customer-service";
import BlockPalette from "./BlockPalette";
import ComposerNode from "./ComposerNode";
import MerchantFlowEdge from "./MerchantFlowEdge";
import { ComposerPreviewPanel } from "./ComposerPreviewPanel";
import { compileToRuntimeWorkflow } from "@/domains/workflow/composer/utils/compileToRuntimeWorkflow";
import { connectComposerBlocks } from "@/domains/workflow/composer/utils/connectBlocks";
import type {
    ComposerBlockKind,
    ComposerEdge,
    ComposerNode as ComposerNodeType,
} from "@/domains/workflow/composer/types/composer";
import { createStarterComposerFlow } from "@/domains/workflow/composer/utils/starterFlow";
import { createTemplateComposerFlow } from "@/domains/workflow/composer/utils/templateFlow";
import { createComposerFlowFromBackendWorkflow } from "@/domains/workflow/composer/utils/backendTemplateFlow";
import { useComposerSelectionActions } from "@/domains/workflow/composer/hooks/useComposerSelectionActions";
import { useComposerBlockActions } from "@/domains/workflow/composer/hooks/useComposerBlockActions";
import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import ComposerShell from "@/domains/workflow/composer/components/shell/ComposerShell";
import ComposerCanvas from "@/domains/workflow/composer/components/canvas/ComposerCanvas";
import ComposerHeader from "@/domains/workflow/composer/components/header/ComposerHeader";
import ComposerEmptyState from "@/domains/workflow/composer/components/empty/ComposerEmptyState";
import ComposerSidePanel from "@/domains/workflow/composer/components/side-panel/ComposerSidePanel";

const nodeTypes: NodeTypes = {
    composer: ComposerNode,
};

const edgeTypes = {
    merchant: MerchantFlowEdge,
};



export default function WorkflowComposer() {
    const searchParams = useSearchParams();
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
    const templateSlug = searchParams.get("template");
    const templateId = searchParams.get("templateId");
    const [loadedTemplateId, setLoadedTemplateId] = useState<string | null>(null);
    const [nodes, setNodes, onNodesChange] = useNodesState<ComposerNodeType>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<ComposerEdge>([]);
    const [runStatus, setRunStatus] = useState("");
    const [runAnswer, setRunAnswer] = useState("");
const [runResult, setRunResult] = useState<any>(null);
    const [workflowRunId, setWorkflowRunId] = useState("");
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
    const [loadedTemplate, setLoadedTemplate] = useState<WorkflowTemplate | null>(null);
    const [saveStatus, setSaveStatus] = useState("");

    const loadBackendTemplateFlow = useCallback(async (id: string) => {
        setRunStatus("Loading backend template...");

        const templates = await customerServiceApi.workflowTemplates();
        const template = templates.find((item) => item.id === id);

        if (!template) {
            setRunStatus("Template not found.");
            return;
        }

        const templateFlow = createComposerFlowFromBackendWorkflow(
            template.workflow_json || {},
        );

        setNodes(templateFlow.nodes);
        setEdges(templateFlow.edges);
        setSelectedNodeId(null);
        setLoadedTemplate(template);
        setSaveStatus("");
        setRunStatus(`Loaded backend template: ${template.name}`);
        setRunAnswer("");
        setRunResult(null);
        setWorkflowRunId("");
    }, [setNodes, setEdges]);


    const loadTemplateFlow = useCallback((template: string) => {
        const templateFlow = createTemplateComposerFlow(template);

        setNodes(templateFlow.nodes);
        setEdges(templateFlow.edges);
        setSelectedNodeId(null);
        setRunStatus("");
        setRunAnswer("");
        setRunResult(null);
        setWorkflowRunId("");
    }, [setNodes, setEdges]);

    useEffect(() => {
        function onDeleteMerchantEdge(event: Event) {
            const customEvent = event as CustomEvent<{ edgeId?: string }>;
            const edgeId = customEvent.detail?.edgeId;

            if (!edgeId) return;

            setEdges((current) => current.filter((edge) => edge.id !== edgeId));
            setSelectedEdgeId(null);
        }

        window.addEventListener("tajeran:delete-merchant-edge", onDeleteMerchantEdge);

        return () => {
            window.removeEventListener("tajeran:delete-merchant-edge", onDeleteMerchantEdge);
        };
    }, [setEdges]);

    useEffect(() => {
        if (templateId) {
            if (loadedTemplateId === templateId) return;

            loadBackendTemplateFlow(templateId).catch((error) => {
                setRunStatus(`Template load failed: ${String(error?.message ?? error)}`);
            });
            setLoadedTemplateId(templateId);
            return;
        }

        if (!templateSlug || templateSlug === "blank") return;
        if (loadedTemplateId === templateSlug) return;

        loadTemplateFlow(templateSlug);
        setLoadedTemplateId(templateSlug);
    }, [templateId, templateSlug, loadedTemplateId, loadBackendTemplateFlow, loadTemplateFlow]);

    const addStarterFlow = useCallback(() => {
        const starterFlow = createStarterComposerFlow();

        setNodes(starterFlow.nodes);
        setEdges(starterFlow.edges);
        setSelectedNodeId(null);
    }, [setNodes, setEdges]);

    const nodeStatus = useRunStore((state) => state.nodeStatus);

    const nodesWithRuntimeStatus = useMemo(
        () =>
            nodes.map((node) => ({
                ...node,
                data: {
                    ...node.data,
                    runStatus: nodeStatus[node.id],
                },
            })),
        [nodes, nodeStatus],
    );

    const selectedNode = useMemo(
        () => nodes.find((node) => node.id === selectedNodeId) ?? null,
        [nodes, selectedNodeId]
    );
    const runCompiledWorkflow = useCallback(async () => {
        setRunStatus("Running...");
        setRunAnswer("");
        setRunResult(null);
        setWorkflowRunId("");

        try {
            const compiled = compileToRuntimeWorkflow(nodes, edges);

            const triggerNode = compiled.nodes.find(
                (node) => node.data?.nodeType === "trigger.message"
            );

            const message = String(triggerNode?.data?.input ?? "");

            const data: any = await workflowApi.run({
                workflow: compiled,
                message,
                thread_id: crypto.randomUUID(),
                strict: true,
            });

            const nextRunId =
                data?.meta?.workflow_run_id ?? data?.workflow_run_id ?? "";

            console.log("WORKFLOW RESULT", data);
            console.log("ANSWER TYPE", typeof data.answer);
            console.log("ANSWER VALUE", data.answer);

            setWorkflowRunId(String(nextRunId || ""));
            setRunAnswer(String(data.answer ?? ""));
            setRunResult(data.answer ?? null);
            setRunStatus(`OK: ${data?.meta?.status ?? "unknown"}`);
        } catch (e: any) {
            if (e instanceof ApiError) {
                setRunStatus(`Run failed: ${e.status} ${e.body}`);
            } else {
                setRunStatus(`Run error: ${String(e?.message ?? e)}`);
            }
        }
    }, [nodes, edges]);

    
    const {
        deleteSelectedNode,
        duplicateSelectedNode,
        deleteSelectedEdge,
    } = useComposerSelectionActions({
        selectedNodeId,
        selectedEdgeId,
        setSelectedNodeId,
        setSelectedEdgeId,
        setNodes,
        setEdges,
    });


const runtime = useMemo(() => compileToRuntimeWorkflow(nodes, edges), [nodes, edges]);

    const displayEdges = useMemo(
        () =>
            edges.map((edge) => {
                const sourceNode = nodes.find((node) => node.id === edge.source);
                const targetNode = nodes.find((node) => node.id === edge.target);

                return {
                    ...edge,
                    type: "merchant",
                    animated: true,
                    data: {
                        ...edge.data,
                        sourceKind: sourceNode?.data.blockKind,
                        targetKind: targetNode?.data.blockKind,
                    },
                };
            }),
        [edges, nodes]
    );

    const saveDraft = useCallback(async () => {
        if (!loadedTemplate) {
            setSaveStatus("No backend template loaded.");
            return;
        }

        if (loadedTemplate.scope !== "private") {
            setSaveStatus("Clone this system template first before saving edits.");
            return;
        }

        if (loadedTemplate.status !== "draft") {
            setSaveStatus("Only draft templates can be edited. Unpublish it first.");
            return;
        }

        try {
            setSaveStatus("Saving draft...");

            const updated = await customerServiceApi.updateWorkflowTemplate(loadedTemplate.id, {
                workflow_json: runtime,
            });

            setLoadedTemplate(updated);
            setSaveStatus(`Saved draft: ${updated.name}`);
        } catch (error: any) {
            setSaveStatus(`Save failed: ${String(error?.message ?? error)}`);
        }
    }, [loadedTemplate, runtime]);


    const {
        addBlock,
        addUnderstandRequest,
        addSummarizeConversation,
        addReviewRefund,
        addAnalyzeSentiment,
        addCustomAgent,
        addOrderSupportAgent,
        addShopifyOrderCheck,
        addTrackingCheck,
        addRefundOrder,
        addCancelOrder,
        addSearchDocuments,
        addSearchWeb,
        addTagConversation,
        addAssignAgent,
    } = useComposerBlockActions({
        setNodes,
    });

    const onConnect = useCallback(
        (connection: Connection) => {
            setEdges((currentEdges) => connectComposerBlocks(connection, nodes, currentEdges));
        },
        [nodes]
    );

    const autoLayout = useCallback(() => {
        const graph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

        graph.setGraph({
            rankdir: "LR",
            nodesep: 45,
            ranksep: 80,
        });

        nodes.forEach((node) => {
            graph.setNode(node.id, {
                width: 176,
                height: 130,
            });
        });

        edges.forEach((edge) => {
            graph.setEdge(edge.source, edge.target);
        });

        dagre.layout(graph);

        setNodes((current) =>
            current.map((node) => {
                const position = graph.node(node.id);

                if (!position) return node;

                return {
                    ...node,
                    position: {
                        x: position.x - 88,
                        y: position.y - 65,
                    },
                };
            })
        );

        window.setTimeout(() => {
            reactFlowInstance?.fitView({ padding: 0.25, duration: 500 });
        }, 50);
    }, [nodes, edges, setNodes, reactFlowInstance]);


    const updateNodeConfig = useCallback((nodeId: string, patch: Record<string, any>) => {
        setNodes((current) =>
            current.map((node) => {
                if (node.id !== nodeId) return node;

                return {
                    ...node,
                    data: {
                        ...node.data,
                        config: {
                            ...node.data.config,
                            ...patch,
                        },
                    },
                };
            })
        );
    }, []);

    const updateNodeLabel = useCallback((nodeId: string, label: string) => {
        setNodes((current) =>
            current.map((node) =>
                node.id === nodeId ? { ...node, data: { ...node.data, label } } : node
            )
        );
    }, []);

    const palette = (
        <BlockPalette
            addBlock={addBlock}
            addUnderstandRequest={addUnderstandRequest}
            addSummarizeConversation={addSummarizeConversation}
            addReviewRefund={addReviewRefund}
            addAnalyzeSentiment={addAnalyzeSentiment}
            addCustomAgent={addCustomAgent}
            addOrderSupportAgent={addOrderSupportAgent}
            addShopifyOrderCheck={addShopifyOrderCheck}
            addTrackingCheck={addTrackingCheck}
            addRefundOrder={addRefundOrder}
            addCancelOrder={addCancelOrder}
            addTagConversation={addTagConversation}
            addAssignAgent={addAssignAgent}
            addSearchDocuments={addSearchDocuments}
            addSearchWeb={addSearchWeb}
        />
    );

    const header = (
        <ComposerHeader
            nodesCount={nodes.length}
            edgesCount={edges.length}
            loadedTemplate={loadedTemplate}
            templateSlug={templateSlug}
            hasSelectedNode={Boolean(selectedNodeId)}
            hasSelectedEdge={Boolean(selectedEdgeId)}
            addStarterFlow={addStarterFlow}
            saveDraft={saveDraft}
            duplicateSelectedNode={duplicateSelectedNode}
            deleteSelectedNode={deleteSelectedNode}
            deleteSelectedEdge={deleteSelectedEdge}
            autoLayout={autoLayout}
            fitView={() => reactFlowInstance?.fitView({ padding: 0.25, duration: 500 })}
            runCompiledWorkflow={runCompiledWorkflow}
            saveStatus={saveStatus}
            runStatus={runStatus}
        />
    );

    const emptyState = (
        <ComposerEmptyState
            loadTemplateFlow={loadTemplateFlow}
            addStarterFlow={addStarterFlow}
        />
    );

    const canvas = (
        <ComposerCanvas
            nodes={nodesWithRuntimeStatus}
            edges={displayEdges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onConnect={onConnect}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onInit={setReactFlowInstance}
            onSelectionChange={({ nodes, edges }) => {
                setSelectedNodeId(nodes[0]?.id ?? null);
                setSelectedEdgeId(edges[0]?.id ?? null);
            }}
            onEdgesDelete={(deletedEdges) => {
                const ids = new Set(deletedEdges.map((edge) => edge.id));

                setEdges((current) =>
                    current.filter((edge) => !ids.has(edge.id))
                );
            }}
            emptyState={emptyState}
        />
    );

    const sidePanel = (
        <ComposerSidePanel
            selectedNode={selectedNode}
            updateNodeLabel={updateNodeLabel}
            updateNodeConfig={updateNodeConfig}
            loadedTemplate={loadedTemplate}
            nodes={nodes}
            edges={edges}
            runStatus={runStatus}
            workflowRunId={workflowRunId}
            runAnswer={runAnswer}
            runResult={runResult}
            runtime={runtime}
            addMissionStart={() => addBlock("customer_message_trigger")}
            addUnderstandingAgent={addUnderstandRequest}
            addHumanApproval={() => addBlock("human_approval")}
            addFinalOutput={() => addBlock("send_response")}
            buildRefundMission={() => loadTemplateFlow("refund")}
            buildOrderStatusMission={() => loadTemplateFlow("order-status")}
            buildEscalationMission={() => loadTemplateFlow("escalation-router")}
        />
    );

    return (
        <ComposerShell
            palette={palette}
            header={header}
            canvas={canvas}
            sidePanel={sidePanel}
        />
    );
}
