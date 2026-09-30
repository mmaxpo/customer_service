import VersionHistoryScreen from "@/domains/customer-service/automation/VersionHistoryScreen";

type Props = {
  params: Promise<{ workflowId: string }>;
};

export default async function WorkflowHistoryPage({ params }: Props) {
  const { workflowId } = await params;
  return <VersionHistoryScreen workflowId={workflowId} />;
}
