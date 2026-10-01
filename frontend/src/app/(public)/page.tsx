import Link from "next/link";

import { AgentsScene } from "@/components/marketing/AgentsScene";
import { aura, display, palette, SALES_EMAIL, SUPPORT_EMAIL } from "@/components/marketing/brand";
import { HeroHeadline, SetupSteps } from "@/components/marketing/LandingMotion";
import { LiveRunDemo } from "@/components/marketing/LiveRunDemo";
import { Pricing } from "@/components/marketing/Pricing";
import { ProductTour } from "@/components/marketing/ProductTour";
import { cn } from "@/platform/utils";
import { TajeranMark } from "@/ui/brand/TajeranMark";

export const metadata = {
  title: "Tajeran.ai: AI agents that run your customer service",
  description:
    "Tajeran reads each customer message, checks the order in Shopify, follows your policy, and replies. It asks before a refund and hands over when a person should take it.",
};

const heading = "font-[family-name:var(--font-display)] font-semibold tracking-tight text-foreground";
const focusRing = "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2";
const primaryLink = cn(
  "inline-flex h-11 items-center justify-center rounded-control bg-primary px-5 text-[14px] font-semibold text-primary-foreground transition-colors hover:bg-primary-hover",
  focusRing,
);

type Mode = "On its own" | "Asks you first" | "Hands to a person";

const MODE_STYLE: Record<Mode, string> = {
  "On its own": "bg-shopify-50 text-shopify-700",
  "Asks you first": "bg-warn-50 text-warn-700",
  "Hands to a person": "bg-tajeran-50 text-tajeran-700",
};

const handled: { topic: string; does: string; mode: Mode }[] = [
  { topic: "Order status", does: "Finds the order and its tracking in Shopify, then replies with where it is.", mode: "On its own" },
  { topic: "Shipping delay", does: "Checks the carrier, explains the delay, and gives the new delivery date.", mode: "On its own" },
  { topic: "Return or exchange", does: "Answers from your help articles and tells the customer what to do next.", mode: "On its own" },
  { topic: "General question", does: "Answers from your help articles, in your tone.", mode: "On its own" },
  { topic: "Damaged item", does: "Checks the order against your policy and prepares the refund.", mode: "Asks you first" },
  { topic: "Refund", does: "Works out what is owed and waits for a yes before any money moves.", mode: "Asks you first" },
  { topic: "Cancellation", does: "Checks whether the order has shipped and prepares the cancellation.", mode: "Asks you first" },
  { topic: "Billing", does: "Collects the details and passes the conversation on with a summary.", mode: "Hands to a person" },
];

const control = [
  {
    title: "It asks before money moves",
    text: "Refunds and cancellations pause for approval. You see the order, the policy it used, and the amount, then approve or decline.",
  },
  {
    title: "It steps back when you step in",
    text: "Once someone on your team replies in a conversation, Tajeran stops answering there. Customers never get two voices at once.",
  },
  {
    title: "You can read every run",
    text: "Each conversation keeps the steps Tajeran took and what it found. Edit a workflow, test it, and roll back to an earlier version.",
  },
];

const setup = [
  { title: "Connect your Shopify store", text: "Tajeran reads orders, customers, fulfillment, and tracking so it can answer with real details." },
  { title: "Add your help articles", text: "Returns, shipping, and product answers. Replies are written from these, not guessed." },
  { title: "Choose what needs approval", text: "Decide which actions run on their own and which wait for a person on your team." },
  { title: "Turn on your channels", text: "Email, the chat widget on your store, Instagram, Messenger, and WhatsApp." },
];

