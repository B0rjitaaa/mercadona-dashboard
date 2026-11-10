import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LanguageSelector } from "./LanguageSelector";

const links = [
  { to: "/", key: "nav.dashboard" },
  { to: "/spending", key: "nav.spending" },
  { to: "/receipts", key: "nav.receipts" },
  { to: "/products", key: "nav.products" },
  { to: "/review", key: "nav.review" },
  { to: "/settings", key: "nav.settings" },
] as const;

export function Layout() {
  const { t } = useTranslation();
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <nav style={{ width: 220, padding: 16, borderRight: "1px solid #ddd" }}>
        <h3>{t("app.title")}</h3>
        {links.map((l) => (
          <div key={l.to} style={{ margin: "8px 0" }}>
            <NavLink to={l.to} end>
              {t(l.key)}
            </NavLink>
          </div>
        ))}
        <div style={{ marginTop: 24 }}>
          <LanguageSelector />
        </div>
      </nav>
      <main style={{ flex: 1, padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
