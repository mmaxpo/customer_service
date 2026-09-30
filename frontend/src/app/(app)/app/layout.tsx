import AppShell from "@/ui/layout/AppShell";
import AuthGate from "./AuthGate";

export default function CustomerAppLayout({
                                              children,
                                          }: {
    children: React.ReactNode;
}) {
    return (
        <AuthGate>
            <AppShell>{children}</AppShell>
        </AuthGate>
    );
}
