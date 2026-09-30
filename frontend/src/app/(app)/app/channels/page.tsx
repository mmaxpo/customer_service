import { redirect } from "next/navigation";

// Channels moved into Settings → Connections.
export default function ChannelsPage() {
  redirect("/app/settings/connections");
}
