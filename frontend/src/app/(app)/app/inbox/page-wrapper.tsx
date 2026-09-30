import { Suspense } from "react";

import InboxPage from "./page";

export default function InboxPageWrapper() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading inbox...</div>}>
      <InboxPage />
    </Suspense>
  );
}
