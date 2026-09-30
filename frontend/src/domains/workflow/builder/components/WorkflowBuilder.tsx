"use client";


import React, { useCallback, useMemo, useState } from "react";
import {
    addEdge,
    useEdgesState,
    useNodesState,
    type Connection,
    type Edge,
    type Node,
} from "@xyflow/react";
import { useNodeCatalog } from "@/domains/workflow/builder/hooks/useNodeCatalog";
import TriggerNode from "@/domains/workflow/builder/components/nodes/TriggerNode";
import EditableLabelNode from "@/domains/workflow/builder/components/nodes/EditableLabelNode";
import { useRunStream } from "../../runner/hooks/useRunStream";
import { useSavedWorkflows } from "@/domains/workflow/builder/hooks/useSavedWorkflows";
import GradientEdge from "@/domains/workflow/builder/components/edges/GradientEdge";
import { useWorkflowRunner } from "@/domains/workflow/builder/hooks/useWorkflowRunner";
import { useWorkflowImportExport } from "@/domains/workflow/builder/hooks/useWorkflowImportExport";
import { useWorkflowSelection } from "@/domains/workflow/builder/hooks/useWorkflowSelection";
import { useWorkflowNodes } from "@/domains/workflow/builder/hooks/useWorkflowNodes";
import { useCatalogView } from "@/domains/workflow/builder/hooks/useCatalogView";
import BuilderInspectorContainer from "@/domains/workflow/builder/components/inspector/BuilderInspectorContainer";
import BuilderToolbarContainer from "@/domains/workflow/builder/components/toolbar/BuilderToolbarContainer";
import BuilderPaletteContainer from "@/domains/workflow/builder/components/palette/BuilderPaletteContainer";
import BuilderRunOutputContainer from "@/domains/workflow/builder/components/runtime/BuilderRunOutputContainer";
import ImportWorkflowModal from "@/domains/workflow/builder/components/modals/ImportWorkflowModal";
import { initialNodes, initialEdges } from "@/domains/workflow/builder/constants/initialWorkflow";
import HumanApprovalModal from "@/domains/workflow/builder/components/modals/HumanApprovalModal";
import { useRunStore } from "@/domains/workflow/runner/store/runStore";
import {
    autoConfigureEdge,
    autoConfigureNodesOnConnect,
} from "@/domains/workflow/builder/utils/autoConfigureConnection";
import { useAgentTools } from "@/domains/workflow/builder/hooks/useAgentTools";
import { validateWorkflowConnection } from "@/domains/workflow/builder/utils/connectionRules";
import { getConnectedAgentForTool } from "@/domains/workflow/builder/utils/toolConnections";
import RuntimePayloadModal from "@/domains/workflow/builder/components/modals/RuntimePayloadModal";
import BuilderShell from "@/domains/workflow/builder/components/shell/BuilderShell";
import BuilderCanvas from "@/domains/workflow/builder/components/canvas/BuilderCanvas";
import { buildRuntimePayload } from "@/domains/workflow/builder/utils/runtimePayload";
import { useWorkflowLayout } from "@/domains/workflow/builder/hooks/useWorkflowLayout";
import { useWorkflowToolNodes } from "@/domains/workflow/builder/hooks/useWorkflowToolNodes";


