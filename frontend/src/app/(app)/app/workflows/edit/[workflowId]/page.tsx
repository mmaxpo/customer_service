import WorkflowEditorScreen from "@/domains/customer-service/automation/WorkflowEditorScreen";

type Props = {
  params: Promise<{ workflowId: string }>;
};

export default async function WorkflowEditPage({ params }: Props) {
  const { workflowId } = await params;
  return <WorkflowEditorScreen workflowId={workflowId} />;
}
