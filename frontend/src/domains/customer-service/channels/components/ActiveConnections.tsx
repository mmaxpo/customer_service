import { ProductPanel } from "@/ui/product";

import type { ChannelConnection } from "@/domains/customer-service/api/customer-service";
import { statusClass } from "../lib/channelUi";

type Props = {
  connections: ChannelConnection[];
};

export function ActiveConnections({
  connections,
}: Props) {
  return (
    <ProductPanel
      title="Active connections"
      description="Connections map external accounts to customer-service conversations."
    >
      {connections.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
          No channel connections yet.
        </div>
      ) : (
        <div className="space-y-3">
          {connections.map((connection) => (
            <div key={connection.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                <div>
                  <div className="font-semibold text-slate-950">
                    {connection.display_name || connection.external_account_id}
                  </div>
                  <div className="mt-1 text-sm text-slate-500">
                    {connection.channel} · {connection.external_account_id}
                  </div>
                </div>

                <span
                  className={[
                    "rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
                    statusClass(connection.status),
                  ].join(" ")}
                >
                  {connection.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </ProductPanel>
  );
}
