"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Bot, Cable, CreditCard, Inbox, Layers3, Settings, UserCog, Workflow, type LucideIcon } from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const appNav = [
  { href: "/app/dashboard", label: "Desk", icon: BarChart3 },
  { href: "/app/inbox", label: "Inbox", icon: Inbox },
  { href: "/app/workflows", label: "Automations", icon: Workflow },
  { href: "/app/knowledge", label: "Knowledge", icon: Layers3 },
];

const managementNav = [
  { href: "/app/channels", label: "Channels", icon: Cable },
  { href: "/app/agents", label: "Team", icon: UserCog },
  { href: "/app/operations", label: "Operations", icon: Activity },
  { href: "/app/settings", label: "Settings", icon: Settings },
  { href: "/app/billing", label: "Plan & billing", icon: CreditCard },
];

function NavigationItems({ items, pathname }: { items: NavItem[]; pathname: string }) {
  return items.map((item) => {
    const Icon = item.icon;
    const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

    return (
      <Link
        key={item.href}
        href={item.href}
        className={[
          "group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition",
          active ? "bg-white text-tajeran-950 shadow-lg shadow-black/20" : "text-slate-300 hover:bg-white/10 hover:text-white",
        ].join(" ")}
      >
        <span className={[
          "flex h-8 w-8 items-center justify-center rounded-xl transition",
          active ? "bg-tajeran-100 text-tajeran-700" : "bg-white/5 text-slate-400 group-hover:bg-white/10 group-hover:text-tajeran-100",
        ].join(" ")}>
          <Icon size={17} />
        </span>
        {item.label}
      </Link>
    );
  });
}

export default function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/10 bg-tajeran-950 text-white shadow-2xl shadow-tajeran-950/30 lg:flex">
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-tajeran-500 via-ai-700 to-shopify-700 text-white shadow-lg shadow-tajeran-500/30">
          <Bot size={19} />
        </div>
        <div>
          <div className="font-semibold tracking-tight text-white">Tajeran.ai</div>
          <div className="text-xs font-medium text-tajeran-100">Support OS</div>
        </div>
      </div>

      <div className="px-3 pt-5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Workspace
      </div>

      <nav className="flex flex-1 flex-col gap-1.5 p-3">
        <NavigationItems items={appNav} pathname={pathname} />
        <div className="mt-5 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Manage</div>
        <NavigationItems items={managementNav} pathname={pathname} />
      </nav>

      <div className="m-3 rounded-2xl border border-white/10 bg-white/[0.06] p-4">
        <div className="text-xs font-semibold text-white">Customer workspace</div>
        <div className="mt-1 text-xs leading-5 text-slate-400">
          Shopify inbox, AI replies, workflows, and routing.
        </div>
      </div>
    </aside>
  );
}
