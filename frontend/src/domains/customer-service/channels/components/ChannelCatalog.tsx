import { Badge } from "@/ui/primitives/badge";
import { ProductPanel } from "@/ui/product";

import { channelDescriptions, channelIcon } from "../lib/channelUi";

type Props = {
  channels: string[];
  connectedChannels: Set<string>;
};

export function ChannelCatalog({
  channels,
  connectedChannels,
}: Props) {
  return (
    <ProductPanel
      title="Channel catalog"
      description="These are the surfaces that can feed conversations into the Inbox."
    >
      <div className="grid gap-3 md:grid-cols-2">
        {channels.map((channel) => {
          const Icon = channelIcon(channel);
          const connected = connectedChannels.has(channel);

          return (
            <div key={channel} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100">
                  <Icon size={18} />
                </div>

                <Badge variant={connected ? "success" : "muted"}>
                  {connected ? "connected" : "not connected"}
                </Badge>
              </div>

              <div className="mt-4 font-semibold capitalize text-slate-950">
                {channel}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                {channelDescriptions[channel] || "Customer support channel."}
              </p>
            </div>
          );
        })}
      </div>
    </ProductPanel>
  );
}
