import { useSearchParams } from "react-router-dom";
import type { FilterQuery } from "../api/queries";
import { DEFAULT_PERIOD, PRESETS, parsePeriod, resolvePeriod, writePeriod, type PeriodValue, type Range } from "./period";

/**
 * Period and section filters shared by every analytics page (FR-14).
 *
 * The URL wins (links and reloads keep the view); otherwise the last choice, remembered
 * in this browser, so moving between pages keeps the same filters.
 */
const PERIOD_KEY = "filters.period";
const SECTIONS_KEY = "filters.sections";

function load<T>(key: string, valid: (v: unknown) => v is T, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    const value: unknown = raw ? JSON.parse(raw) : null;
    return valid(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable: filters just won't be remembered */
  }
}

const isPeriod = (v: unknown): v is PeriodValue =>
  typeof v === "object" && v !== null && (PRESETS as readonly string[]).includes((v as PeriodValue).preset);

const isSections = (v: unknown): v is string[] => Array.isArray(v) && v.every((s) => typeof s === "string");

export interface Filters {
  period: PeriodValue;
  range: Range;
  /** Section ids as strings, plus "none" for lines without a category */
  sections: string[];
  query: FilterQuery;
  setPeriod: (value: PeriodValue) => void;
  setSections: (value: string[]) => void;
}

export function useFilters(): Filters {
  const [params, setParams] = useSearchParams();
  const period = parsePeriod(params) ?? load(PERIOD_KEY, isPeriod, DEFAULT_PERIOD);
  const fromUrl = params.get("sections");
  const sections =
    fromUrl !== null ? fromUrl.split(",").filter(Boolean) : load(SECTIONS_KEY, isSections, [] as string[]);
  const range = resolvePeriod(period);

  return {
    period,
    range,
    sections,
    query: { ...range, sections: sections.length ? sections.join(",") : undefined },
    setPeriod: (value) => {
      save(PERIOD_KEY, value);
      setParams((prev) => writePeriod(prev, value), { replace: true });
    },
    setSections: (value) => {
      save(SECTIONS_KEY, value);
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("sections", value.join(","));
          return next;
        },
        { replace: true },
      );
    },
  };
}
