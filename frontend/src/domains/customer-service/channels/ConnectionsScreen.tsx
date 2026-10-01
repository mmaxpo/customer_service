"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Mail, MessageCircle, MessagesSquare, ShoppingBag } from "lucide-react";

import {
  customerServiceApi,
  getChatWidgetSettings,
  type ChannelConnection,
  type ChatWidgetSettings,
} from "@/domains/customer-service/api/customer-service";
import { apiErrorMessage } from "@/platform/api/client";
import { Button } from "@/ui/primitives/button";
import { Input } from "@/ui/primitives/input";

import { ToneChip } from "../inbox/case/parts";

type EmailIdentity = {
  from_name: string;
  from_email: string;
  reply_to: string | null;
  verification_status: string;
} | null;

// Channels the backend can't connect yet (adapters exist, provider setup doesn't).
const COMING_SOON = [
  { name: "WhatsApp", description: "Answer WhatsApp Business messages in the Inbox." },
  { name: "Instagram", description: "Answer Instagram direct messages in the Inbox." },
  { name: "Facebook Messenger", description: "Answer Messenger conversations in the Inbox." },
];

function Row({
  icon: Icon,
  name,
  description,
  status,
  children,
}: {
  icon: React.ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>;
  name: string;
  description: string;
  status: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <li className="flex items-start gap-3 px-4 py-4">
      <Icon size={18} className="mt-0.5 shrink-0 text-text-secondary" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[14px] font-semibold text-foreground">{name}</h3>
          {status}
        </div>
        <p className="mt-0.5 text-[13px] text-text-secondary">{description}</p>
        {children}
      </div>
    </li>
  );
}

function emailStatus(identity: EmailIdentity) {
  if (!identity) return <ToneChip tone="neutral">Not set up</ToneChip>;
  if (identity.verification_status === "verified") return <ToneChip tone="commerce">Verified</ToneChip>;
  return <ToneChip tone="attention">Waiting for verification</ToneChip>;
}