export default function PublicHomePage() {
  return (
    <main className={cn(display.variable, "min-h-screen overflow-x-clip bg-background text-foreground")} style={palette}>
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className={cn("flex items-center gap-2 rounded-control text-[15px] font-semibold", focusRing)}>
          <TajeranMark size={26} />
          Tajeran.ai
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1 whitespace-nowrap text-[14px] sm:gap-2">
          <a href="#agents" className={cn("hidden rounded-control px-3 py-2 text-text-secondary hover:text-foreground md:block", focusRing)}>
            How the agents work
          </a>
          <a href="#handles" className={cn("hidden rounded-control px-3 py-2 text-text-secondary hover:text-foreground lg:block", focusRing)}>
            What it handles
          </a>
          <a href="#pricing" className={cn("hidden rounded-control px-3 py-2 text-text-secondary hover:text-foreground sm:block", focusRing)}>
            Pricing
          </a>
          <Link href="/contact" className={cn("hidden rounded-control px-3 py-2 text-text-secondary hover:text-foreground md:block", focusRing)}>
            Contact us
          </Link>
          <Link href="/login" className={cn("rounded-control px-3 py-2 font-medium text-foreground hover:bg-muted", focusRing)}>
            Log in
          </Link>
          <Link href="/signup" className={cn(primaryLink, "h-9 px-4")}>
            Create a workspace
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-5 pb-20 pt-10 sm:px-8 sm:pt-16">
        <div className="max-w-3xl">
          <HeroHeadline
            text="A team of AI agents that runs your customer service."
            className={cn(heading, "text-[40px] leading-[1.05] sm:text-[64px]")}
          />
          <p className="mt-5 max-w-2xl text-[17px] leading-7 text-text-secondary">
            They read each message, look up the order in Shopify, follow your policy, and reply. They ask you before a
            refund and hand over when a person should take it.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href="/signup" className={primaryLink}>
              Create a workspace
            </Link>
            <a href="#handles" className={cn("rounded-control px-3 py-2.5 text-[14px] font-semibold text-foreground hover:bg-muted", focusRing)}>
              See what it handles
            </a>
          </div>
        </div>

        <div className="relative isolate mt-12">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-6 bottom-10 -z-10 opacity-30 blur-3xl" style={aura} />
          <LiveRunDemo />
        </div>
      </section>

      <section id="agents" className="border-y border-border bg-surface">
        <AgentsScene />
      </section>

      <section id="product" className="mx-auto max-w-6xl px-5 py-12 sm:px-8 lg:py-0">
        <ProductTour />
      </section>

      <section id="handles" className="border-y border-border bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <div className="max-w-2xl">
            <h2 className={cn(heading, "text-[30px] leading-tight sm:text-[38px]")}>What it handles, and when it stops to ask</h2>
            <p className="mt-3 text-[16px] leading-7 text-text-secondary">
              Tajeran sorts every conversation by topic. Each topic runs a workflow you can open, read, and change.
            </p>
          </div>

          <ul className="mt-10 divide-y divide-border border-y border-border">
            {handled.map((row) => (
              <li key={row.topic} className="grid gap-x-6 gap-y-1.5 py-4 sm:grid-cols-[180px_1fr_auto] sm:items-center">
                <span className="text-[15px] font-semibold text-foreground">{row.topic}</span>
                <span className="text-[14.5px] leading-6 text-text-secondary">{row.does}</span>
                <span className={cn("w-fit rounded-full px-2.5 py-1 text-[12.5px] font-medium", MODE_STYLE[row.mode])}>{row.mode}</span>
              </li>
            ))}
          </ul>

          <p className="mt-6 text-[14.5px] leading-6 text-text-secondary">
            It answers wherever customers write: email, the chat widget on your store, Instagram, Messenger, and WhatsApp.
          </p>
        </div>
      </section>

      <section id="control" className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <h2 className={cn(heading, "max-w-2xl text-[30px] leading-tight sm:text-[38px]")}>You decide where it stops</h2>
        <div className="mt-10 grid gap-10 md:grid-cols-3 md:gap-8">
          {control.map((item) => (
            <div key={item.title} className="border-t-2 border-foreground pt-4">
              <h3 className="text-[16px] font-semibold text-foreground">{item.title}</h3>
              <p className="mt-2 text-[14.5px] leading-6 text-text-secondary">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-border bg-surface">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
          <h2 className={cn(heading, "max-w-2xl text-[30px] leading-tight sm:text-[38px]")}>Four steps to your first resolved conversation</h2>
          <div className="mt-12">
            <SetupSteps steps={setup} />
          </div>
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-6xl px-5 py-20 sm:px-8">
        <div className="max-w-2xl">
          <h2 className={cn(heading, "text-[30px] leading-tight sm:text-[38px]")}>Pricing</h2>
          <p className="mt-3 text-[16px] leading-7 text-text-secondary">
            Every plan starts with a trial. Billing runs through Shopify, and you can change plan at any time.
          </p>
        </div>
        <div className="mt-10">
          <Pricing />
        </div>
      </section>

      <section id="contact" className="border-y border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-5 py-16 sm:px-8 md:flex-row md:items-center">
          <div className="max-w-xl">
            <h2 className={cn(heading, "text-[30px] leading-tight sm:text-[38px]")}>Contact us</h2>
            <p className="mt-3 text-[16px] leading-7 text-text-secondary">
              Thinking about a plan, or want to see how the agents would work with your store? Write to sales. Already
              a customer? Support will help.
            </p>
            <Link href="/contact" className={cn(primaryLink, "mt-6")}>
              Send us a message
            </Link>
          </div>
          <dl className="shrink-0 space-y-4 text-[15px]">
            {[
              ["Plans and Enterprise", SALES_EMAIL],
              ["Help with your workspace", SUPPORT_EMAIL],
            ].map(([label, email]) => (
              <div key={email}>
                <dt className="text-[13.5px] text-text-secondary">{label}</dt>
                <dd>
                  <a href={`mailto:${email}`} className={cn("rounded-control font-semibold text-primary hover:underline", focusRing)}>
                    {email}
                  </a>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="relative isolate mx-auto max-w-6xl px-5 py-24 text-center sm:px-8 sm:py-32">
        <div aria-hidden className="pointer-events-none absolute inset-x-[10%] top-1/3 -z-10 h-40 opacity-25 blur-3xl" style={aura} />
        <h2 className={cn(heading, "mx-auto max-w-3xl text-[34px] leading-[1.08] sm:text-[52px]")}>
          Put the agents to work on your next conversation.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-[16px] leading-7 text-text-secondary">
          Create a workspace, connect Shopify, and add your help articles. They start from there.
        </p>
        <Link href="/signup" className={cn(primaryLink, "mt-8")}>
          Create a workspace
        </Link>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-8 text-[13px] text-text-secondary sm:px-8">
        <span className="flex items-center gap-2">
          <TajeranMark size={18} /> Tajeran.ai, customer service for Shopify stores
        </span>
        <Link href="/login" className={cn("rounded-control hover:text-foreground", focusRing)}>
          Log in
        </Link>
      </footer>
    </main>
  );
}
