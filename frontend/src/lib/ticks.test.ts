import { describe, expect, it } from "vitest";
import { niceTicks } from "./ticks";

describe("niceTicks", () => {
  it("rounds money axes to clean steps", () => {
    expect(niceTicks(0, 370)).toEqual([0, 100, 200, 300, 400]);
    expect(niceTicks(0, 18.15)).toEqual([0, 5, 10, 15, 20]);
  });
  it("handles price ranges and flat series", () => {
    expect(niceTicks(1.4, 1.65)).toEqual([1.4, 1.5, 1.6, 1.7]);
    expect(niceTicks(4, 4)).toEqual([3.6, 3.8, 4, 4.2, 4.4]);
  });
});
