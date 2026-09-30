"use client";

type TemplateOption = {
  slug: string;
  title: string;
  description: string;
};

type Props = {
  loadTemplateFlow: (template: string) => void;
  addStarterFlow: () => void;
};

const TEMPLATE_OPTIONS: TemplateOption[] = [
  {
    slug: "refund",
    title: "Refund Mission",
    description: "Check order, pause for approval, reply.",
  },
  {
    slug: "order-status",
    title: "Order Intelligence Mission",
    description: "Find order and tracking context.",
  },
  {
    slug: "shipping-delay",
    title: "Shipping Delay Mission",
    description: "Explain delays and escalate late packages.",
  },
  {
    slug: "escalation-router",
    title: "Escalation Decision Mission",
    description: "Route urgent messages to the right team.",
  },
];

export default function ComposerEmptyState({
  loadTemplateFlow,
  addStarterFlow,
}: Props) {
  return (
    <div className="mt-8 w-[620px] rounded-[32px] border border-white/80 bg-white/90 p-5 text-center shadow-xl shadow-tajeran-100/70 backdrop-blur">
      <div className="text-lg font-extrabold tracking-tight text-slate-950">
        Start with an AI mission
      </div>

      <div className="mt-1 text-sm text-slate-500">
        Choose a mission pattern or assemble agents, tools, decisions, memory, and outputs from the left.
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-left">
        {TEMPLATE_OPTIONS.map((option) => (
          <button
            key={option.slug}
            onClick={() => loadTemplateFlow(option.slug)}
            className="rounded-3xl border border-tajeran-100 bg-gradient-to-br from-white to-tajeran-50 p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-tajeran-100/70"
          >
            <div className="font-bold text-slate-950">{option.title}</div>
            <div className="mt-1 text-xs leading-5 text-slate-500">
              {option.description}
            </div>
          </button>
        ))}
      </div>

      <button
        onClick={addStarterFlow}
        className="mt-4 rounded-2xl bg-gradient-to-r from-tajeran-950 to-ai-950 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-tajeran-950/20"
      >
        Or create a simple mission map
      </button>
    </div>
  );
}
