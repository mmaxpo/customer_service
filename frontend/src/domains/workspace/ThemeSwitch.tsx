"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

const KEY = "tajeran-theme";

/** Light / dark switch. The choice is kept in this browser. */
export function ThemeSwitch() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    if (next) document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem(KEY, next ? "dark" : "light");
    } catch {
      // Private browsing: the choice lasts until the page is reloaded.
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="mb-1.5 ml-auto inline-flex shrink-0 items-center whitespace-nowrap gap-1.5 rounded-control border border-border bg-surface px-2.5 py-1 text-[12.5px] font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
    >
      {dark ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
      <span className="hidden sm:inline">{dark ? "Light mode" : "Dark mode"}</span>
    </button>
  );
}
