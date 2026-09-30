import RunReviewScreen from "@/domains/customer-service/automation/RunReviewScreen";

type Props = {
  params: Promise<{ runId: string }>;
};

export default async function WorkflowRunReviewPage({ params }: Props) {
  const { runId } = await params;
  return <RunReviewScreen runId={runId} />;
}
