import type { ReactNode } from "react";
import { cn } from "@/platform/utils";

type Variant = "default" | "success" | "warning" | "danger" | "info";

const variants: Record<Variant, string> = {
  default: "border-slate-200 bg-white text-slate-700",
  success: "border-emerald-100 bg-emerald-50 text-emerald-800",
  warning: "border-amber-100 bg-amber-50 text-amber-800",
  danger: "border-red-100 bg-red-50 text-red-700",
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
