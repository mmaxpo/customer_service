import * as React from "react";
import { cn } from "@/platform/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-control border border-border bg-surface px-3 text-sm text-foreground outline-none transition placeholder:text-text-secondary focus:border-focus focus:ring-2 focus:ring-focus/30 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
