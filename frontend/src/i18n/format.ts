import { useTranslation } from "react-i18next";

/** Locale-aware formatters (FR-12). Always use these instead of formatting by hand. */
export function useFormatters() {
  const { i18n } = useTranslation();
  const locale = i18n.resolvedLanguage ?? "en";

  return {
    currency: (value: number | string) =>
      new Intl.NumberFormat(locale, { style: "currency", currency: "EUR" }).format(Number(value)),
    number: (value: number | string, maximumFractionDigits = 3) =>
      new Intl.NumberFormat(locale, { maximumFractionDigits }).format(Number(value)),
    date: (value: string | Date) =>
      new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value)),
    dateTime: (value: string | Date) =>
      new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
      ),
  };
}
