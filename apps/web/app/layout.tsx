import type { Metadata } from "next";
import { cookies } from "next/headers";
import { AppProviders } from "@/components/providers";
import { parseLocale, LOCALE_COOKIE } from "@/lib/locale";
import { FRAMES_COOKIE, THEME_BOOT, THEME_COOKIE, parseFrames, parseThemePref } from "@/lib/theme-config";
import { MESSAGES } from "@/lib/messages";
import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Xavier",
  description: "Xavier Institute — Cerebro remembers what you send it",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const jar = await cookies();
  const locale = parseLocale(jar.get(LOCALE_COOKIE)?.value);
  const themePref = parseThemePref(jar.get(THEME_COOKIE)?.value);
  const frames = parseFrames(jar.get(FRAMES_COOKIE)?.value);
  return (
    <html
      lang={locale}
      data-theme={themePref === "system" ? "dark" : themePref}
      data-theme-pref={themePref}
      data-frames={frames}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body suppressHydrationWarning>
        <AppProviders
          messages={MESSAGES}
          initialLocale={locale}
          initialTheme={themePref}
          initialFrames={frames}
        >
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
