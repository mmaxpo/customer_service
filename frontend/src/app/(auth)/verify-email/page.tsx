"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
        <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
            <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-medium text-slate-500">Tajeran.ai</p>
                <h1 className="mt-2 text-2xl font-bold tracking-tight">Verify your email</h1>
                <p className="mt-3 text-sm leading-6 text-slate-600">{status}</p>
                <button
                    type="button"
                    onClick={resend}
                    disabled={sending}
                    className="mt-6 w-full rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {sending ? "Sending..." : "Resend verification email"}
                </button>
                <Link href="/login" className="mt-4 block text-center text-sm font-medium text-slate-700">
                    Back to login
                </Link>
            </section>
        </main>
    );
}
