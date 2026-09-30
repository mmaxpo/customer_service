import * as React from "react";
import { cn } from "@/platform/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-24 w-full rounded-control border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-text-secondary focus:border-focus focus:ring-2 focus:ring-focus/30 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);

Textarea.displayName = "Textarea";
