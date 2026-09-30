"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, authApi, knowledgeApi, workflowApi } from "@/platform/api";

type KBResult = {
    id: number;
    doc_id: string;
    chunk_index?: number | null;
    content: string;
    score_hybrid?: number;
};

type KBDocRow = {
    doc_id: string;
    updated_at?: string;
    chunks?: number;
};

type WorkflowRunRow = {
    workflow_run_id: string;
    status: string;
    thread_id?: string | null;
    created_at?: string;
    updated_at?: string;
};




export default function KnowledgeConsole() {
    const [email, setEmail] = useState("mehdi@mmaxpo.com");
    const [password, setPassword] = useState("");
    const [loginStatus, setLoginStatus] = useState("");

    const [ingestDocId, setIngestDocId] = useState("refund-policy");
    const [ingestText, setIngestText] = useState("Refund Policy: returns accepted within 5 days.");
    const [ingestStatus, setIngestStatus] = useState("");

    const [docs, setDocs] = useState<KBDocRow[]>([]);
    const [docsStatus, setDocsStatus] = useState("");

    const [query, setQuery] = useState("refund policy");
    const [kbResults, setKbResults] = useState<KBResult[]>([]);
    const [kbStatus, setKbStatus] = useState("");

    const [askMsg, setAskMsg] = useState("what is our refund policy?");
    const [askReply, setAskReply] = useState("");
    const [askStatus, setAskStatus] = useState("");

    const [askMcpReply, setAskMcpReply] = useState("");
    const [askMcpStatus, setAskMcpStatus] = useState("");

    const [runs, setRuns] = useState<WorkflowRunRow[]>([]);
    const [runsStatus, setRunsStatus] = useState("");

    async function loadRuns() {
        setRunsStatus("Loading runs...");

        try {
            const data: any = await workflowApi.listRuns("limit=10&offset=0");
            setRuns(data.items || []);
            setRunsStatus(`OK (${(data.items || []).length} runs)`);
        } catch (e: any) {
            if (e instanceof ApiError) setRunsStatus(`Runs failed: ${e.status} ${e.body}`);
            else setRunsStatus(`Runs error: ${String(e?.message ?? e)}`);
        }
    }

    async function login() {
        setLoginStatus("Logging in...");
        try {
            await authApi.login({ email, password });
            setLoginStatus("Login ok (cookie stored).");
        } catch (e: any) {
            if (e instanceof ApiError) setLoginStatus(`Login failed: ${e.status} ${e.body}`);
            else setLoginStatus(`Login error: ${String(e?.message ?? e)}`);
        }
    }

    async function loadDocs() {
        setDocsStatus("Loading docs...");
        let data: any;
        try {
            data = await knowledgeApi.docs();
        } catch (e: any) {
            if (e instanceof ApiError) setDocsStatus(`Docs failed: ${e.status} ${e.body}`);
            else setDocsStatus(`Docs error: ${String(e?.message ?? e)}`);
            return;
        }
        setDocs(data.docs || []);
        setDocsStatus(`OK (${(data.docs || []).length} docs)`);
    }

    async function ingest() {
        setIngestStatus("Ingesting...");
        const texts = ingestText
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean);

        let data: any;
        try {
            data = await knowledgeApi.ingest({ doc_id: ingestDocId || undefined, texts });
        } catch (e: any) {
            if (e instanceof ApiError) setIngestStatus(`Ingest failed: ${e.status} ${e.body}`);
            else setIngestStatus(`Ingest error: ${String(e?.message ?? e)}`);
            return;
        }
        setIngestStatus(`OK (doc_id=${data.doc_id}, chunks=${data.chunks})`);
        await loadDocs();
    }

    async function deleteDoc(doc_id: string) {
        if (!confirm(`Delete doc_id="${doc_id}" ?`)) return;
        try {
            await knowledgeApi.deleteDoc(doc_id);
        } catch (e: any) {
            if (e instanceof ApiError) alert(`Delete failed: ${e.status} ${e.body}`);
            else alert(`Delete error: ${String(e?.message ?? e)}`);
            return;
        }
        await loadDocs();
    }

    async function kbSearch() {
        setKbStatus("Searching...");
        setKbResults([]);

        let data: any;
        try {
            data = await knowledgeApi.search({ query, top_k: 5 });
        } catch (e: any) {
            if (e instanceof ApiError) setKbStatus(`Search failed: ${e.status} ${e.body}`);
            else setKbStatus(`Search error: ${String(e?.message ?? e)}`);
            return;
        }
        setKbResults(data.results || []);
        setKbStatus(`OK (${(data.results || []).length} results)`);
    }

    async function askAgent() {
        setAskStatus("Asking agent...");
        setAskReply("");

        let data: any;
        try {
            data = await knowledgeApi.askAgent({ message: askMsg }, false);
        } catch (e: any) {
            if (e instanceof ApiError) setAskStatus(`Ask failed: ${e.status} ${e.body}`);
            else setAskStatus(`Ask error: ${String(e?.message ?? e)}`);
            return;
        }
        const reply =
            data.reply ??
            data.answer ??
            data?.state?.vars?.answer ??
            data?.state?.last ??
            "";
        setAskReply(String(reply));
    }

    async function askAgentMcp() {
        setAskMcpStatus("Asking MCP agent...");
        setAskMcpReply("");

        let data: any;
        try {
            data = await knowledgeApi.askAgentMcp({ message: askMsg }, false);
        } catch (e: any) {
            if (e instanceof ApiError) setAskMcpStatus(`Ask MCP failed: ${e.status} ${e.body}`);
            else setAskMcpStatus(`Ask MCP error: ${String(e?.message ?? e)}`);
            return;
        }
        const reply =
            data.reply ??
            data.answer ??
            data?.state?.vars?.answer ??
            data?.state?.last ??
            "";
        setAskMcpReply(String(reply));
    }

    useEffect(() => {
        loadDocs().catch(() => {});
        loadRuns().catch(() => {});
    }, []);

    return (
        <div style={{ maxWidth: 900 }}>
            <h2 style={{ marginTop: 0 }}>Dev Console</h2>

            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                <Link href="/dev-console" style={{ padding: "8px 12px", border: "1px solid #eee", borderRadius: 8 }}>
                    Dev Console
                </Link>
                <Link href="/workflow-builder" style={{ padding: "8px 12px", border: "1px solid #eee", borderRadius: 8 }}>
                    Workflow Builder
                </Link>
                <Link href="/runs" style={{ padding: "8px 12px", border: "1px solid #eee", borderRadius: 8 }}>
                    Runs
                </Link>
            </div>

            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8, marginBottom: 16 }}>
                <h3>1) Login (cookie auth)</h3>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <input style={{ padding: 8, minWidth: 260 }} value={email} onChange={(e) => setEmail(e.target.value)} />
                    <input style={{ padding: 8, minWidth: 220 }} value={password} type="password" onChange={(e) => setPassword(e.target.value)} />
                    <button style={{ padding: "8px 12px" }} onClick={login}>Login</button>
                    <button style={{ padding: "8px 12px" }} onClick={loadDocs}>Refresh Docs</button>
                </div>
                <div style={{ marginTop: 8, color: "#555" }}>{loginStatus}</div>
            </section>
            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8, marginBottom: 16 }}>
                <h3>2) Latest Workflow Runs</h3>

                <button style={{ padding: "8px 12px" }} onClick={loadRuns}>
                    Refresh Runs
                </button>

                <div style={{ marginTop: 8, color: "#555" }}>{runsStatus}</div>

                <div style={{ marginTop: 12 }}>
                    {runs.map((r) => (
                        <div
                            key={r.workflow_run_id}
                            style={{
                                padding: 10,
                                border: "1px solid #f0f0f0",
                                borderRadius: 8,
                                marginBottom: 10,
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                                <div>
                                    <div>
                                        <b>{r.status}</b>
                                    </div>
                                    <div style={{ fontSize: 12, color: "#666", fontFamily: "monospace" }}>
                                        {r.workflow_run_id}
                                    </div>
                                    <div style={{ fontSize: 12, color: "#666" }}>
                                        updated: {r.updated_at ?? "?"}
                                    </div>
                                </div>

                                <Link
                                    href={`/runs/${r.workflow_run_id}`}
                                    style={{
                                        padding: "8px 12px",
                                        border: "1px solid #ddd",
                                        borderRadius: 8,
                                        height: "fit-content",
                                    }}
                                >
                                    Open
                                </Link>
                            </div>
                        </div>
                    ))}
                </div>
            </section>
            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8, marginBottom: 16 }}>
                <h3>2) KB Ingest</h3>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <input style={{ padding: 8, minWidth: 260 }} value={ingestDocId} onChange={(e) => setIngestDocId(e.target.value)} />
                    <button style={{ padding: "8px 12px" }} onClick={ingest}>Ingest</button>
                </div>
                <textarea
                    style={{ width: "100%", padding: 8, minHeight: 90, marginTop: 8 }}
                    value={ingestText}
                    onChange={(e) => setIngestText(e.target.value)}
                />
                <div style={{ marginTop: 8, color: "#555" }}>{ingestStatus}</div>
            </section>

            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8, marginBottom: 16 }}>
                <h3>3) KB Docs</h3>
                <div style={{ marginTop: 8, color: "#555" }}>{docsStatus}</div>
                <div style={{ marginTop: 12 }}>
                    {docs.map((d) => (
                        <div key={d.doc_id} style={{ padding: 10, border: "1px solid #f0f0f0", borderRadius: 8, marginBottom: 10 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                                <div>
                                    <div><b>{d.doc_id}</b></div>
                                    <div style={{ fontSize: 12, color: "#666" }}>
                                        chunks: {d.chunks ?? "?"} | updated: {d.updated_at ?? "?"}
                                    </div>
                                </div>
                                <button onClick={() => deleteDoc(d.doc_id)} style={{ padding: "8px 12px" }}>Delete</button>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8, marginBottom: 16 }}>
                <h3>4) KB Search</h3>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <input style={{ padding: 8, minWidth: 420 }} value={query} onChange={(e) => setQuery(e.target.value)} />
                    <button style={{ padding: "8px 12px" }} onClick={kbSearch}>Search</button>
                </div>
                <div style={{ marginTop: 8, color: "#555" }}>{kbStatus}</div>
                <div style={{ marginTop: 12 }}>
                    {kbResults.map((r) => (
                        <div key={r.id} style={{ padding: 10, border: "1px solid #f0f0f0", borderRadius: 8, marginBottom: 10 }}>
                            <div style={{ fontSize: 12, color: "#666" }}>
                                doc_id: <b>{r.doc_id}</b> | chunk: {r.chunk_index ?? 0} | hybrid:{" "}
                                {typeof r.score_hybrid === "number" ? r.score_hybrid.toFixed(3) : "n/a"}
                            </div>
                            <div style={{ marginTop: 6 }}>{r.content}</div>
                        </div>
                    ))}
                </div>
            </section>

            <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8 }}>
                <h3>5) Ask Agent (Tool) + Ask Agent (MCP)</h3>
                <textarea style={{ width: "100%", padding: 8, minHeight: 80 }} value={askMsg} onChange={(e) => setAskMsg(e.target.value)} />
                <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                    <button style={{ padding: "8px 12px" }} onClick={askAgent}>Ask (Tool)</button>
                    <button style={{ padding: "8px 12px" }} onClick={askAgentMcp}>Ask (MCP)</button>
                    <div style={{ alignSelf: "center", color: "#555" }}>{askStatus}</div>
                    <div style={{ alignSelf: "center", color: "#555" }}>{askMcpStatus}</div>
                </div>

                {(askReply || askMcpReply) && (
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
                        <div style={{ padding: 12, background: "#fafafa", border: "1px solid #eee", borderRadius: 8 }}>
                            <b>Tool Reply:</b>
                            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{askReply}</div>
                        </div>
                        <div style={{ padding: 12, background: "#fafafa", border: "1px solid #eee", borderRadius: 8 }}>
                            <b>MCP Reply:</b>
                            <div style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{askMcpReply}</div>
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
}