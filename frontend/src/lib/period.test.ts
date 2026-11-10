import { describe, expect, it } from "vitest";
import { monthPeriod, parsePeriod, resolveComparison, resolvePeriod, singleMonth, withinOneMonth, writePeriod } from "./period";

const today = new Date(2026, 10, 10); // 10 Nov 2026

describe("resolvePeriod", () => {
  it("resolves presets relative to today", () => {
    expect(resolvePeriod({ preset: "this_month" }, today)).toEqual({ from: "2026-11-01" });
    expect(resolvePeriod({ preset: "last_month" }, today)).toEqual({ from: "2026-10-01", to: "2026-10-31" });
    expect(resolvePeriod({ preset: "3m" }, today)).toEqual({ from: "2026-09-01" });
    expect(resolvePeriod({ preset: "12m" }, today)).toEqual({ from: "2025-12-01" });
    expect(resolvePeriod({ preset: "this_year" }, today)).toEqual({ from: "2026-01-01" });
    expect(resolvePeriod({ preset: "last_year" }, today)).toEqual({ from: "2025-01-01", to: "2025-12-31" });
    expect(resolvePeriod({ preset: "all" }, today)).toEqual({});
  });

  it("handles January for last month", () => {
    expect(resolvePeriod({ preset: "last_month" }, new Date(2026, 0, 15))).toEqual({
      from: "2025-12-01",
      to: "2025-12-31",
    });
  });

  it("keeps custom ranges and ignores empty ends", () => {
    expect(resolvePeriod({ preset: "custom", from: "2026-02-03", to: "" }, today)).toEqual({ from: "2026-02-03" });
  });
});

describe("month helpers", () => {
  it("builds and detects single months", () => {
    expect(monthPeriod("2024-02")).toEqual({ preset: "custom", from: "2024-02-01", to: "2024-02-29" });
    expect(singleMonth({ from: "2024-02-01", to: "2024-02-29" })).toBe("2024-02");
    expect(singleMonth({ from: "2024-02-01", to: "2024-03-31" })).toBeNull();
    expect(singleMonth({ from: "2024-02-01" })).toBeNull();
  });

  it("detects ranges inside one month", () => {
    const today = new Date(2026, 10, 10);
    expect(withinOneMonth({ from: "2026-11-01" }, today)).toBe(true);
    expect(withinOneMonth({ from: "2026-10-01", to: "2026-10-31" }, today)).toBe(true);
    expect(withinOneMonth({ from: "2026-10-01" }, today)).toBe(false);
    expect(withinOneMonth({}, today)).toBe(false);
  });
});

describe("URL round trip", () => {
  it("writes and reads periods", () => {
    const params = writePeriod(new URLSearchParams("x=1&from=old"), { preset: "custom", from: "2026-01-01", to: "2026-02-01" });
    expect(params.get("x")).toBe("1");
    expect(parsePeriod(params)).toEqual({ preset: "custom", from: "2026-01-01", to: "2026-02-01" });
    expect(parsePeriod(writePeriod(params, { preset: "6m" }))).toEqual({ preset: "6m" });
    expect(parsePeriod(new URLSearchParams("period=bogus"))).toBeNull();
  });
});

describe("resolveComparison", () => {
  it("compares with the same days of last year", () => {
    expect(resolveComparison("month_yoy", today)).toEqual({
      a: { from: "2026-11-01", to: "2026-11-10" },
      b: { from: "2025-11-01", to: "2025-11-10" },
    });
    expect(resolveComparison("ytd", new Date(2028, 1, 29))).toEqual({
      a: { from: "2028-01-01", to: "2028-02-29" },
      b: { from: "2027-01-01", to: "2027-02-28" },
    });
  });

  it("compares full months", () => {
    expect(resolveComparison("month_mom", today)).toEqual({
      a: { from: "2026-10-01", to: "2026-10-31" },
      b: { from: "2026-09-01", to: "2026-09-30" },
    });
    expect(resolveComparison("quarter", today)).toEqual({
      a: { from: "2026-08-01", to: "2026-10-31" },
      b: { from: "2026-05-01", to: "2026-07-31" },
    });
  });
});
