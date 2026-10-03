"use client";

import { useEffect, useState } from "react";
import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import { customerServiceApi } from "@/domains/customer-service/api/customer-service";

const plans = [
  { id: "starter" as const, name: "Starter", description: "For a small support team getting started.", price: "$49/mo" },
  { id: "growth" as const, name: "Growth", description: "For stores ready to automate more conversations.", price: "$149/mo" },
  { id: "pro" as const, name: "Pro", description: "For teams running support as an operation.", price: "$399/mo" },
];

export default function BillingPage() {
  const [subscription, setSubscription] = useState<any>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    customerServiceApi.subscription().then(setSubscription).catch((error) => setStatus(error instanceof Error ? error.message : "Could not load billing.")).finally(() => setLoading(false));
  }, []);

  async function choosePlan(plan: "starter" | "growth" | "pro") {
    try {
      setBusy(plan);
      setStatus(null);
      const result = await customerServiceApi.billingCheckout(plan);
      window.location.href = result.confirmation_url;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not start Shopify billing.");
    } finally {
      setBusy(null);
    }
  }

  async function openPortal() {
    try {
      const result = await customerServiceApi.billingPortal();
      window.location.href = result.manage_url;
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Billing portal is not available yet.");
    }
  }

  return (
    <AppContainer>
      <PageHeader eyebrow="Commercial" title="Plan & usage" description="Manage your Tajeran trial or subscription through Shopify billing." />
      {status && <ProductNotice>{status}</ProductNotice>}
      {loading ? <ProductPanel title="Loading billing" description="Checking your current plan." ><div className="h-12" /></ProductPanel> : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <ProductStatCard label="Current plan" value={subscription?.plan || "trial"} description={subscription?.status || "trialing"} />
            <ProductStatCard label="Billing status" value={subscription?.status || "trialing"} description="Shopify-managed billing" />
            <ProductStatCard label="Trial ends" value={subscription?.trial_ends_at ? new Date(subscription.trial_ends_at).toLocaleDateString() : "—"} description="Upgrade before your trial ends" />
          </div>
          <ProductPanel title="Choose a plan" description="Start with a trial and upgrade when Tajeran is handling real customer conversations.">
            <div className="grid gap-4 md:grid-cols-3">
              {plans.map((plan) => <div key={plan.id} className="rounded-2xl border border-border bg-surface p-5"><div className="flex items-center justify-between"><h3 className="font-semibold text-foreground">{plan.name}</h3><span className="text-sm font-bold text-text-secondary">{plan.price}</span></div><p className="mt-2 min-h-12 text-sm leading-6 text-text-secondary">{plan.description}</p><button onClick={() => choosePlan(plan.id)} disabled={busy !== null} className="mt-5 w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{busy === plan.id ? "Opening Shopify..." : "Choose plan"}</button></div>)}
            </div>
            {subscription?.status === "active" && <button onClick={openPortal} className="mt-5 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-foreground">Manage subscription</button>}
          </ProductPanel>
        </>
      )}
    </AppContainer>
  );
}
