import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductPanel } from "@/ui/product";
import RunnerShell from "@/domains/workflow/runner/components/RunnerShell";

type Props = {
  params: Promise<{ runId: string }>;
};

export default async function AppRunDetailPage({ params }: Props) {
  const { runId } = await params;

  return (
    <AppContainer>
      <PageHeader
        eyebrow="Runtime trace"
        title="Workflow run detail"
        description="Inspect workflow state, node execution, agent traces, events, and human approval pauses."
        actions={
          <Link
            href="/app/runs"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft size={15} />
            Back to runs
          </Link>
        }
      />

      <ProductPanel>
        <RunnerShell runId={runId} />
      </ProductPanel>
    </AppContainer>
  );
}
