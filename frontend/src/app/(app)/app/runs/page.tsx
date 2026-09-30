import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductPanel } from "@/ui/product";
import RunsList from "@/domains/workflow/runner/components/RunsList";

export default function AppRunsPage() {
  return (
    <AppContainer>
      <PageHeader
        eyebrow="Runtime"
        title="Workflow Runs"
        description="Monitor customer-service automations, agent workflows, approvals, failures, and live execution traces."
      />

      <ProductPanel>
        <RunsList />
      </ProductPanel>
    </AppContainer>
  );
}
