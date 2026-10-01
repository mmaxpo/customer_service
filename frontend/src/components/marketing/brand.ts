import type { CSSProperties } from "react";
import { Bricolage_Grotesque } from "next/font/google";

// Shared by the public pages (landing, log in, sign up) only; the app keeps
// its own quieter tokens.
export const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });

export const palette = {
  "--color-primary": "#5B3DF5",
  "--color-primary-hover": "#4A2FE0",
  "--color-focus": "#5B3DF5",
} as CSSProperties;

// One soft aura built from the agents' colours.
export const aura: CSSProperties = { background: "linear-gradient(100deg, #7A4DFF, #2F6BFF 35%, #E0349A 65%, #00A37A)" };

// TODO: make sure both mailboxes exist before launch.
export const SALES_EMAIL = "sales@tajeran.ai";
export const SUPPORT_EMAIL = "support@tajeran.ai";
