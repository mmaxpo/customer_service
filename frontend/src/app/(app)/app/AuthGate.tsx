"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/platform/api";

export default function AuthGate({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let cancelled = false;

        async function checkAuth() {
            try {
                const user = (await authApi.me()) as { email_verified_at?: string | null };

                if (!user.email_verified_at) {
                    router.replace("/verify-email");
                    return;
                }

                if (!cancelled) {
                    setReady(true);
                }
            } catch {
                if (!cancelled) {
                    router.replace("/login");
                }
            }
        }

        checkAuth();

        return () => {
            cancelled = true;
        };
    }, [router]);

    if (!ready) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">
                Checking authentication...
            </div>
        );
    }

    return <>{children}</>;
}
