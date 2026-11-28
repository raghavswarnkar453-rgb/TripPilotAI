const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const formatINR = (n: number) => inr.format(Math.round(n));

/** "2026-12-15" -> local Date (no timezone shifting). */
export function parseDay(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

export function formatDay(iso: string, long = false): string {
  return parseDay(iso).toLocaleDateString("en-IN", {
    weekday: long ? "long" : "short",
    day: "numeric",
    month: "short",
    ...(long ? { year: "numeric" } : {}),
  });
}

export function formatDuration(minutes?: number | null): string | null {
  if (!minutes) return null;
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export const CATEGORY_LABELS: Record<string, string> = {
  transport: "Transport",
  accommodation: "Stay",
  food: "Food",
  tickets: "Activities & tickets",
  local_travel: "Local travel",
  misc: "Miscellaneous",
};

export const shortPlaceName = (displayName: string) => displayName.split(",").slice(0, 2).join(",").trim();
