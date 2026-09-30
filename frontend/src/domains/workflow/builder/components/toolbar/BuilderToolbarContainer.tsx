"use client";

import WorkflowToolbar from "./WorkflowToolbar";

type SavedWorkflow = {
  id: string;
  name: string;
};

type Props = {
  selectedNodeId: string | null;
  selectedEdgeIds: string[];
  deleteSelected: () => void;

  runWorkflow: () => void;
  runSavedWorkflow: () => void;
  runStatus: string;

  saveWorkflow: () => void;
  refreshSaved: () => void;
  renameWorkflow: (id: string, name: string) => void;
  deleteWorkflow: (id: string) => void;
  savedStatus: string;

  saveName: string;
  setSaveName: (value: string) => void;

  selectedWorkflowId: string;
  setSelectedWorkflowId: (value: string) => void;
  saved: SavedWorkflow[];
  loadSaved: () => void;

  setShowImport: (value: boolean) => void;
  exportWorkflow: () => void;
  showRuntimePreview: () => void;
};

export default function BuilderToolbarContainer(props: Props) {
  return <WorkflowToolbar {...props} />;
}
