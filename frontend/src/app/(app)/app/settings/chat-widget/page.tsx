import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import ChatWidgetScreen from "@/domains/customer-service/chatbot/ChatWidgetScreen";
import { SettingsTabs } from "@/domains/workspace/SettingsTabs";

export default function ChatWidgetPage() {
  return (
    <AppContainer>
      <PageHeader eyebrow="Workspace" title="Settings" description="Configure the identity, working hours, and people behind your customer-support workspace." />
      <SettingsTabs />
      <ChatWidgetScreen />
    </AppContainer>
  );
}
