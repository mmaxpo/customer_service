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
