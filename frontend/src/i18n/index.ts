import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import es from "./locales/es.json";

export const SUPPORTED_LANGUAGES = ["es", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, es: { translation: es } },
    supportedLngs: SUPPORTED_LANGUAGES,
    fallbackLng: "en",
    nonExplicitSupportedLngs: true,
    interpolation: { escapeValue: false },
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
  });

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

export default i18n;
