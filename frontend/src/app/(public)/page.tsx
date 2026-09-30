import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  GitBranch,
  Inbox,
  Layers3,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

const features = [
  {
    icon: Inbox,
    title: "Inbox built for ecommerce",
    text: "One workspace for email, chat, social, Shopify order context, tickets, tags, and AI reply drafting.",
  },
  {
    icon: Workflow,
    title: "Sellable support workflows",
    text: "Launch refund approvals, order status replies, shipping delay flows, and escalation routing from templates.",
  },
  {
    icon: GitBranch,
    title: "Workflow intelligence",
    text: "Every conversation can show intent, urgency, suggested actions, automation trace, and human approval state.",
  },
];

const bullets = [
  "Shopify order context inside support",
  "AI replies grounded in knowledge",
  "Suggested actions agents can accept or run",
  "Human approval for risky actions",
  "Routing by intent, team, queue, priority",
  "Workflow run history and traces",
];

const workflowSteps = [
  ["Customer message", "Damaged item, wants refund for order #10482"],
  ["AI intelligence", "Detects refund intent, high urgency, and review needed"],
  ["Shopify context", "Checks payment, fulfillment, tracking, refund eligibility"],
  ["Human approval", "Pauses high-value refund before action"],
  ["Workflow action", "Runs refund / reply / escalation with trace"],
];

export default function PublicHomePage() {
  return (
    <main className="min-h-screen bg-white text-slate-950">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-white">
            <Sparkles size={18} />
          </div>
          Tajeran.ai
        </Link>

        <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
          <Link href="/app/inbox" className="hover:text-slate-950">
            Inbox
          </Link>
          <Link href="/app/workflows" className="hover:text-slate-950">
            Templates
          </Link>
          <Link href="/login" className="hover:text-slate-950">
            Login
          </Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-20 lg:grid-cols-[1.02fr_0.98fr] lg:items-center">
        <div>
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-purple-100 bg-purple-50 px-3 py-1 text-sm font-medium text-purple-800">
            <Sparkles size={15} />
            AI customer service workflows for Shopify-first brands
          </div>

          <h1 className="max-w-4xl text-5xl font-bold tracking-tight md:text-6xl">
            A support inbox where every conversation can become an intelligent workflow.
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
            Tajeran.ai combines omnichannel support, Shopify context, AI replies, routing,
            knowledge, human approvals, and workflow automation in one customer-service OS.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/app/inbox"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-slate-800"
            >
              Open Inbox
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/app/workflows"
              className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-semibold hover:bg-slate-50"
            >
              View Templates
            </Link>
          </div>

          <div className="mt-8 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
            {bullets.map((item) => (
              <div key={item} className="flex items-center gap-2">
                <CheckCircle2 size={17} className="text-emerald-600" />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-500">Live workflow intelligence</div>
                <div className="font-semibold">Refund approval automation</div>
              </div>
              <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                Active
              </div>
            </div>

            <div className="space-y-3">
              {workflowSteps.map(([title, text], index) => (
                <div
                  key={title}
                  className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950 text-sm font-semibold text-white">
                    {index + 1}
                  </div>
                  <div>
                    <div className="text-sm font-semibold">{title}</div>
                    <div className="text-sm text-slate-500">{text}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl bg-purple-50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-purple-950">
                  <Bot size={16} />
                  AI reply
                </div>
                <p className="mt-2 text-sm leading-6 text-purple-800">
                  Drafted from policy, order context, and conversation history.
                </p>
              </div>

              <div className="rounded-2xl bg-amber-50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-amber-950">
                  <ShieldCheck size={16} />
                  Approval
                </div>
                <p className="mt-2 text-sm leading-6 text-amber-800">
                  Risky action pauses before execution.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-6 pb-10 md:grid-cols-3">
        {features.map((feature) => {
          const Icon = feature.icon;

          return (
            <div key={feature.title} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100">
                <Icon size={20} />
              </div>
              <h2 className="mt-5 text-lg font-bold">{feature.title}</h2>
              <p className="mt-2 leading-7 text-slate-600">{feature.text}</p>
            </div>
          );
        })}
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-20">
        <div className="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-white">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
            <div>
              <div className="text-sm font-medium text-slate-300">Built different</div>
              <h2 className="mt-3 text-3xl font-bold tracking-tight">
                Not just tickets. Agentic customer-service operations.
              </h2>
              <p className="mt-4 leading-7 text-slate-300">
                Normal helpdesks organize support. Tajeran orchestrates support: AI agents,
                humans, tools, approvals, routing, Shopify actions, and runtime traces.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {[
                [Inbox, "Omnichannel Inbox"],
                [Layers3, "Knowledge Base"],
                [Workflow, "Workflow Templates"],
                [GitBranch, "Routing Center"],
              ].map(([Icon, label]: any) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <Icon size={18} className="text-slate-300" />
                  <div className="mt-3 font-semibold">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
