type Props = {
    showImport: boolean;
    importText: string;
    setImportText: (value: string) => void;
    importWorkflow: () => void;
    setShowImport: (value: boolean) => void;
};

export default function ImportWorkflowModal({
                                                showImport,
                                                importText,
                                                setImportText,
                                                importWorkflow,
                                                setShowImport,
                                            }: Props) {
    if (!showImport) return null;

    return (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
            <div style={{ background: "white", padding: 20, borderRadius: 12, width: 600, maxWidth: "95%" }}>
                <h3>Import Workflow JSON</h3>

                <textarea
                    value={importText}
                    onChange={(e) => setImportText(e.target.value)}
                    rows={12}
                    style={{ width: "100%", fontFamily: "monospace", padding: 10 }}
                />

                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                    <button onClick={importWorkflow}>Load</button>
                    <button onClick={() => setShowImport(false)}>Cancel</button>
                </div>
            </div>
        </div>
    );
}