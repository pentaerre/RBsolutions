"use client";

import type { ReactNode } from "react";
import { Shell } from "@/components/shell";
import { ClientOnly } from "@/components/client-only";
import { I18nProvider, type Locale } from "@/lib/i18n";
import { ThemeProvider, type FramePref, type ThemePref } from "@/lib/theme";

export function AppProviders({
  messages,
  initialLocale,
  initialTheme,
  initialFrames,
  children,
}: {
  messages: Record<Locale, Record<string, string>>;
  initialLocale: Locale;
  initialTheme: ThemePref;
  initialFrames: FramePref;
  children: ReactNode;
}) {
  return (
    <I18nProvider messages={messages} initialLocale={initialLocale}>
      <ThemeProvider initialPref={initialTheme} initialFrames={initialFrames}>
        <ClientOnly>
          <Shell>{children}</Shell>
        </ClientOnly>
      </ThemeProvider>
    </I18nProvider>
  );
}
