/** Period presets shared by every filtered page (FR-14). Dates are local YYYY-MM-DD strings. */

export const PRESETS = [
  "this_month",
  "last_month",
  "3m",
  "6m",
  "12m",
  "this_year",
  "last_year",
  "all",
  "custom",
] as const;
export type Preset = (typeof PRESETS)[number];

export interface PeriodValue {
  preset: Preset;
  /** Only for "custom" */
  from?: string;
  to?: string;
}

export interface Range {
  from?: string;
  to?: string;
}

export const DEFAULT_PERIOD: PeriodValue = { preset: "12m" };

export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function parseIso(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function monthStart(today: Date, offset: number): Date {
  return new Date(today.getFullYear(), today.getMonth() + offset, 1);
}

function monthEnd(today: Date, offset: number): Date {
  return new Date(today.getFullYear(), today.getMonth() + offset + 1, 0);
}

/** The dates a period covers. An open `to` means "until today". */
export function resolvePeriod(value: PeriodValue, today = new Date()): Range {
  switch (value.preset) {
    case "this_month":
      return { from: isoDate(monthStart(today, 0)) };
    case "last_month":
      return { from: isoDate(monthStart(today, -1)), to: isoDate(monthEnd(today, -1)) };
    case "3m":
    case "6m":
    case "12m":
      return { from: isoDate(monthStart(today, -(parseInt(value.preset, 10) - 1))) };
    case "this_year":
      return { from: `${today.getFullYear()}-01-01` };
    case "last_year":
      return { from: `${today.getFullYear() - 1}-01-01`, to: `${today.getFullYear() - 1}-12-31` };
    case "all":
      return {};
    case "custom":
      return { from: value.from || undefined, to: value.to || undefined };
  }
}

/** A single whole month as a custom period, e.g. after clicking a bar. */
export function monthPeriod(key: string): PeriodValue {
  const [y, m] = key.split("-").map(Number);
  return { preset: "custom", from: `${key}-01`, to: isoDate(new Date(y, m, 0)) };
}

/** True when the range starts and ends (an open end means today) in the same calendar month. */
export function withinOneMonth(range: Range, today = new Date()): boolean {
  if (!range.from) return false;
  const end = range.to ?? isoDate(today);
  return range.from.slice(0, 7) === end.slice(0, 7) && range.from <= end;
}

/** "YYYY-MM" when the range is exactly one calendar month. */
export function singleMonth(range: Range): string | null {
  if (!range.from || !range.to || !range.from.endsWith("-01")) return null;
  const key = range.from.slice(0, 7);
  return monthPeriod(key).to === range.to ? key : null;
}

export function parsePeriod(params: URLSearchParams): PeriodValue | null {
  const preset = params.get("period");
  if (!preset || !(PRESETS as readonly string[]).includes(preset)) return null;
  if (preset !== "custom") return { preset: preset as Preset };
  return { preset: "custom", from: params.get("from") ?? undefined, to: params.get("to") ?? undefined };
}

export function writePeriod(params: URLSearchParams, value: PeriodValue): URLSearchParams {
  const next = new URLSearchParams(params);
  next.set("period", value.preset);
  next.delete("from");
  next.delete("to");
  if (value.preset === "custom") {
    if (value.from) next.set("from", value.from);
    if (value.to) next.set("to", value.to);
  }
  return next;
}

/** Comparison presets: period A against baseline B. */
export const COMPARISONS = ["month_yoy", "month_mom", "ytd", "quarter", "custom"] as const;
export type Comparison = (typeof COMPARISONS)[number];

export interface ComparisonRanges {
  a: Required<Range>;
  b: Required<Range>;
}

function shiftYear(value: string, years: number): string {
  const d = parseIso(value);
  const target = new Date(d.getFullYear() + years, d.getMonth(), 1);
  const last = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  target.setDate(Math.min(d.getDate(), last));
  return isoDate(target);
}

export function resolveComparison(
  kind: Exclude<Comparison, "custom">,
  today = new Date(),
): ComparisonRanges {
  const now = isoDate(today);
  switch (kind) {
    case "month_yoy": {
      // This month so far vs the same days a year earlier
      const from = isoDate(monthStart(today, 0));
      return { a: { from, to: now }, b: { from: shiftYear(from, -1), to: shiftYear(now, -1) } };
    }
    case "month_mom":
      // Last full month vs the month before
      return {
        a: { from: isoDate(monthStart(today, -1)), to: isoDate(monthEnd(today, -1)) },
        b: { from: isoDate(monthStart(today, -2)), to: isoDate(monthEnd(today, -2)) },
      };
    case "ytd": {
      const from = `${today.getFullYear()}-01-01`;
      return { a: { from, to: now }, b: { from: shiftYear(from, -1), to: shiftYear(now, -1) } };
    }
    case "quarter":
      // Last 3 full months vs the 3 before
      return {
        a: { from: isoDate(monthStart(today, -3)), to: isoDate(monthEnd(today, -1)) },
        b: { from: isoDate(monthStart(today, -6)), to: isoDate(monthEnd(today, -4)) },
      };
  }
}
