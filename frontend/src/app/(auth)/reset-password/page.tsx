"use client";

import Link from "next/link";
import { PasswordInput } from "@/ui/primitives/password-input";
import { FormEvent, useEffect, useState } from "react";
import { authButton, authInput, authLabel, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
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
  return (
    <AuthShell title="Choose a new password" subtitle="You'll use it the next time you log in." footer={<p><Link href="/login" className="font-medium text-primary hover:underline">Back to log in</Link></p>}>
      <form onSubmit={submit} className="mt-7 space-y-4">
        <label className={authLabel}>New password
          <PasswordInput className={authInput} minLength={8} required autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <span className="mt-1.5 block text-[12.5px] font-normal text-text-secondary">At least 8 characters, with a letter and a number.</span>
        </label>
        <button className={authButton}>Update password</button>
      </form>
      <AuthStatus message={status} />
    </AuthShell>
  );
}
