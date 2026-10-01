import type { LucideIcon } from "lucide-react";
import { cn } from "@/platform/utils";

type Props = {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  description?: string;
  className?: string;
};

export function ProductStatCard({
  label,
  value,
  icon: Icon,
  description,
  className,
}: Props) {
  return (
    <div className={cn("rounded-2xl border border-border bg-surface p-5 shadow-sm", className)}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm text-text-secondary">{label}</div>
          <div className="mt-1 text-2xl font-bold text-foreground">{value}</div>
        </div>
        {Icon && <Icon className="text-text-secondary" size={22} />}
      </div>
      {description && <p className="mt-3 text-sm leading-6 text-text-secondary">{description}</p>}
    </div>
  );
}
