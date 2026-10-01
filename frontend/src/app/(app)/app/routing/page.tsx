import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import RoutingScreen from "@/domains/customer-service/routing/RoutingScreen";

export default function RoutingPage() {
  return (
    <AppContainer>
      <PageHeader
        eyebrow="Team"
        title="Routing"
        description="Decide which team member gets a conversation when it needs a person."
      />
      <RoutingScreen />
    </AppContainer>
  );
}
