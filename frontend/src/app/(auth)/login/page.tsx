"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bot, Eye, EyeOff } from "lucide-react";
import { ApiError, authApi } from "@/platform/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("email")) setEmail(params.get("email") ?? "");
    if (params.get("created") === "1") setStatus("Account created. Check your email, then log in.");
  }, []);

  async function login(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setStatus("Logging in…");
    try {
      await authApi.login({ email, password });
      window.location.href = "/app/dashboard";
    } catch (error) {
      if (error instanceof ApiError) {
        try { const body = JSON.parse(error.body); setStatus(typeof body?.detail === "string" ? body.detail : "Please check your email and password."); }
        catch { setStatus("Please check your email and password."); }
      } else setStatus("Login failed. Please try again.");
    } finally { setLoading(false); }
  }

  return <main className="flex min-h-screen items-center justify-center bg-[#fff0e4] px-4 py-8">
    <section className="w-full max-w-[410px] rounded-md border border-border bg-surface-elevated px-8 py-7 shadow-elevated">
      <div className="text-center"><div className="mx-auto flex h-9 w-9 items-center justify-center rounded border border-foreground text-foreground"><Bot size={20} /></div><p className="mt-2 text-xl font-medium tracking-tight text-foreground">Tajeran.ai</p></div>
      <div className="mt-6 flex items-center gap-2 text-xs text-text-secondary"><span className="rounded-full bg-[#ffe7dc] px-2.5 py-1 text-foreground">1/2</span><span className="font-medium text-foreground">Log in to your workspace</span></div><div className="mt-2 h-1 rounded-full bg-[#ff8d79]" />
      <form onSubmit={login} className="mt-5 space-y-4">
        <label className="block text-xs font-medium text-foreground">Your work email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required autoComplete="email" placeholder="jane@mystore.com" className="mt-1.5 h-10 w-full rounded border border-foreground/60 bg-surface px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /></label>
        <label className="block text-xs font-medium text-foreground">Your password<div className="relative mt-1.5"><input value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} required autoComplete="current-password" className="h-10 w-full rounded border border-foreground/60 bg-surface px-3 pr-10 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} className="absolute right-2 top-2 text-text-secondary">{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
        <button disabled={loading} className="h-10 w-full rounded bg-[#ff8d79] px-4 text-sm font-semibold text-foreground hover:bg-[#ff7b65] disabled:opacity-60">{loading ? "Logging in…" : "Log in"}</button>
      </form>
      <div className="my-5 flex items-center gap-3 text-xs text-text-secondary"><span className="h-px flex-1 bg-border" />OR<span className="h-px flex-1 bg-border" /></div>
      <button type="button" disabled title="Google sign-in will be enabled after the backend OAuth setup" className="h-10 w-full rounded border border-foreground bg-surface text-sm font-medium text-foreground disabled:cursor-not-allowed disabled:opacity-70"><span className="mr-2 font-bold text-[#4285f4]">G</span>Continue with Google</button>
      {status ? <p role="status" className="mt-4 rounded bg-muted px-3 py-2 text-sm text-text-secondary">{status}</p> : null}
      <p className="mt-5 text-center text-xs text-text-secondary">Forgot your password? <Link href="/forgot-password" className="font-medium text-primary underline">Reset it</Link></p>
      <p className="mt-3 text-center text-xs text-text-secondary">Don&apos;t have a Tajeran account? <Link href="/signup" className="font-medium text-primary underline">Create one</Link></p>
      <p className="mt-5 text-center text-[11px] text-text-secondary">By continuing, you agree to our Terms of Service and Privacy Policy.</p>
    </section>
  </main>;
}
