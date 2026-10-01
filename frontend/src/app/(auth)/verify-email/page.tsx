"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authButton, AuthShell, AuthStatus } from "@/components/marketing/AuthShell";
import { ApiError, authApi } from "@/platform/api";

export default function VerifyEmailPage() {
    const router = useRouter();
    const [status, setStatus] = useState("Check your inbox for a verification link.");
    const [sending, setSending] = useState(false);

    useEffect(() => {
        const token = new URLSearchParams(window.location.search).get("token");
        if (!token) return;

        void (async () => {
            setStatus("Verifying your email...");
            try {
                await authApi.confirmEmailVerification(token);
                setStatus("Email verified. Redirecting to your workspace...");
                router.replace("/app/dashboard");
            } catch (error) {
                setStatus(
                    error instanceof ApiError
                        ? "This verification link is invalid or expired. Request a new one."
                        : "We could not verify this email. Request a new link.",
                );
            }
        })();
    }, [router]);

    async function resend() {
        setSending(true);
        try {
            await authApi.requestEmailVerification();
            setStatus("Verification instructions were sent. Check your inbox.");
        } catch (error) {
            setStatus(
                error instanceof ApiError && error.status === 401
                    ? "Please log in before requesting a verification email."
                    : "We could not send a verification email. Please try again shortly.",
            );
        } finally {
            setSending(false);
        }
    }

    return (
        <AuthShell title="Verify your email" subtitle="We sent a link to the address you signed up with." footer={<p><Link href="/login" className="font-medium text-primary hover:underline">Back to log in</Link></p>}>
            <AuthStatus message={status} />
            <button type="button" onClick={resend} disabled={sending} className={`${authButton} mt-5 disabled:cursor-not-allowed`}>
                {sending ? "Sending…" : "Resend verification email"}
            </button>
        </AuthShell>
    );
}
