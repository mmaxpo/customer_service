import AppHeader from "./AppHeader";
import AppMain from "./AppMain";
import AppRail from "./AppRail";
import MobileNav from "./MobileNav";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh bg-background text-foreground">
      <AppRail />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <AppMain>{children}</AppMain>
        <MobileNav />
      </div>
    </div>
  );
}
