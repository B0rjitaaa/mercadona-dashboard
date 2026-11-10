import { useEffect, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useSections } from "../../api/queries";
import { useFormatters } from "../../i18n/format";
import type { Filters } from "../../lib/filters";
import { PRESETS, isoDate, resolvePeriod, type PeriodValue, type Preset, type Range } from "../../lib/period";

/** "1 dic 2025 – hoy" */
export function useRangeLabel() {
  const { t } = useTranslation();
  const f = useFormatters();
  return (range: Range) => {
    if (!range.from && !range.to) return t("filters.allTime");
    const from = range.from ? f.date(`${range.from}T00:00:00`) : t("filters.start");
    const to = range.to ? f.date(`${range.to}T00:00:00`) : t("filters.today");
    return `${from} – ${to}`;
  };
}

export function PeriodPicker({
  value,
  onChange,
  presets = PRESETS,
  label,
}: {
  value: PeriodValue;
  onChange: (value: PeriodValue) => void;
  presets?: readonly Preset[];
  label?: string;
}) {
  const { t } = useTranslation();
  const rangeLabel = useRangeLabel();
  const range = resolvePeriod(value);

  const choose = (preset: Preset) => {
    if (preset !== "custom") return onChange({ preset });
    // Start the custom range from what was on screen
    onChange({ preset, from: range.from ?? "", to: range.to ?? isoDate(new Date()) });
  };

  return (
    <div className="filters">
      <label className="filters secondary">
        {label ?? t("filters.period")}
        <select value={value.preset} onChange={(e) => choose(e.target.value as Preset)}>
          {presets.map((p) => (
            <option key={p} value={p}>
              {t(`filters.presets.${p}`)}
            </option>
          ))}
        </select>
      </label>
      {value.preset === "custom" ? (
        <>
          <input
            type="date"
            aria-label={t("filters.from")}
            value={value.from ?? ""}
            max={value.to || undefined}
            onChange={(e) => onChange({ ...value, from: e.target.value })}
          />
          <span className="muted">–</span>
          <input
            type="date"
            aria-label={t("filters.to")}
            value={value.to ?? ""}
            min={value.from || undefined}
            onChange={(e) => onChange({ ...value, to: e.target.value })}
          />
        </>
      ) : (
        <span className="muted" style={{ fontSize: 13 }}>{rangeLabel(range)}</span>
      )}
    </div>
  );
}

/** Multi-select of catalogue sections, in a dropdown. */
export function SectionPicker({ value, onChange }: { value: string[]; onChange: (value: string[]) => void }) {
  const { t } = useTranslation();
  const sections = useSections();
  const ref = useRef<HTMLDetailsElement>(null);

  // Close when clicking outside or pressing Escape
  useEffect(() => {
    const close = (e: Event) => {
      const el = ref.current;
      if (!el?.open) return;
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !el.contains(e.target as Node)) el.open = false;
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, []);

  const options = (sections.data?.sections ?? []).map((s) => ({
    key: s.id === null ? "none" : String(s.id),
    name: s.section ?? t("filters.uncategorised"),
  }));
  const names = new Map(options.map((o) => [o.key, o.name]));
  const toggle = (key: string) =>
    onChange(value.includes(key) ? value.filter((v) => v !== key) : [...value, key]);

  const summary =
    value.length === 0
      ? t("filters.allSections")
      : value.length === 1
        ? (names.get(value[0]) ?? t("filters.sectionsCount", { count: 1 }))
        : t("filters.sectionsCount", { count: value.length });

  return (
    <details className="dropdown" ref={ref}>
      <summary className={value.length ? "active" : ""} aria-label={t("filters.sections")}>
        {summary}
      </summary>
      <div className="dropdown-panel" role="group" aria-label={t("filters.sections")}>
        {options.map((o) => (
          <label key={o.key} className="check">
            <input type="checkbox" checked={value.includes(o.key)} onChange={() => toggle(o.key)} />
            <span>{o.name}</span>
          </label>
        ))}
        {value.length > 0 && (
          <button className="btn-ghost" onClick={() => onChange([])}>
            {t("filters.clear")}
          </button>
        )}
      </div>
    </details>
  );
}

/** One row of filters above the charts. */
export function FilterBar({
  filters,
  sections = true,
  children,
}: {
  filters: Filters;
  sections?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="filter-bar">
      <PeriodPicker value={filters.period} onChange={filters.setPeriod} />
      {sections && <SectionPicker value={filters.sections} onChange={filters.setSections} />}
      {children}
    </div>
  );
}
