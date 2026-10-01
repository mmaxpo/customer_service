import {
  Activity,
  BookOpen,
  ChartColumn,
  CreditCard,
  Inbox,
  Route,
  Settings,
  Stamp,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: "approvals" | "waiting";
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

// Supervise items point at the closest existing real pages until they are redesigned.
export const primaryNav: NavGroup[] = [
  {
    label: "Handle",
    items: [
      { href: "/app/inbox", label: "Inbox", icon: Inbox },
      { href: "/app/approvals", label: "Approvals", icon: Stamp, badge: "approvals" },
    ],
  },
  {
    label: "Supervise",
    items: [
      { href: "/app/live", label: "Live", icon: Activity, badge: "waiting" },
      { href: "/app/dashboard", label: "Desk", icon: ChartColumn },
    ],
  },
  {
    label: "Improve",
    items: [
      { href: "/app/workflows", label: "Automations", icon: Workflow },
      { href: "/app/knowledge", label: "Knowledge", icon: BookOpen },
      { href: "/app/routing", label: "Routing & teams", icon: Route },
    ],
  },
];

export const configurationNav: NavItem[] = [
  { href: "/app/settings", label: "Settings", icon: Settings },
  { href: "/app/billing", label: "Billing", icon: CreditCard },
];

export function isActivePath(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

// Routes that render their own full-height workspace instead of a padded page.
export const fullBleedRoutes = ["/app/inbox", "/app/approvals", "/app/workflows/runs", "/app/workflows/proposals", "/app/workflows/edit"];
