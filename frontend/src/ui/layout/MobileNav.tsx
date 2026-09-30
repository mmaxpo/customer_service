"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/platform/utils";

import { isActivePath, primaryNav } from "./navigation";

const mobileHrefs = ["/app/inbox", "/app/dashboard", "/app/approvals", "/app/workflows", "/app/knowledge"];
const mobileItems = primaryNav
  .flatMap((group) => group.items)
  .filter((item) => mobileHrefs.includes(item.href));

export default function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <div className="mx-auto grid h-16 max-w-lg grid-cols-5">
        {mobileItems.map((item) => {
          const Icon = item.icon;
          const active = isActivePath(pathname, item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center justify-center gap-1 text-[11px] font-medium",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus",
                active ? "text-primary" : "text-text-secondary",
              )}
            >
              <Icon size={20} strokeWidth={1.75} aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
