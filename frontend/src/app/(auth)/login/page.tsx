"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Eye, EyeOff } from "lucide-react";
import { authButton, authInput, authLabel, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
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

  const failed = Boolean(status) && !loading && !status.startsWith("Account created");

  return (
    <AuthShell
      title="Log in to your workspace"
      subtitle="Pick up where your agents left off."
      footer={
        <>
          <p>Forgot your password? <Link href="/forgot-password" className="font-medium text-primary hover:underline">Reset it</Link></p>
          <p>New to Tajeran? <Link href="/signup" className="font-medium text-primary hover:underline">Create a workspace</Link></p>
          <p className="pt-2 text-[12.5px]">By continuing, you agree to our Terms of Service and Privacy Policy.</p>
        </>
      }
    >
      <form onSubmit={login} className="mt-7 space-y-4">
        <label className={authLabel}>Work email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required autoComplete="email" placeholder="jane@mystore.com" className={authInput} />
        </label>
        <label className={authLabel}>Password
          <div className="relative">
            <input value={password} onChange={(event) => setPassword(event.target.value)} type={showPassword ? "text" : "password"} required autoComplete="current-password" className={`${authInput} pr-11`} />
            <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} className="absolute right-1.5 top-[11px] flex h-8 w-8 items-center justify-center rounded-control text-text-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
              {showPassword ? <EyeOff size={17} aria-hidden /> : <Eye size={17} aria-hidden />}
            </button>
          </div>
        </label>
        <button disabled={loading} className={authButton}>{loading ? "Logging in…" : "Log in"}</button>
      </form>
      <div className="my-5 flex items-center gap-3 text-[12.5px] text-text-secondary"><span className="h-px flex-1 bg-border" />or<span className="h-px flex-1 bg-border" /></div>
      <button type="button" disabled title="Google sign-in will be enabled after the backend OAuth setup" className="h-11 w-full rounded-control border border-border bg-surface text-[14.5px] font-medium text-foreground disabled:cursor-not-allowed">
        <svg viewBox="0 0 48 48" width="20" height="20" aria-hidden className="mr-2.5 inline-block align-[-4px]">
          <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
          <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
          <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
          <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
        </svg>Continue with Google
      </button>
      <AuthStatus message={status || null} tone={failed ? "error" : "info"} />
    </AuthShell>
  );
}
