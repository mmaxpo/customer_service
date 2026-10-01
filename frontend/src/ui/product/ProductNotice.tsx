import type { ReactNode } from "react";
import { cn } from "@/platform/utils";

type Variant = "default" | "success" | "warning" | "danger" | "info";

const variants: Record<Variant, string> = {
  default: "border-border bg-surface text-text-secondary",
  success: "border-shopify-100 bg-shopify-50 text-shopify-700",
  warning: "border-warn-100 bg-warn-50 text-warn-700",
  danger: "border-danger/30 bg-danger/10 text-danger",
  info: "border-ai-100 bg-ai-50 text-ai-800",
};

type Props = {
  children: ReactNode;
  variant?: Variant;
  className?: string;
};

export function ProductNotice({
  children,
  variant = "default",
  className,
}: Props) {
  return (
    <div className={cn("rounded-2xl border p-4 text-sm shadow-sm", variants[variant], className)}>
      {children}
    </div>
  );
}
