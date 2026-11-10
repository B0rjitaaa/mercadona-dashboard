import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "../i18n";

export function LanguageSelector() {
  const { t, i18n } = useTranslation();
  return (
    <label>
      {t("language.label")}{" "}
      <select
        value={i18n.resolvedLanguage}
        onChange={(e) => void i18n.changeLanguage(e.target.value)}
      >
        {SUPPORTED_LANGUAGES.map((lng) => (
          <option key={lng} value={lng}>
            {t(`language.${lng}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
