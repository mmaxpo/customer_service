import type { ReactNode } from "react";
import { cn } from "@/platform/utils";

type Props = {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
};

export function ProductPanel({
  title,
  description,
  icon,
  action,
  children,
  className,
  contentClassName,
}: Props) {
  return (
    <section className={cn("overflow-hidden rounded-3xl border border-border bg-surface shadow-sm shadow-slate-200/70", className)}>
      {(title || description || icon || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-border p-5">
          <div className="flex min-w-0 items-start gap-3">
            {icon && (
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary text-white">
                {icon}
              </div>
            )}
            <div className="min-w-0">
              {title && <h2 className="font-bold text-foreground">{title}</h2>}
              {description && <p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p>}
            </div>
          </div>
          {action}
        </div>
      )}
      <div className={cn("p-5", contentClassName)}>{children}</div>
    </section>
  );
}
