import { Suspense } from "react";

import WorkflowComposer from "@/domains/workflow/composer/components/WorkflowComposer";

export default function WorkflowComposerPage() {
    return (
        <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading workflow composer...</div>}>
            <WorkflowComposer />
        </Suspense>
    );
}
