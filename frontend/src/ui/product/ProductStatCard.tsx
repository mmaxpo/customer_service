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
    <div className={cn("rounded-2xl border border-slate-200 bg-white p-5 shadow-sm", className)}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-sm text-slate-500">{label}</div>
          <div className="mt-1 text-2xl font-bold text-slate-950">{value}</div>
        </div>
        {Icon && <Icon className="text-slate-400" size={22} />}
      </div>
      {description && <p className="mt-3 text-sm leading-6 text-slate-500">{description}</p>}
    </div>
  );
}
