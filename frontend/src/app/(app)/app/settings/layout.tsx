"use client";

import { roleAtLeast, useWorkspaceRole } from "@/domains/workspace/useWorkspaceRole";
import { ThemeSwitch } from "@/domains/workspace/ThemeSwitch";
import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";

// Workspace settings are for admins and the owner. Everyone else only gets
// their own display setting.
export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const role = useWorkspaceRole();

  if (role === null) {
    return <AppContainer><div className="h-40 animate-pulse rounded bg-muted" /></AppContainer>;
  }
  if (roleAtLeast(role, "admin")) return <>{children}</>;

  return (
    <AppContainer>
      <PageHeader eyebrow="Settings" title="Your settings" description="Workspace settings, connections, the chat widget and the team are managed by your admin." />
      <div className="mt-5 flex items-center gap-3">
        <span className="text-[13.5px] text-foreground">Appearance</span>
        <ThemeSwitch />
      </div>
    </AppContainer>
  );
}
