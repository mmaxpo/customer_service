"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bot,
  GitBranch,
  Loader2,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

import AppContainer from "@/ui/layout/AppContainer";
import PageHeader from "@/ui/layout/PageHeader";
import { Badge } from "@/ui/primitives/badge";
import { Button } from "@/ui/primitives/button";
import { ProductNotice, ProductPanel, ProductStatCard } from "@/ui/product";
import {
  customerServiceApi,
  type WorkflowTemplate,
} from "@/domains/customer-service/api/customer-service";

const featuredTemplates = [
  {
    id: "refund",
    title: "Refund approval flow",
    description:
      "Pause high-value refunds for human approval, check Shopify order context, then continue automatically.",
    badge: "Shopify",
    icon: ShieldCheck,
  },
  {
    id: "order-status",
    title: "Order status assistant",
    description:
      "Answer order status questions using Shopify, shipping tracking, knowledge, and AI reply quality checks.",
    badge: "Automation",
    icon: Bot,
  },
  {
    id: "escalation-router",
    title: "Escalation router",
    description:
      "Route urgent conversations to the right team, queue, agent, or workflow branch based on intent and priority.",
    badge: "Routing",
    icon: GitBranch,
  },
  {
    id: "shipping-delay",
    title: "Shipping delay automation",
    description:
      "Detect shipping-delay intent, retrieve tracking context, explain delay, and escalate late packages.",
    badge: "Shipping",
    icon: PlayCircle,
  },
  {
    id: "vip-escalation",
    title: "VIP escalation",
    description:
      "Identify VIP or high-risk customers and route them to priority queues with workflow trace visibility.",
    badge: "VIP",
    icon: Sparkles,
  },
  {
    id: "return-exchange",
    title: "Return & exchange flow",
    description:
      "Guide return eligibility, exchange options, labels, and approval handoff from one customer-service workflow.",
    badge: "Returns",
    icon: Workflow,
  },
];

function statusVariant(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "published") return "success";
  if (normalized === "draft") return "warning";

  return "default";
}

