import { useEffect, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
const KEY = "theme";
const EVENT = "themechange";

function read(): ThemeChoice {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(choice: ThemeChoice = read()) {
  if (choice === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = choice;
}

export function useTheme(): [ThemeChoice, (c: ThemeChoice) => void] {
  const [choice, setChoice] = useState<ThemeChoice>(read);
  const update = (c: ThemeChoice) => {
    try {
      if (c === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, c);
    } catch {
      /* storage unavailable: theme just won't persist */
    }
    applyTheme(c);
    setChoice(c);
    window.dispatchEvent(new Event(EVENT));
  };
  return [choice, update];
}

/** Resolved CSS custom properties, re-read when the theme or OS scheme changes. */
export function useCssVars<T extends string>(names: readonly T[]): Record<T, string> {
  const resolve = () => {
    const style = getComputedStyle(document.documentElement);
    return Object.fromEntries(names.map((n) => [n, style.getPropertyValue(`--${n}`).trim()])) as Record<
      T,
      string
    >;
  };
  const [vars, setVars] = useState(resolve);
  useEffect(() => {
    const refresh = () => setVars(resolve());
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", refresh);
    window.addEventListener(EVENT, refresh);
    return () => {
      media.removeEventListener("change", refresh);
      window.removeEventListener(EVENT, refresh);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return vars;
}
