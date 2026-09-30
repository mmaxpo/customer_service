"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Plus, ShoppingBag } from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductNotice, ProductPanel } from "@/ui/product";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";
import {
  customerServiceApi,
  type ChannelConnection,
  type ProviderCapability,
} from "@/domains/customer-service/api/customer-service";
import { ActiveConnections } from "@/domains/customer-service/channels/components/ActiveConnections";
import { ChannelCatalog } from "@/domains/customer-service/channels/components/ChannelCatalog";
import { ChannelsOverviewCards } from "@/domains/customer-service/channels/components/ChannelsOverviewCards";
import { ProviderCapabilities } from "@/domains/customer-service/channels/components/ProviderCapabilities";

export default function ChannelsPage() {
  const [channels, setChannels] = useState<string[]>([]);
  const [connections, setConnections] = useState<ChannelConnection[]>([]);
  const [capabilities, setCapabilities] = useState<ProviderCapability[]>([]);
  const [selectedChannel, setSelectedChannel] = useState("shopify");
  const [displayName, setDisplayName] = useState("Main Shopify Store");
  const [externalAccountId, setExternalAccountId] = useState("tajeran-support-dev.myshopify.com");
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [isConnectingShopify, setIsConnectingShopify] = useState(false);
  const [emailIdentity, setEmailIdentity] = useState<any>(null);
  const [emailForm, setEmailForm] = useState({ from_name: "", from_email: "", reply_to: "" });
  const [isSavingEmail, setIsSavingEmail] = useState(false);

  const connectedChannels = useMemo(
    () => new Set(connections.map((connection) => connection.channel)),
    [connections],
  );

  async function refresh() {
    const [channelData, connectionData, capabilityData, emailData] = await Promise.all([
      customerServiceApi.channels().catch(() => ({ channels: [] })),
      customerServiceApi.channelConnections().catch(() => []),
      customerServiceApi.providerCapabilities().catch(() => []),
      customerServiceApi.emailIdentity().catch(() => null),
    ]);

    setChannels(channelData.channels || []);
    setConnections(connectionData);
    setCapabilities(capabilityData);
    setEmailIdentity(emailData);
    if (emailData) setEmailForm({ from_name: emailData.from_name || "", from_email: emailData.from_email || "", reply_to: emailData.reply_to || "" });
  }

  async function saveEmailIdentity(event: React.FormEvent) {
    event.preventDefault();
    try {
      setIsSavingEmail(true);
      const saved = await customerServiceApi.configureEmailIdentity(emailForm);
      setEmailIdentity(saved);
      setStatus("Support email identity saved.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not configure support email.");
    } finally {
      setIsSavingEmail(false);
    }
  }

  async function verifyEmailIdentity() {
    try {
      setEmailIdentity(await customerServiceApi.verifyEmailIdentity());
      setStatus("Email verification requested.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not verify support email.");
    }
  }

  async function connectShopify() {
    try {
      setIsConnectingShopify(true);
      setStatus(null);

      const result = await customerServiceApi.startShopifyInstall(externalAccountId);
      window.location.href = result.install_url;
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not start Shopify OAuth install.");
    } finally {
      setIsConnectingShopify(false);
    }
  }

  async function createConnection() {
    try {
      setIsCreating(true);
      setStatus(null);

      const created = await customerServiceApi.createChannelConnection({
        channel: selectedChannel,
        external_account_id: externalAccountId,
        display_name: displayName,
        config: {
          source: "frontend_quick_setup",
          mode: selectedChannel === "shopify" ? "manual_mapping" : "manual_mapping",
        },
      });

      setConnections((current) => [created, ...current]);
      setStatus(`Connected ${created.display_name || created.external_account_id}.`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not create channel connection.");
    } finally {
      setIsCreating(false);
    }
  }

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setIsLoading(true);
        setStatus(null);
        await refresh();
      } catch (err) {
        if (!alive) return;
        setStatus(err instanceof Error ? err.message : "Could not load channels.");
      } finally {
        if (alive) setIsLoading(false);
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, []);

  return (
    <AppContainer>
      <PageHeader
        eyebrow="Channels"
        title="Connect support channels"
        description="Bring Shopify, email, chat, WhatsApp, Instagram, and social messages into the Tajeran Inbox."
      />

      {status && (
        <ProductNotice>{status}</ProductNotice>
      )}

      {isLoading ? (
        <ProductPanel>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="animate-spin" size={16} />
            Loading channels...
          </div>
        </ProductPanel>
      ) : (
        <>
          <ChannelsOverviewCards
            channelCount={channels.length}
            connectionCount={connections.length}
            providerCount={capabilities.length}
          />

          <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
            <ProductPanel
              title="Quick connect"
              description="Connect Shopify through OAuth or create a manual channel mapping for non-Shopify channels."
            >
              <div className="space-y-3">
                <select
                  value={selectedChannel}
                  onChange={(event) => {
                    const channel = event.target.value;
                    setSelectedChannel(channel);
                    setDisplayName(channel === "shopify" ? "Main Shopify Store" : `${channel} Support`);
                    setExternalAccountId(channel === "shopify" ? "tajeran-support-dev.myshopify.com" : `${channel}-account`);
                  }}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                >
                  {channels.map((channel) => (
                    <option key={channel} value={channel}>
                      {channel}
                    </option>
                  ))}
                </select>

                <Input
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Display name"
                />

                <Input
                  value={externalAccountId}
                  onChange={(event) => setExternalAccountId(event.target.value)}
                  placeholder="External account ID"
                />

                {selectedChannel === "shopify" && (
                  <Button
                    onClick={connectShopify}
                    disabled={isConnectingShopify || !externalAccountId.trim()}
                    className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700"
                  >
                    {isConnectingShopify ? <Loader2 className="animate-spin" size={15} /> : <ShoppingBag size={15} />}
                    Connect Shopify with OAuth
                  </Button>
                )}

                <Button
                  onClick={createConnection}
                  disabled={isCreating || !selectedChannel || !externalAccountId.trim()}
                  className="w-full gap-2"
                >
                  {isCreating ? <Loader2 className="animate-spin" size={15} /> : <Plus size={15} />}
                  Create manual connection
                </Button>
              </div>
            </ProductPanel>

            <div className="space-y-6">
              <ChannelCatalog
                channels={channels}
                connectedChannels={connectedChannels}
              />

              <ActiveConnections connections={connections} />

              <ProviderCapabilities capabilities={capabilities} />
            </div>
          </div>

          <ProductPanel
            title="Support email"
            description="Connect the address customers already use. Incoming and outgoing email threads will appear in the Inbox."
          >
            <form onSubmit={saveEmailIdentity} className="grid gap-3 md:grid-cols-3">
              <Input value={emailForm.from_name} onChange={(event) => setEmailForm({ ...emailForm, from_name: event.target.value })} placeholder="From name" required />
              <Input type="email" value={emailForm.from_email} onChange={(event) => setEmailForm({ ...emailForm, from_email: event.target.value })} placeholder="support@example.com" required />
              <Input type="email" value={emailForm.reply_to} onChange={(event) => setEmailForm({ ...emailForm, reply_to: event.target.value })} placeholder="Reply-to (optional)" />
              <div className="flex flex-wrap items-center gap-2 md:col-span-3">
                <Button type="submit" disabled={isSavingEmail}>{isSavingEmail ? "Saving..." : "Save email identity"}</Button>
                {emailIdentity && <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold capitalize text-slate-700">{emailIdentity.verification_status || "configured"}</span>}
                {emailIdentity && <Button type="button" variant="secondary" onClick={verifyEmailIdentity}>Verify email</Button>}
              </div>
            </form>
          </ProductPanel>
        </>
      )}
    </AppContainer>
  );
}
