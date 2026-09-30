export type InboxListLikeItem = {
  customer_name?: string | null;
  customer_email?: string | null;
};

export function minutesUntil(value?: string | null) {
  if (!value) return null;
  return Math.round((new Date(value).getTime() - Date.now()) / 60000);
}

export function formatDuration(minutes: number | null) {
  if (minutes == null) return "—";
  const abs = Math.abs(minutes);
  const label = abs < 60 ? `${abs}m` : `${Math.round(abs / 60)}h`;
  return minutes < 0 ? `${label} overdue` : `${label} left`;
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function titleFor(item: InboxListLikeItem) {
  return item.customer_name || item.customer_email || "Unknown customer";
}

export function priorityClass(priority?: string | null) {
  switch ((priority || "").toUpperCase()) {
    case "HIGH":
      return "border-red-200 bg-red-50 text-red-700";
    case "MEDIUM":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "LOW":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    default:
      return "border-slate-200 bg-slate-50 text-slate-600";
  }
}
