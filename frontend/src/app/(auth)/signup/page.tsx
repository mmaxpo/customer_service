"use client";

import Link from "next/link";
import { PasswordInput } from "@/ui/primitives/password-input";
import { FormEvent, useState } from "react";
import { authButton, authInput, authLabel, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
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
    <AuthShell
      title="Create your workspace"
      subtitle="Connect Shopify, add your help articles, and let the agents take the first conversation."
      footer={<p>Already have an account? <Link href="/login" className="font-medium text-primary hover:underline">Log in</Link></p>}
    >
      <form onSubmit={submit} className="mt-7 space-y-4">
        <label className={authLabel}>Your name (optional)
          <input className={authInput} value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
        </label>
        <label className={authLabel}>Work email
          <input className={authInput} value={email} onChange={(e) => setEmail(e.target.value)} type="email" required autoComplete="email" placeholder="jane@mystore.com" />
        </label>
        <label className={authLabel}>Password
          <PasswordInput className={authInput} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
          <span className="mt-1.5 block text-[12.5px] font-normal text-text-secondary">At least 8 characters, with a letter and a number.</span>
        </label>
        <label className="flex items-start gap-2.5 text-[13.5px] leading-5 text-text-secondary">
          <input className="mt-0.5 h-4 w-4 accent-primary" type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
          <span>I agree to the Terms and Privacy Policy.</span>
        </label>
        <button disabled={loading} className={authButton}>{loading ? "Creating workspace…" : "Create workspace"}</button>
      </form>
      <AuthStatus message={status} tone="error" />
    </AuthShell>
  );
}
