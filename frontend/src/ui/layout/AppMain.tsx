"use client";

import { usePathname } from "next/navigation";

import { fullBleedRoutes, isActivePath } from "./navigation";

export default function AppMain({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const fullBleed = fullBleedRoutes.some((route) => isActivePath(pathname, route));

  if (fullBleed) {
    return (
      <main className="flex min-h-0 flex-1 flex-col overflow-hidden pb-16 lg:pb-0">
        {children}
      </main>
    );
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto p-3 pb-24 sm:p-4 sm:pb-24 lg:p-6">
      {children}
    </main>
  );
}
