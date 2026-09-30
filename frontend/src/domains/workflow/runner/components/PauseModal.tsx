"use client";

export default function PauseModal({
                                       open,
                                       title,
                                       description,
                                       onResume,
                                       onClose,
                                   }: {
    open: boolean;
    title?: string;
    description?: string;
    onResume: () => void;
    onClose: () => void;
}) {
    if (!open) return null;

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 50,
                padding: 16,
            }}
        >
            <div style={{ width: 520, maxWidth: "100%", background: "#fff", borderRadius: 14, border: "1px solid #eee" }}>
                <div style={{ padding: 14, borderBottom: "1px solid #eee" }}>
                    <b>{title ?? "Action required"}</b>
                    <div style={{ marginTop: 6, fontSize: 13, color: "#555", lineHeight: 1.45 }}>
                        {description ?? "This workflow is paused and needs your input to continue."}
                    </div>
                </div>

                <div style={{ padding: 14, display: "flex", justifyContent: "flex-end", gap: 10 }}>
                    <button onClick={onClose} style={{ padding: "8px 12px" }}>
                        Close
                    </button>
                    <button onClick={onResume} style={{ padding: "8px 12px" }}>
                        Resume
                    </button>
                </div>
            </div>
        </div>
    );
}