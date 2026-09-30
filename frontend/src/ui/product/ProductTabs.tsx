import { cn } from "@/platform/utils";

type Tab<T extends string> = {
  value: T;
  label: string;
};

type Props<T extends string> = {
  tabs: Tab<T>[];
  value: T;
  onChange: (value: T) => void;
  columns?: number;
};

export function ProductTabs<T extends string>({
  tabs,
  value,
  onChange,
  columns,
}: Props<T>) {
  return (
    <div className="rounded-2xl border border-tajeran-100 bg-white/90 p-1 shadow-sm shadow-tajeran-100/60 backdrop-blur">
      <div
        className="grid gap-1"
        style={{ gridTemplateColumns: `repeat(${columns ?? tabs.length}, minmax(0, 1fr))` }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => onChange(tab.value)}
            className={cn(
              "rounded-xl px-2 py-2 text-xs font-semibold transition",
              value === tab.value
                ? "bg-tajeran-700 text-white shadow-md shadow-tajeran-500/20"
                : "text-slate-500 hover:bg-tajeran-50 hover:text-tajeran-700",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
