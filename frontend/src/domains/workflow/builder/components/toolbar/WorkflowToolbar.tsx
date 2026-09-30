import { Download, Play, RefreshCcw, Save, Trash2, Upload } from "lucide-react";

type Props = {

    selectedNodeId: string | null;

    selectedEdgeIds: string[];

    deleteSelected: () => void;

    runWorkflow: () => void;

    runSavedWorkflow: () => void;

    saveWorkflow: () => void;

    refreshSaved: () => void;

    renameWorkflow: (id: string, name: string) => void;

    deleteWorkflow: (id: string) => void;

    saveName: string;

    setSaveName: (v: string) => void;

    selectedWorkflowId: string;

    setSelectedWorkflowId: (v: string) => void;

    saved: { id: string; name: string }[];

    loadSaved: () => void;

    setShowImport: (v: boolean) => void;

    exportWorkflow: () => void;

    runStatus: string;

    savedStatus: string;

    showRuntimePreview: () => void;


};

function buttonClass(kind: "primary" | "danger" | "plain" = "plain") {
    if (kind === "primary") {
        return "inline-flex items-center gap-2 rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800";
    }

    if (kind === "danger") {
        return "inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40";
    }

    return "inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40";
}

export default function WorkflowToolbar(props: Props) {

    return (
        <div className="flex max-w-[calc(100vw-760px)] flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur">
            <button
                className={buttonClass("danger")}
                onClick={props.deleteSelected}
                disabled={!props.selectedNodeId && props.selectedEdgeIds.length === 0}
            >
                <Trash2 size={14} />
                Delete
            </button>

            <button className={buttonClass("primary")} onClick={props.runWorkflow}>
                <Play size={14} />
                Run
            </button>

            <input
                value={props.saveName}
                onChange={(e) => props.setSaveName(e.target.value)}
                placeholder="Workflow name"
                className="h-9 min-w-44 rounded-xl border border-slate-200 px-3 text-xs outline-none focus:border-slate-400"
            />
            <button onClick={props.showRuntimePreview}>
                Preview Runtime Payload
            </button>

            <button className={buttonClass()} onClick={props.saveWorkflow}>
                <Save size={14} />
                Save
            </button>

            <button className={buttonClass()} onClick={props.refreshSaved}>
                <RefreshCcw size={14} />
                Refresh
            </button>
            <button
                className={buttonClass()}
                disabled={!props.selectedWorkflowId}
                onClick={() =>
                    props.renameWorkflow(props.selectedWorkflowId, props.saveName)
                }
            >
                Rename
            </button>

            <button
                className={buttonClass("danger")}
                disabled={!props.selectedWorkflowId}
                onClick={() => props.deleteWorkflow(props.selectedWorkflowId)}
            >
                <Trash2 size={14} />
                Delete Saved
            </button>

            <select
                value={props.selectedWorkflowId}
                onChange={(e) => props.setSelectedWorkflowId(e.target.value)}
                className="h-9 max-w-48 rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none"
            >
                <option value="">Select saved…</option>
                {props.saved.map((w) => (
                    <option key={w.id} value={w.id}>
                        {w.name}
                    </option>
                ))}
            </select>

            <button
                className={buttonClass()}
                onClick={props.loadSaved}
                disabled={!props.selectedWorkflowId}
            >
                Load
            </button>

            <button
                className={buttonClass("primary")}
                onClick={props.runSavedWorkflow}
                disabled={!props.selectedWorkflowId}
            >
                <Play size={14} />
                Run Saved
            </button>

            <button className={buttonClass()} onClick={() => props.setShowImport(true)}>
                <Upload size={14} />
                Import
            </button>

            <button className={buttonClass()} onClick={props.exportWorkflow}>
                <Download size={14} />
                Export
            </button>

            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-500">
                {props.runStatus || "Idle"}
                {props.savedStatus ? ` • ${props.savedStatus}` : ""}
            </span>
        </div>
    );
}