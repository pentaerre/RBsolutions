import type { Metadata } from "next";
import { cookies } from "next/headers";
import { AppProviders } from "@/components/providers";
import { parseLocale, LOCALE_COOKIE } from "@/lib/locale";
import { MESSAGES } from "@/lib/messages";
import "./globals.css";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Atrium Admin",
  description: "Control plane for Atrium apps, tools, and agents",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const jar = await cookies();
  const locale = parseLocale(jar.get(LOCALE_COOKIE)?.value);
  return (
    <html lang={locale} suppressHydrationWarning>
      <body suppressHydrationWarning>
        <AppProviders messages={MESSAGES} initialLocale={locale}>
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