export default function ConnectionsScreen() {
  const [connections, setConnections] = useState<ChannelConnection[]>([]);
  const [widget, setWidget] = useState<ChatWidgetSettings | null>(null);
  const [email, setEmail] = useState<EmailIdentity>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [shopDomain, setShopDomain] = useState("");
  const [emailForm, setEmailForm] = useState({ from_name: "", from_email: "", reply_to: "" });
  const [busy, setBusy] = useState<"shopify" | "email" | "verify" | null>(null);

  useEffect(() => {
    Promise.all([
      customerServiceApi.channelConnections(),
      getChatWidgetSettings().catch(() => null),
      customerServiceApi.emailIdentity().catch(() => null),
    ])
      .then(([connectionList, widgetSettings, identity]) => {
        setConnections(connectionList);
        setWidget(widgetSettings);
        setEmail(identity);
        if (identity) setEmailForm({ from_name: identity.from_name ?? "", from_email: identity.from_email ?? "", reply_to: identity.reply_to ?? "" });
      })
      .catch((err) => setError(apiErrorMessage(err, "Could not load your connections.")))
      .finally(() => setLoading(false));
  }, []);

  const shopify = connections.find((c) => c.channel === "shopify" && c.status === "active");

  const connectShopify = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy("shopify");
    setError(null);
    try {
      const { install_url } = await customerServiceApi.startShopifyInstall(shopDomain.trim());
      window.location.href = install_url;
    } catch (err) {
      setError(apiErrorMessage(err, "Could not start connecting Shopify."));
      setBusy(null);
    }
  };

  const saveEmail = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy("email");
    setError(null);
    try {
      setEmail(await customerServiceApi.configureEmailIdentity({ ...emailForm, reply_to: emailForm.reply_to || null }));
      setNotice("Support email saved. Verify it so replies can be sent from this address.");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save the support email."));
    } finally {
      setBusy(null);
    }
  };

  const verifyEmail = async () => {
    setBusy("verify");
    setError(null);
    try {
      setEmail(await customerServiceApi.verifyEmailIdentity());
      setNotice("Verification requested. Add the DNS records from your email provider, then check again.");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not verify the support email."));
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return (
      <p className="mt-5 flex items-center gap-2 text-[13.5px] text-text-secondary">
        <Loader2 size={15} className="animate-spin" aria-hidden /> Loading connections…
      </p>
    );
  }

  return (
    <div className="mt-5 max-w-3xl space-y-3">
      <p className="text-[13.5px] text-text-secondary">
        Messages from every connected channel arrive in one Inbox, where your team and your workflows answer them.
      </p>
      {error ? <p role="alert" className="text-[13px] text-danger">{error}</p> : null}
      {notice ? <p role="status" className="text-[13px] text-foreground">{notice}</p> : null}

      <ul className="divide-y divide-border rounded-container border border-border bg-surface">
        <Row
          icon={ShoppingBag}
          name="Shopify"
          description="Order details in every conversation, and order actions after approval."
          status={shopify ? <ToneChip tone="commerce">Connected</ToneChip> : <ToneChip tone="neutral">Not connected</ToneChip>}
        >
          {shopify ? (
            <p className="mt-1.5 text-[13px] text-foreground">{shopify.display_name || shopify.external_account_id} · {shopify.external_account_id}</p>
          ) : (
            <form onSubmit={connectShopify} className="mt-2.5 flex max-w-md gap-2">
              <label htmlFor="shop-domain" className="sr-only">Shopify store domain</label>
              <Input id="shop-domain" value={shopDomain} onChange={(e) => setShopDomain(e.target.value)} placeholder="your-store.myshopify.com" required />
              <Button type="submit" size="sm" disabled={busy !== null || !shopDomain.trim()}>
                {busy === "shopify" ? "Opening Shopify…" : "Connect"}
              </Button>
            </form>
          )}
        </Row>

        <Row
          icon={MessageCircle}
          name="Website chat"
          description="The chat bubble on your store. Customers get answers from your workflows, or reach your team."
          status={widget?.enabled ? <ToneChip tone="commerce">On</ToneChip> : <ToneChip tone="neutral">Off</ToneChip>}
        >
          <Link href="/app/settings/chat-widget" className="mt-1.5 inline-block text-[13px] font-medium text-primary hover:underline">
            Install code, look and greeting
          </Link>
        </Row>

        <Row
          icon={Mail}
          name="Email"
          description="Replies to customers are sent from your support address. Receiving email into the Inbox isn't available yet."
          status={emailStatus(email)}
        >
          <form onSubmit={saveEmail} className="mt-2.5 grid gap-2 sm:grid-cols-3">
            <label className="text-[12.5px] font-medium text-foreground">
              From name
              <Input className="mt-1" value={emailForm.from_name} onChange={(e) => setEmailForm({ ...emailForm, from_name: e.target.value })} placeholder="Acme Support" required />
            </label>
            <label className="text-[12.5px] font-medium text-foreground">
              Support address
              <Input className="mt-1" type="email" value={emailForm.from_email} onChange={(e) => setEmailForm({ ...emailForm, from_email: e.target.value })} placeholder="support@your-store.com" required />
            </label>
            <label className="text-[12.5px] font-medium text-foreground">
              Reply-to (optional)
              <Input className="mt-1" type="email" value={emailForm.reply_to} onChange={(e) => setEmailForm({ ...emailForm, reply_to: e.target.value })} />
            </label>
            <div className="flex gap-2 sm:col-span-3">
              <Button type="submit" size="sm" disabled={busy !== null}>{busy === "email" ? "Saving…" : "Save"}</Button>
              {email && email.verification_status !== "verified" ? (
                <Button type="button" variant="secondary" size="sm" disabled={busy !== null} onClick={() => void verifyEmail()}>
                  {busy === "verify" ? "Checking…" : "Verify"}
                </Button>
              ) : null}
            </div>
          </form>
        </Row>

        {COMING_SOON.map((channel) => (
          <Row
            key={channel.name}
            icon={MessagesSquare}
            name={channel.name}
            description={channel.description}
            status={<ToneChip tone="neutral">Coming soon</ToneChip>}
          />
        ))}
      </ul>
    </div>
  );
}
