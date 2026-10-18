// API timestamps are UTC (ISO-8601); the UI shows JST as YYYY-MM-DD HH:mm (ui-design §8).
const parts = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const map = Object.fromEntries(parts.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
}

export function formatCount(n: number): string {
  return `${n.toLocaleString("ja-JP")} 件`;
}
