"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { apiJson, jsonBody } from "@/platform/api/client";

type Theme = "light" | "dark";

const KEY = "tajeran-theme";
const ENDPOINT = "/api/workspaces/current/theme";
const CHANGED = "tajeran-theme-changed";

const currentTheme = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

// The browser copy lets the page paint in the right theme before the account
// answers (see the inline script in app/layout.tsx).
function applyTheme(theme: Theme) {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // Private browsing: the choice lasts until the page is reloaded.
  }
  window.dispatchEvent(new Event(CHANGED));
}

/** Applies the theme saved on the signed-in user's account. Renders nothing. */
export function ThemeSync() {
  useEffect(() => {
    apiJson<{ theme: Theme | null }>(ENDPOINT)
      .then(({ theme }) => {
        if (theme && theme !== currentTheme()) applyTheme(theme);
      })
      .catch(() => {});
  }, []);
  return null;
}

/** Light / dark switch. Saved on the user's account and in this browser. */
export function ThemeSwitch() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const read = () => setDark(currentTheme() === "dark");
    read();
    window.addEventListener(CHANGED, read);
    return () => window.removeEventListener(CHANGED, read);
  }, []);

  const toggle = () => {
    const next: Theme = dark ? "light" : "dark";
    applyTheme(next);
    apiJson(ENDPOINT, { method: "PUT", body: jsonBody({ theme: next }) }).catch(() => {});
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="mb-1.5 ml-auto inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-control border border-border bg-surface px-2.5 py-1 text-[12.5px] font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
    >
      {dark ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
      <span className="hidden sm:inline">{dark ? "Light mode" : "Dark mode"}</span>
    </button>
  );
}
