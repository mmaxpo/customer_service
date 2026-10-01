import AppShell from "@/ui/layout/AppShell";
import AuthGate from "./AuthGate";
import { ThemeSync } from "@/domains/workspace/ThemeSwitch";
import { PendingInvite } from "@/domains/workspace/PendingInvite";

export default function CustomerAppLayout({
                                              children,
                                          }: {
    children: React.ReactNode;
}) {
    return (
        <AuthGate>
            <ThemeSync />
            <PendingInvite />
            <AppShell>{children}</AppShell>
        </AuthGate>
    );
}
