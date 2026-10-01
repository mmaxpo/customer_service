import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { SettingsTabs } from "@/domains/workspace/SettingsTabs";
import TeamScreen from "@/domains/workspace/TeamScreen";

export default function TeamPage() {
  return (
    <AppContainer>
      <PageHeader eyebrow="Workspace" title="Settings" description="Configure the identity, working hours, and people behind your customer-support workspace." />
      <SettingsTabs />
      <TeamScreen />
    </AppContainer>
  );
}
