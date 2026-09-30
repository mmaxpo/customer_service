"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LockKeyhole, Workflow } from "lucide-react";
import { ApiError, authApi } from "@/platform/api";

export default function DevConsolePage() {
    const router = useRouter();

    const [email, setEmail] = useState("mehdi@mmaxpo.com");
    const [password, setPassword] = useState("");
    const [status, setStatus] = useState("");

    async function login(e: React.FormEvent) {
        e.preventDefault();
        setStatus("Checking admin access...");

        try {
            await authApi.login({ email, password });
            setStatus("Access granted.");
            window.location.href = "/workflow-builder";
        } catch (err: any) {
            if (err instanceof ApiError) {
                setStatus(`Login failed: ${err.status} ${err.body}`);
            } else {
                setStatus(`Login error: ${String(err?.message ?? err)}`);
            }
        }
    }

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
            <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur">
                <Link href="/" className="mb-8 flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-slate-950">
                        <Workflow size={20} />
                    </div>
                    <div>
                        <div className="font-bold">Tajeran.ai Admin</div>
                        <div className="text-xs text-slate-400">Internal workflow console</div>
                    </div>
                </Link>

                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10">
                    <LockKeyhole size={22} />
                </div>

                <h1 className="mt-5 text-2xl font-bold tracking-tight">Admin access</h1>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                    Login to access the internal workflow builder and runtime tools.
                </p>

                <form onSubmit={login} className="mt-6 space-y-4">
                    <div>
                        <label className="text-sm font-medium text-slate-300">Email</label>
                        <input
                            className="mt-2 w-full rounded-xl border border-white/10 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            type="email"
                        />
                    </div>

                    <div>
                        <label className="text-sm font-medium text-slate-300">Password</label>
                        <input
                            className="mt-2 w-full rounded-xl border border-white/10 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            type="password"
                        />
                    </div>

                    <button
                        type="submit"
                        className="w-full rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-slate-100"
                    >
                        Continue to Workflow Builder
                    </button>
                </form>

                {status && <div className="mt-4 text-sm text-slate-300">{status}</div>}

                <div className="mt-6 text-xs text-slate-500">
                    This page is for internal development/admin access.
                </div>
            </div>
        </main>
    );
}