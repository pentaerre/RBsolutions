"use client";

import type { ReactNode } from "react";
import { Shell } from "@/components/shell";
import { ClientOnly } from "@/components/client-only";
import { I18nProvider, type Locale } from "@/lib/i18n";

export function AppProviders({
  messages,
  initialLocale,
  children,
}: {
  messages: Record<Locale, Record<string, string>>;
  initialLocale: Locale;
  children: ReactNode;
}) {
  return (
    <I18nProvider messages={messages} initialLocale={initialLocale}>
      <ClientOnly>
        <Shell>{children}</Shell>
      </ClientOnly>
    </I18nProvider>
  );
}
