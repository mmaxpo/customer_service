import ProposalScreen from "@/domains/customer-service/automation/ProposalScreen";

type Props = {
  params: Promise<{ proposalId: string }>;
};

export default async function WorkflowProposalPage({ params }: Props) {
  const { proposalId } = await params;
  return <ProposalScreen proposalId={proposalId} />;
}
