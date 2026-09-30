"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, authApi } from "@/platform/api";

function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return "Something went wrong. Please try again.";
  try {
    const body = JSON.parse(error.body);
    const detail = body?.detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).join(" ");
    if (typeof detail === "string") return detail;
  } catch {
    // Keep a useful fallback for non-JSON proxy errors.
  }
  return `Could not create your account (${error.status}).`;
}

export default function SignupPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accepted) {
      setStatus("Please accept the Terms and Privacy Policy to continue.");
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      await authApi.signup({
        full_name: fullName || undefined,
        email,
        password,
        terms_accepted: true,
        terms_version: "v1",
        privacy_accepted: true,
        privacy_version: "v1",
      });
      window.location.href = `/login?created=1&email=${encodeURIComponent(email)}`;
    } catch (error) {
      setStatus(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-10">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold text-slate-500">Tajeran.ai · Support OS</p>
        <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-950">Create your workspace</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">Connect Shopify, bring support into one inbox, and start with a clear setup checklist.</p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-medium text-slate-700">Your name (optional)
            <input className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 outline-none focus:border-slate-500" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
          </label>
          <label className="block text-sm font-medium text-slate-700">Work email
            <input className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 outline-none focus:border-slate-500" value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="email" />
          </label>
          <label className="block text-sm font-medium text-slate-700">Password
            <input className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 outline-none focus:border-slate-500" value={password} onChange={(e) => setPassword(e.target.value)} type="password" required minLength={8} autoComplete="new-password" />
          </label>
          <label className="flex items-start gap-3 text-sm leading-5 text-slate-600">
            <input className="mt-1" type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
            <span>I agree to the Terms and Privacy Policy.</span>
          </label>
          <button disabled={loading} className="w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60">
            {loading ? "Creating workspace…" : "Create workspace"}
          </button>
        </form>
        {status && <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{status}</p>}
        <p className="mt-6 text-center text-sm text-slate-500">Already have an account? <Link href="/login" className="font-semibold text-slate-950">Log in</Link></p>
      </section>
    </main>
  );
}
