import RunnerShell from "@/domains/workflow/runner/components/RunnerShell";

type Props = {
    params: Promise<{ runId: string }>;
};

export default async function RunPage({ params }: Props) {
    const { runId } = await params;
    return <RunnerShell runId={runId} />;
}