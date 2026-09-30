import { ShieldCheck, Sparkles, Workflow } from "lucide-react";

import { MessageCircle, Metric, Status } from "./ChatbotUi";

type Props = {
  publicKey: string;
  enabled: boolean;
  autoAnswerAttached: boolean;
  hasPublicKey: boolean;
};

export function ChatbotHero({
  publicKey,
  enabled,
  autoAnswerAttached,
  hasPublicKey,
}: Props) {
  return (
    <section className="relative overflow-hidden rounded-[2rem] bg-slate-950 p-7 text-white shadow-2xl shadow-slate-950/30 lg:p-9">
      <div className="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-emerald-400/20 blur-3xl" />
      <div className="absolute bottom-0 left-1/2 h-56 w-56 rounded-full bg-cyan-400/10 blur-3xl" />

      <div className="relative grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-bold text-emerald-100">
            <Sparkles size={14} />
            Premium Shopify AI support widget
          </div>

          <h1 className="mt-5 max-w-4xl text-4xl font-black tracking-tight sm:text-5xl">
            Turn your Shopify storefront into an AI-powered support channel.
          </h1>

          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
            Every visitor message becomes a Tajeran Inbox conversation, ticket, SLA event, and optional workflow-powered reply.
          </p>

          <div className="mt-7 grid gap-3 sm:grid-cols-3">
            <Metric icon={MessageCircle} label="Widget" value="Live chat" />
            <Metric icon={ShieldCheck} label="Support" value="Inbox + SLA" />
            <Metric icon={Workflow} label="Automation" value="Workflow ready" />
          </div>
        </div>

        <div className="rounded-[1.75rem] border border-white/10 bg-white/[0.07] p-5 backdrop-blur">
          <div className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Public install key</div>
          <div className="mt-3 break-all rounded-2xl border border-white/10 bg-black/30 p-4 font-mono text-sm text-emerald-100">
            {publicKey}
          </div>

          <div className="mt-5 space-y-3">
            <Status active={enabled} label={enabled ? "Widget enabled" : "Widget disabled"} />
            <Status
              active={autoAnswerAttached}
              label={autoAnswerAttached ? "AI automation attached" : "Manual support mode"}
            />
            <Status active={hasPublicKey} label="Safe public key generated" />
          </div>
        </div>
      </div>
    </section>
  );
}
