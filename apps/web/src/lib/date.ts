// Exported so callers with an existing Date (or a timestamp to convert, e.g. ToneGameTrendCard
// turning a played_at datetime into a calendar-day bucket) can reuse this instead of
// re-deriving the same local-date formatting.
export function toLocalIsoDate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** The user's local calendar date, as yyyy-mm-dd. Never use the server's UTC date for
 * "today" — see ARCHITECTURE.md / CHANGELOG.md for why that produces off-by-one days. */
export function todayLocalDate(): string {
  return toLocalIsoDate(new Date());
}

export function daysAgoLocalDate(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return toLocalIsoDate(d);
}

export function lastNDates(n: number): string[] {
  const dates: string[] = [];
  for (let i = n - 1; i >= 0; i--) {
    dates.push(daysAgoLocalDate(i));
  }
  return dates;
}
