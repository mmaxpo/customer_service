import { ProductPanel } from "@/ui/product";

import type { ProviderCapability } from "@/domains/customer-service/api/customer-service";

type Props = {
  capabilities: ProviderCapability[];
};

export function ProviderCapabilities({
  capabilities,
}: Props) {
  return (
    <ProductPanel
      title="Provider capabilities"
      description="Backend provider adapters advertise what they can do."
    >
      {capabilities.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
          No provider capabilities returned yet.
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {capabilities.map((capability, index) => (
            <div key={index} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="font-semibold text-slate-950">
                {String(capability.name || capability.provider || capability.channel || "Provider")}
              </div>
              <pre className="mt-3 max-h-40 overflow-auto rounded-xl bg-slate-950 p-3 text-xs text-slate-100">
                {JSON.stringify(capability, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </ProductPanel>
  );
}