function formatDate(value?: string) {
  if (!value) return "—";

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export default function WorkflowTemplatesPage() {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const systemTemplates = useMemo(
    () => templates.filter((template) => template.scope === "system"),
    [templates],
  );

  const privateTemplates = useMemo(
    () => templates.filter((template) => template.scope === "private"),
    [templates],
  );

  async function loadTemplates() {
    try {
      setIsLoading(true);
      setStatus(null);

      const data = await customerServiceApi.workflowTemplates();
      setTemplates(data);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not load workflow templates.");
    } finally {
      setIsLoading(false);
    }
  }

  async function seedShopifyTemplates() {
    try {
      setIsSeeding(true);
      setStatus(null);

      const result = await customerServiceApi.seedShopifyWorkflowTemplates();
      setStatus(
        `Shopify templates ready: ${result.created_count} created, ${result.existing_count} already existed.`,
      );

      await loadTemplates();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not seed Shopify templates.");
    } finally {
      setIsSeeding(false);
    }
  }

  async function cloneTemplate(template: WorkflowTemplate) {
    try {
      setActiveTemplateId(template.id);
      setStatus(null);

      const cloned = await customerServiceApi.cloneWorkflowTemplate(template.id, {
        name: `${template.name} Copy`,
      });

      setTemplates((current) => [cloned, ...current]);
      setStatus(`Created private draft: ${cloned.name}`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not clone template.");
    } finally {
      setActiveTemplateId(null);
    }
  }

  async function togglePublish(template: WorkflowTemplate) {
    try {
      setActiveTemplateId(template.id);
      setStatus(null);

      const updated =
        template.status === "published"
          ? await customerServiceApi.unpublishWorkflowTemplate(template.id)
          : await customerServiceApi.publishWorkflowTemplate(template.id);

      setTemplates((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not update template status.");
    } finally {
      setActiveTemplateId(null);
    }
  }

  useEffect(() => {
    loadTemplates().catch(() => {});
  }, []);

  return (
    <AppContainer>
      <PageHeader
        eyebrow="Support Autopilot"
        title="Automate the questions your team answers every day"
        description="Choose a proven Shopify workflow, review the safety steps, and test it with a real customer message before you turn it on."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={seedShopifyTemplates}
              disabled={isSeeding}
            >
              {isSeeding ? "Preparing..." : "Prepare Shopify workflows"}
            </Button>
            <Link
              href="/app/workflows/builder?template=blank"
              className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-900 transition hover:bg-slate-50"
            >
              Create from scratch
            </Link>
          </div>
        }
      />

      {status && (
        <ProductNotice>{status}</ProductNotice>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <ProductStatCard label="Featured" value={featuredTemplates.length} />
        <ProductStatCard label="System templates" value={systemTemplates.length} />
        <ProductStatCard
          label="Private drafts"
          value={privateTemplates.filter((template) => template.status === "draft").length}
        />
        <ProductStatCard
          label="Published"
          value={templates.filter((template) => template.status === "published").length}
        />
      </div>

      <ProductPanel
        title="Start with a customer outcome"
        description="Every workflow below connects to Shopify context. Risky actions pause for your approval before anything changes an order."
      >
        <div className="grid gap-4 md:grid-cols-3">
          {featuredTemplates.map((template) => {
            const Icon = template.icon;

            return (
              <div
                key={template.id}
                className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100">
                    <Icon size={20} />
                  </div>

                  <Badge variant="default" className="border-purple-100 bg-purple-50 text-purple-700">
                    {template.badge}
                  </Badge>
                </div>

                <h3 className="mt-5 font-semibold text-slate-950">
                  {template.title}
                </h3>

                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {template.description}
                </p>

                <Link
                  href={`/app/workflows/builder?template=${template.id}`}
                  className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-slate-950"
                >
                  Review workflow
                  <ArrowRight size={15} />
                </Link>
              </div>
            );
          })}
        </div>
      </ProductPanel>

      <ProductPanel
        title="Installed workflow templates"
        description="Backend-backed system and private templates. Clone system templates into private drafts, then publish when ready."
      >
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="animate-spin" size={16} />
            Loading workflow templates...
          </div>
        ) : templates.length === 0 ? (
          <ProductNotice>
            No templates installed yet. Seed Shopify templates to create the first system catalog.
          </ProductNotice>
        ) : (
          <div className="space-y-3">
            {templates.map((template) => (
              <div
                key={template.id}
                className="rounded-2xl border border-slate-200 bg-white p-4"
              >
                <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">{template.name}</h3>
                      <Badge variant={statusVariant(template.status) as "success" | "warning" | "default"} className="capitalize">
                        {template.status}
                      </Badge>
                      <Badge variant="default">{template.scope}</Badge>
                    </div>

                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      {template.description || "No description."}
                    </p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                        {template.category}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                        v{template.version}
                      </span>
                      <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                        {formatDate(template.created_at)}
                      </span>
                      {(template.tags || []).slice(0, 4).map((tag) => (
                        <span key={tag} className="rounded-full bg-purple-50 px-2.5 py-1 text-xs text-purple-700">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-2">
                    {template.scope === "system" ? (
                      <Button
                        size="sm"
                        onClick={() => cloneTemplate(template)}
                        disabled={activeTemplateId !== null}
                      >
                        {activeTemplateId === template.id ? "Cloning..." : "Clone"}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => togglePublish(template)}
                        disabled={activeTemplateId !== null}
                      >
                        {activeTemplateId === template.id
                          ? "Updating..."
                          : template.status === "published"
                            ? "Unpublish"
                            : "Publish"}
                      </Button>
                    )}

                    <Link
                      href={`/app/workflows/builder?templateId=${encodeURIComponent(template.id)}`}
                      className="inline-flex h-8 items-center justify-center rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-900 transition hover:bg-slate-50"
                    >
                      Open builder
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </ProductPanel>

      <ProductPanel
        title="How Support Autopilot works"
        description="A simple path for your team and a controlled path for every Shopify action."
      >
        <div className="grid gap-4 md:grid-cols-3">
          {[
            "Understands the customer message",
            "Checks the Shopify order and shipping context",
            "Uses your policies and knowledge base",
            "Pauses refunds and cancellations for approval",
            "Replies clearly and keeps a run history",
            "Escalates edge cases to your team",
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4"
            >
              <Workflow size={17} className="text-slate-500" />
              <span className="text-sm font-medium">{item}</span>
            </div>
          ))}
        </div>
      </ProductPanel>
    </AppContainer>
  );
}
