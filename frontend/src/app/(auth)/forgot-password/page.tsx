"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, authApi } from "@/platform/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      await authApi.requestPasswordReset(email);
      setStatus("If that account exists, reset instructions are on the way.");
    } catch (error) {
      setStatus(error instanceof ApiError ? "We could not send the reset email. Try again shortly." : "Something went wrong. Try again shortly.");
    } finally { setLoading(false); }
  }
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6"><section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm"><p className="text-sm font-semibold text-slate-500">Tajeran.ai</p><h1 className="mt-3 text-2xl font-bold tracking-tight">Reset your password</h1><p className="mt-2 text-sm leading-6 text-slate-600">Enter your work email and we’ll send a secure reset link.</p><form onSubmit={submit} className="mt-6 space-y-4"><label className="block text-sm font-medium text-slate-700">Work email<input className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><button disabled={loading} className="w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{loading ? "Sending…" : "Send reset link"}</button></form>{status && <p className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-700">{status}</p>}<Link href="/login" className="mt-6 block text-center text-sm font-semibold">Back to login</Link></section></main>;
}
