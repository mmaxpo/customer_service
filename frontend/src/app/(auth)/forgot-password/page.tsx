"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { authButton, authInput, authLabel, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
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
  return (
    <AuthShell title="Reset your password" subtitle="Enter your work email and we'll send a secure reset link." footer={<p><Link href="/login" className="font-medium text-primary hover:underline">Back to log in</Link></p>}>
      <form onSubmit={submit} className="mt-7 space-y-4">
        <label className={authLabel}>Work email
          <input className={authInput} type="email" required autoComplete="email" placeholder="jane@mystore.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <button disabled={loading} className={authButton}>{loading ? "Sending…" : "Send reset link"}</button>
      </form>
      <AuthStatus message={status} />
    </AuthShell>
  );
}
