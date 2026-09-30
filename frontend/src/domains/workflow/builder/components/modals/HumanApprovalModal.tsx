type PendingApproval = {
    workflowRunId: string;
    question: string;
    interrupt: any;
} | null;

type Props = {
    pendingApproval: PendingApproval;
    resumeApproval: (approved: boolean) => void;
};

export default function HumanApprovalModal({
                                               pendingApproval,
                                               resumeApproval,
                                           }: Props) {
    if (!pendingApproval) return null;

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.45)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 2000,
            }}
        >
            <div
                style={{
                    background: "white",
                    width: 420,
                    maxWidth: "95%",
                    borderRadius: 14,
                    padding: 20,
                    boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
                }}
            >
                <div style={{ fontWeight: 800, fontSize: 18, marginBottom: 8 }}>
                    Human approval required
                </div>

                <div style={{ color: "#555", marginBottom: 16 }}>
                    {pendingApproval.question}
                </div>

                <div
                    style={{
                        fontSize: 12,
                        color: "#777",
                        background: "#f8fafc",
                        border: "1px solid #e5e7eb",
                        borderRadius: 10,
                        padding: 10,
                        marginBottom: 16,
                        wordBreak: "break-word",
                    }}
                >
                    Workflow Run ID: {pendingApproval.workflowRunId}
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                    <button
                        onClick={() => resumeApproval(false)}
                        style={{
                            padding: "8px 12px",
                            borderRadius: 10,
                            border: "1px solid #ddd",
                            background: "white",
                            cursor: "pointer",
                        }}
                    >
                        Reject
                    </button>

                    <button
                        onClick={() => resumeApproval(true)}
                        style={{
                            padding: "8px 12px",
                            borderRadius: 10,
                            border: "1px solid #16a34a",
                            background: "#16a34a",
                            color: "white",
                            cursor: "pointer",
                        }}
                    >
                        Approve
                    </button>
                </div>
            </div>
        </div>
    );
}