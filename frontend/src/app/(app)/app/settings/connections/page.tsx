import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import ConnectionsScreen from "@/domains/customer-service/channels/ConnectionsScreen";
import { SettingsTabs } from "@/domains/workspace/SettingsTabs";

export default function ConnectionsPage() {
  return (
    <AppContainer>
      <PageHeader eyebrow="Workspace" title="Settings" description="Configure the identity, working hours, and people behind your customer-support workspace." />
      <SettingsTabs />
      <ConnectionsScreen />
    </AppContainer>
  );
}
