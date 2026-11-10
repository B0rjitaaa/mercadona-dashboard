import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useCatalogStatus, useSummary } from "../api/queries";
import { SUPPORTED_LANGUAGES } from "../i18n";
import { useTheme, type ThemeChoice } from "../lib/theme";
import { Icon, type IconName } from "./Icon";

const LINKS: { to: string; key: string; icon: IconName }[] = [
  { to: "/", key: "nav.dashboard", icon: "home" },
  { to: "/spending", key: "nav.spending", icon: "chart" },
  { to: "/receipts", key: "nav.receipts", icon: "receipt" },
  { to: "/products", key: "nav.products", icon: "box" },
  { to: "/prices", key: "nav.prices", icon: "tag" },
  { to: "/review", key: "nav.review", icon: "inbox" },
  { to: "/settings", key: "nav.settings", icon: "settings" },
];

export function Layout() {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const summary = useSummary();
  const pending = summary.data ? summary.data.pending.needs_review + summary.data.pending.error : 0;
  const catalog = useCatalogStatus();
  const unmatched = catalog.data?.unmatched ?? 0;

  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="app">
      <div className="topbar">
        <span className="brand" style={{ padding: 0 }}>
          <span className="brand-mark">M</span>
          {t("app.title")}
        </span>
        <button className="btn-ghost" onClick={() => setOpen(true)} aria-label={t("nav.open")}>
          <Icon name="menu" size={20} />
        </button>
      </div>

      <nav className={`sidebar ${open ? "open" : ""}`} aria-label={t("nav.label")}>
        <div className="brand">
          <span className="brand-mark">M</span>
          <span style={{ flex: 1 }}>{t("app.title")}</span>
          {open && (
            <button className="btn-ghost" onClick={() => setOpen(false)} aria-label={t("nav.close")}>
              <Icon name="close" size={18} />
            </button>
          )}
        </div>
        {LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} end={link.to === "/"} className="nav-link">
            <Icon name={link.icon} />
            {t(link.key)}
            {link.to === "/receipts" && pending > 0 && (
              <span className="nav-badge" title={t("dashboard.pendingTitle")}>
                {pending}
              </span>
            )}
            {link.to === "/review" && unmatched > 0 && (
              <span className="nav-badge" style={{ background: "var(--surface-2)", color: "var(--ink-2)" }}>
                {unmatched}
              </span>
            )}
          </NavLink>
        ))}

        <div className="sidebar-footer">
          <label className="secondary" style={{ display: "grid", gap: 4, fontSize: 12 }}>
            {t("language.label")}
            <select value={i18n.resolvedLanguage} onChange={(e) => void i18n.changeLanguage(e.target.value)}>
              {SUPPORTED_LANGUAGES.map((lng) => (
                <option key={lng} value={lng}>
                  {t(`language.${lng}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="secondary" style={{ display: "grid", gap: 4, fontSize: 12 }}>
            {t("theme.label")}
            <select value={theme} onChange={(e) => setTheme(e.target.value as ThemeChoice)}>
              {(["system", "light", "dark"] as const).map((c) => (
                <option key={c} value={c}>
                  {t(`theme.${c}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </nav>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
