import { Cable, CheckCircle2, MessageSquare } from "lucide-react";

import { ProductStatCard } from "@/ui/product";

type Props = {
  channelCount: number;
  connectionCount: number;
  providerCount: number;
};

export function ChannelsOverviewCards({
  channelCount,
  connectionCount,
  providerCount,
}: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <ProductStatCard label="Supported channels" value={channelCount} icon={Cable} />
      <ProductStatCard label="Connections" value={connectionCount} icon={CheckCircle2} />
      <ProductStatCard label="Providers" value={providerCount} icon={MessageSquare} />
    </div>
  );
}
