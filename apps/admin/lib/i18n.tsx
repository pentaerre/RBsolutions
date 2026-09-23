"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { LOCALE_COOKIE, parseLocale, type Locale } from "./locale";

export type { Locale };

type Messages = Record<string, string>;

type I18nValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

export function readLocale(fallback: Locale = "en"): Locale {
  if (typeof document !== "undefined") {
    const cookie = document.cookie.match(new RegExp(`(?:^|; )${LOCALE_COOKIE}=(en|es)`));
    if (cookie) {
      return parseLocale(cookie[1]);
    }
    try {
      const stored = localStorage.getItem(LOCALE_COOKIE);
      if (stored === "en" || stored === "es") {
        return stored;
      }
    } catch {
      /* ignore */
    }
    if (navigator.language?.toLowerCase().startsWith("es")) {
      return "es";
    }
  }
  return fallback;
}

export function writeLocale(locale: Locale) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; SameSite=Lax`;
  try {
    localStorage.setItem(LOCALE_COOKIE, locale);
  } catch {
    /* ignore */
  }
}

function interpolate(template: string, vars?: Record<string, string | number>) {
  if (!vars) {
    return template;
  }
  let text = template;
  for (const [key, value] of Object.entries(vars)) {
    text = text.replaceAll(`{${key}}`, String(value));
  }
  return text;
}

export function I18nProvider({
  messages,
  initialLocale = "en",
  children,
}: {
  messages: Record<Locale, Messages>;
  initialLocale?: Locale;
  children: ReactNode;
}) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale);

  useEffect(() => {
    const next = readLocale(initialLocale);
    if (next !== locale) {
      setLocaleState(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nValue>(() => {
    const setLocale = (next: Locale) => {
      setLocaleState(next);
      writeLocale(next);
    };
    const t = (key: string, vars?: Record<string, string | number>) =>
      interpolate(messages[locale]?.[key] || messages.en[key] || key, vars);
    return { locale, setLocale, t };
  }, [locale, messages]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const value = useContext(I18nContext);
  if (!value) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return value;
}

export function LanguageSelect() {
  const { locale, setLocale, t } = useI18n();
  return (
    <div className="lang-select">
      <span>{t("lang.label")}</span>
      <div className="lang-toggle" role="group" aria-label={t("lang.label")}>
        <button type="button" className={locale === "en" ? "btn" : "btn secondary"} onClick={() => setLocale("en")}>
          EN
        </button>
        <button type="button" className={locale === "es" ? "btn" : "btn secondary"} onClick={() => setLocale("es")}>
          ES
        </button>
      </div>
    </div>
  );
}

export function CrossAppLink({ port, children }: { port: number; children: React.ReactNode }) {
  return (
    <a
      href={`http://localhost:${port}`}
      onClick={(event) => {
        if (typeof window === "undefined") {
          return;
        }
        event.preventDefault();
        window.location.href = `${window.location.protocol}//${window.location.hostname}:${port}`;
      }}
    >
      {children}
    </a>
  );
}
