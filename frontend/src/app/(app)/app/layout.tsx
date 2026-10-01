import AppShell from "@/ui/layout/AppShell";
import AuthGate from "./AuthGate";
import { ThemeSync } from "@/domains/workspace/ThemeSwitch";

export default function CustomerAppLayout({
                                              children,
                                          }: {
    children: React.ReactNode;
}) {
    return (
        <AuthGate>
            <ThemeSync />
            <AppShell>{children}</AppShell>
        </AuthGate>
    );
}
