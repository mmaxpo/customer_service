"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { authApi } from "@/platform/api";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  useEffect(() => setToken(new URLSearchParams(window.location.search).get("token") ?? ""), []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try { await authApi.confirmPasswordReset(token, password); setStatus("Password updated. You can log in now."); }
    catch { setStatus("This reset link is invalid or expired."); }
  }
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6"><section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm"><p className="text-sm font-semibold text-slate-500">Tajeran.ai</p><h1 className="mt-3 text-2xl font-bold tracking-tight">Choose a new password</h1><form onSubmit={submit} className="mt-6 space-y-4"><label className="block text-sm font-medium">New password<input className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5" type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} /></label><button className="w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white">Update password</button></form>{status && <p className="mt-4 text-sm text-slate-700">{status}</p>}<Link href="/login" className="mt-6 block text-center text-sm font-semibold">Back to login</Link></section></main>;
}
