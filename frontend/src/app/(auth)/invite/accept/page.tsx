"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { authButton, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
import { apiErrorMessage, apiJson, jsonBody } from "@/platform/api/client";
import { authApi } from "@/platform/api";

// Kept across sign-up, email verification and login, so the invitation is
// accepted as soon as the person is signed in (see PendingInvite).
const INVITE_KEY = "tajeran-invite-token";

type Preview = { email: string; role: string; workspace_name: string };
type Step = "loading" | "invalid" | "signed-out" | "wrong-account" | "joining";

export default function AcceptInvitePage() {
  const [step, setStep] = useState<Step>("loading");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [signedInAs, setSignedInAs] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get("token") ?? "";
    if (!token) {
      setStep("invalid");
      return;
    }

    (async () => {
      let invite: Preview;
      try {
        invite = await apiJson<Preview>(`/api/workspaces/invitations/preview?token=${encodeURIComponent(token)}`);
      } catch {
        try { localStorage.removeItem(INVITE_KEY); } catch {}
        setStep("invalid");
        return;
      }
      setPreview(invite);

      let user: { email: string; email_verified_at?: string | null } | null = null;
      try {
        user = await authApi.me();
      } catch {
        user = null;
      }

      if (!user) {
        try { localStorage.setItem(INVITE_KEY, token); } catch {}
        setStep("signed-out");
        return;
      }
      if (user.email.trim().toLowerCase() !== invite.email.trim().toLowerCase()) {
        setSignedInAs(user.email);
        setStep("wrong-account");
        return;
      }
      if (!user.email_verified_at) {
        try { localStorage.setItem(INVITE_KEY, token); } catch {}
        window.location.href = "/verify-email";
        return;
      }

      setStep("joining");
      try {
        await apiJson("/api/workspaces/invitations/accept", { method: "POST", body: jsonBody({ token }) });
        try { localStorage.removeItem(INVITE_KEY); } catch {}
        window.location.href = "/app/inbox";
      } catch (err) {
        setError(apiErrorMessage(err, "Could not accept this invitation."));
        setStep("invalid");
      }
    })();
  }, []);

  const logOutAndRetry = async () => {
    await authApi.logout();
    window.location.reload();
  };

  const invited = preview ? `${preview.workspace_name} as ${preview.role}` : "";

  return (
    <AuthShell
      title={step === "invalid" ? "This invitation can't be used" : preview ? `Join ${preview.workspace_name}` : "Joining your team…"}
      subtitle={preview ? `You've been invited to join ${invited}.` : "One moment."}
      footer={null}
    >
      {step === "signed-out" && preview ? (
        <div className="mt-7 space-y-3">
          <p className="text-[13.5px] text-text-secondary">
            Use the email address this invitation was sent to: <strong className="text-foreground">{preview.email}</strong>. You choose your own password.
          </p>
          <Link href={`/signup?email=${encodeURIComponent(preview.email)}`} className={`${authButton} flex items-center justify-center`}>Create an account</Link>
          <Link href={`/login?email=${encodeURIComponent(preview.email)}`} className="block text-center text-[13.5px] font-medium text-primary hover:underline">I already have an account</Link>
        </div>
      ) : null}

      {step === "wrong-account" && preview ? (
        <div className="mt-7 space-y-3">
          <p className="text-[13.5px] text-text-secondary">
            You're signed in as <strong className="text-foreground">{signedInAs}</strong>, but this invitation is for <strong className="text-foreground">{preview.email}</strong>.
          </p>
          <button type="button" onClick={() => void logOutAndRetry()} className={authButton}>Log out and continue</button>
        </div>
      ) : null}

      {step === "invalid" ? (
        <p className="mt-7 text-[13.5px] text-text-secondary">
          It may have expired, been cancelled, or already been used. Ask your admin to send a new one, or <Link href="/login" className="font-medium text-primary hover:underline">log in</Link>.
        </p>
      ) : null}

      <AuthStatus message={error ?? (step === "joining" ? "Joining…" : null)} tone={error ? "error" : "info"} />
    </AuthShell>
  );
}
