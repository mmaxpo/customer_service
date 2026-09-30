"use client";

import RunOutputPanel from "@/domains/workflow/builder/components/panels/RunOutputPanel";

type Props = {
  runAnswer: string;
  setRunAnswer: (value: string) => void;
  runStatus: string;
};

export default function BuilderRunOutputContainer({
  runAnswer,
  setRunAnswer,
  runStatus,
}: Props) {
  return (
    <RunOutputPanel
      runAnswer={runAnswer}
      setRunAnswer={setRunAnswer}
      runStatus={runStatus}
    />
  );
}
