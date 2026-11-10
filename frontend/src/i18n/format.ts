import { useTranslation } from "react-i18next";
import type { Unit } from "../api/types";

/** Locale-aware formatters (FR-12). Always use these instead of formatting by hand. */
export function useFormatters() {
  const { i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "en";

  const currencyFmt = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" });
  const compactFmt = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const wholeFmt = new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  });

  const monthDate = (key: string) => {
    const [y, m] = key.split("-").map(Number);
    return new Date(y, m - 1, 1);
  };

  return {
    locale,
    currency: (value: number | string | null | undefined) =>
      value === null || value === undefined ? "—" : currencyFmt.format(Number(value)),
    /** Axis ticks: whole euros under 10,000, compact above. */
    currencyAxis: (value: number) =>
      Math.abs(value) >= 10000 ? compactFmt.format(value) : wholeFmt.format(value),
    number: (value: number | string, maximumFractionDigits = 3) =>
      new Intl.NumberFormat(locale, { maximumFractionDigits }).format(Number(value)),
    percent: (value: number | string, signed = true) =>
      new Intl.NumberFormat(locale, {
        style: "percent",
        maximumFractionDigits: 1,
        signDisplay: signed ? "exceptZero" : "auto",
      }).format(Number(value) / 100),
    quantity: (value: string | number, unit: Unit) =>
      unit === "kg"
        ? `${new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(Number(value))} kg`
        : new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(Number(value)),
    date: (value: string | Date | null | undefined) =>
      value ? new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value)) : "—",
    dateTime: (value: string | Date | null | undefined) =>
      value
        ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
            new Date(value),
          )
        : "—",
    /** "2026-11" -> "nov 26" */
    monthShort: (key: string) =>
      new Intl.DateTimeFormat(locale, { month: "short", year: "2-digit" }).format(monthDate(key)),
    /** "2026-11" -> "Noviembre de 2026" (first letter only, as a heading) */
    monthLong: (key: string) => {
      const text = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(monthDate(key));
      return text.charAt(0).toLocaleUpperCase(locale) + text.slice(1);
    },
  };
}

export type Formatters = ReturnType<typeof useFormatters>;

/** First and last day of a "YYYY-MM" month, as YYYY-MM-DD. */
export function monthRange(key: string): { from: string; to: string } {
  const [y, m] = key.split("-").map(Number);
  const last = new Date(y, m, 0).getDate();
  return { from: `${key}-01`, to: `${key}-${String(last).padStart(2, "0")}` };
}

export function currentMonthKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}
