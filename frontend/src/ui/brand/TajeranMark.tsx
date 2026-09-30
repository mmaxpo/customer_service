import { cn } from "@/platform/utils";

type Props = {
  size?: number;
  variant?: "brand" | "actor";
  className?: string;
  title?: string;
};

// One mark for Tajeran everywhere: ink for the brand, violet when it marks
// something Tajeran (the AI agent) did.
export function TajeranMark({ size = 20, variant = "brand", className, title }: Props) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-control text-white",
        variant === "brand" ? "bg-foreground" : "bg-ai-accent",
        className,
      )}
      style={{ width: size, height: size }}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <svg viewBox="0 0 20 20" width={size * 0.7} height={size * 0.7} fill="currentColor" aria-hidden>
        <path d="M3.5 4.5h11v3h-4v8.5h-3V7.5h-4z" />
        <circle cx="15.25" cy="14.25" r="1.9" />
      </svg>
    </span>
  );
}