export default function WorkflowBuilder() {
    const nodeTypes = {
        trigger: TriggerNode,
        editable: EditableLabelNode,
    };
    const { catalog, catalogStatus } = useNodeCatalog();
    const { catalogByType, groupedCatalog } = useCatalogView(catalog);
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>(initialNodes);
    const [connectionStatus, setConnectionStatus] = React.useState("");


    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(
        initialEdges.map((edge) => ({
            ...edge,
            type: "gradient",
            animated: true,
            style: { strokeWidth: 2 },
        }))
    );
    const edgeTypes = {
        gradient: GradientEdge,
    };
    const { tools: agentTools, status: agentToolsStatus } = useAgentTools();
    const nodeStatus = useRunStore((s) => s.nodeStatus);
    const {
        saved,
        savedStatus,
        selectedWorkflowId,
        saveName,
        setSelectedWorkflowId,
        setSaveName,
        setSavedStatus,
        refreshSaved,
        loadSaved,
        saveWorkflow,
        renameWorkflow,
        deleteWorkflow,
    } = useSavedWorkflows(nodes, edges, setNodes, setEdges);
    const {
        workflowRunId,
        runStatus,
        runAnswer,
        setRunAnswer,
        runWorkflow,
        runSavedWorkflow,
        pendingApproval,
        resumeApproval,
    } = useWorkflowRunner(nodes, edges, selectedWorkflowId);
    const {
        importText,
        setImportText,
        showImport,
        setShowImport,
        importWorkflow,
        exportWorkflow,
    } = useWorkflowImportExport(nodes, edges, setNodes, setEdges, setSavedStatus);
    const {
        selectedNode,
        selectedNodeId,
        selectedEdgeIds,
        onSelectionChange,
        deleteSelected,
    } = useWorkflowSelection(nodes, setNodes, setEdges);
    const {
        nodesWithHandlers,
        addNode,
        updateSelectedNodeField,
    } = useWorkflowNodes(nodes, setNodes, selectedNodeId, nodeStatus);

    const displayNodes = nodesWithHandlers.map((node) => {
        const data = node.data as any;

        if (data?.nodeType !== "tool.reference") return node;

        const connectedAgent = getConnectedAgentForTool(node.id, nodes, edges);

        return {
            ...node,
            data: {
                ...data,
                connectedAgentName: connectedAgent?.name ?? "",
            },
        };
    });
    const onConnect = useCallback(
        (conn: Connection) => {
            const validation = validateWorkflowConnection(nodes, conn);

            if (!validation.ok) {
                setConnectionStatus(
                    "reason" in validation ? validation.reason : "Invalid connection"
                );
                return;
            }

            setConnectionStatus("");

            setNodes((nds) => autoConfigureNodesOnConnect(nds, conn));

            setEdges((eds) =>
                addEdge(
                    autoConfigureEdge({
                        ...conn,
                        id: `${conn.source}-${conn.target}`,
                        source: conn.source!,
                target: conn.target!,
        } as Edge),
            eds
        )
        );
        },
        [nodes, setNodes, setEdges]
    );

    useRunStream(workflowRunId || null);
    const onLayout = useWorkflowLayout(nodes, edges, setNodes, setEdges);

    const { addToolNode } = useWorkflowToolNodes(setNodes);
    const [showRuntimePreview, setShowRuntimePreview] = useState(false);

    const runtimePreviewPayload = useMemo(
        () => buildRuntimePayload(nodes, edges),
        [nodes, edges]
    );

    const modals = (
        <>
            <ImportWorkflowModal
                showImport={showImport}
                importText={importText}
                setImportText={setImportText}
                importWorkflow={importWorkflow}
                setShowImport={setShowImport}
            />
            <HumanApprovalModal
                pendingApproval={pendingApproval}
                resumeApproval={resumeApproval}
            />
            <RuntimePayloadModal
                open={showRuntimePreview}
                payload={runtimePreviewPayload}
                onClose={() => setShowRuntimePreview(false)}
            />
        </>
    );

    const palette = (
        <BuilderPaletteContainer
            catalogStatus={catalogStatus}
            groupedCatalog={groupedCatalog}
            addNode={addNode}
            agentTools={agentTools}
            addToolNode={addToolNode}
        />
    );

    const toolbar = (
        <BuilderToolbarContainer
            selectedNodeId={selectedNodeId}
            selectedEdgeIds={selectedEdgeIds}
            deleteSelected={deleteSelected}
            runWorkflow={runWorkflow}
            runSavedWorkflow={runSavedWorkflow}
            saveWorkflow={saveWorkflow}
            refreshSaved={refreshSaved}
            saveName={saveName}
            setSaveName={setSaveName}
            selectedWorkflowId={selectedWorkflowId}
            setSelectedWorkflowId={setSelectedWorkflowId}
            saved={saved}
            loadSaved={loadSaved}
            setShowImport={setShowImport}
            exportWorkflow={exportWorkflow}
            runStatus={runStatus}
            savedStatus={savedStatus}
            renameWorkflow={renameWorkflow}
            deleteWorkflow={deleteWorkflow}
            showRuntimePreview={() => setShowRuntimePreview(true)}
        />
    );

    const canvas = (
        <BuilderCanvas
            nodes={displayNodes}
            edges={edges}
            edgeTypes={edgeTypes}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onSelectionChange={onSelectionChange}
            isValidConnection={(conn) => validateWorkflowConnection(nodes, conn).ok}
            connectionStatus={connectionStatus}
        />
    );

    const inspector = (
        <BuilderInspectorContainer
            selectedNode={selectedNode}
            catalogByType={catalogByType}
            updateSelectedNodeField={updateSelectedNodeField}
            agentTools={agentTools}
            agentToolsStatus={agentToolsStatus}
        />
    );

    const runOutput = (
        <BuilderRunOutputContainer
            runAnswer={runAnswer}
            setRunAnswer={setRunAnswer}
            runStatus={runStatus}
        />
    );

    return (
        <BuilderShell
            palette={palette}
            toolbar={toolbar}
            canvas={canvas}
            inspector={inspector}
            runOutput={runOutput}
            modals={modals}
        />
    );

}
