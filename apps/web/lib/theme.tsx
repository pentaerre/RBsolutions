"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useI18n } from "@/lib/i18n";
import {
  FRAMES_COOKIE,
  THEME_COOKIE,
  parseFrames,
  parseThemePref,
  resolveTheme,
  type FramePref,
  type ResolvedTheme,
  type ThemePref,
} from "@/lib/theme-config";

export type { FramePref, ResolvedTheme, ThemePref };
export { FRAMES_COOKIE, THEME_COOKIE, parseFrames, parseThemePref } from "@/lib/theme-config";

type ThemeValue = {
  pref: ThemePref;
  frames: FramePref;
  resolved: ResolvedTheme;
  setPref: (next: ThemePref) => void;
  setFrames: (next: FramePref) => void;
};

const ThemeContext = createContext<ThemeValue | null>(null);

function writeCookie(name: string, value: string) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=31536000; SameSite=Lax`;
  try {
    localStorage.setItem(name, value);
  } catch {
    /* ignore */
  }
}

function readStored(name: string, fallback: string) {
  try {
    return localStorage.getItem(name) || fallback;
  } catch {
    return fallback;
  }
}

function applyDom(pref: ThemePref, frames: FramePref, resolved: ResolvedTheme) {
  const el = document.documentElement;
  el.setAttribute("data-theme", resolved);
  el.setAttribute("data-theme-pref", pref);
  el.setAttribute("data-frames", frames);
  el.style.colorScheme = resolved;
}

export function ThemeProvider({
  children,
  initialPref = "system",
  initialFrames = "soft",
}: {
  children: ReactNode;
  initialPref?: ThemePref;
  initialFrames?: FramePref;
}) {
  const [pref, setPrefState] = useState<ThemePref>(initialPref);
  const [frames, setFramesState] = useState<FramePref>(initialFrames);
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolveTheme(initialPref, true));

  useEffect(() => {
    const storedPref = parseThemePref(readStored(THEME_COOKIE, initialPref));
    const storedFrames = parseFrames(readStored(FRAMES_COOKIE, initialFrames));
    if (storedPref !== pref) setPrefState(storedPref);
    if (storedFrames !== frames) setFramesState(storedFrames);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const next = resolveTheme(pref, mq.matches);
      setResolved(next);
      applyDom(pref, frames, next);
    };
    apply();
    writeCookie(THEME_COOKIE, pref);
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [pref, frames]);

  useEffect(() => {
    writeCookie(FRAMES_COOKIE, frames);
    document.documentElement.setAttribute("data-frames", frames);
  }, [frames]);

  const value = useMemo<ThemeValue>(
    () => ({
      pref,
      frames,
      resolved,
      setPref: (next) => {
        setPrefState(next);
        writeCookie(THEME_COOKIE, next);
      },
      setFrames: (next) => {
        setFramesState(next);
        writeCookie(FRAMES_COOKIE, next);
      },
    }),
    [pref, frames, resolved],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return value;
}

export function PrefsPanel() {
  const { t, locale, setLocale } = useI18n();
  const { pref, frames, setPref, setFrames } = useTheme();

  return (
    <details className="prefs">
      <summary className="prefs-title">{t("prefs.title")}</summary>
      <div className="prefs-body">
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
        <div className="lang-select">
          <span>{t("prefs.theme")}</span>
          <div className="lang-toggle theme-toggle" role="group" aria-label={t("prefs.theme")}>
            <button type="button" className={pref === "system" ? "btn" : "btn secondary"} onClick={() => setPref("system")}>
              {t("prefs.themeSystem")}
            </button>
            <button type="button" className={pref === "dark" ? "btn" : "btn secondary"} onClick={() => setPref("dark")}>
              {t("prefs.themeDark")}
            </button>
            <button type="button" className={pref === "light" ? "btn" : "btn secondary"} onClick={() => setPref("light")}>
              {t("prefs.themeLight")}
            </button>
          </div>
        </div>
        <div className="lang-select">
          <span>{t("prefs.frames")}</span>
          <div className="lang-toggle" role="group" aria-label={t("prefs.frames")}>
            <button type="button" className={frames === "soft" ? "btn" : "btn secondary"} onClick={() => setFrames("soft")}>
              {t("prefs.framesSoft")}
            </button>
            <button type="button" className={frames === "firm" ? "btn" : "btn secondary"} onClick={() => setFrames("firm")}>
              {t("prefs.framesFirm")}
            </button>
          </div>
        </div>
      </div>
    </details>
  );
}
