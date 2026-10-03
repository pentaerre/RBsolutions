"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CrossAppLink, useI18n } from "@/lib/i18n";
import { PrefsPanel } from "@/lib/theme";

const LINKS = [
  { href: "/", key: "nav.overview" },
  { href: "/calendar", key: "nav.calendar" },
  { href: "/library", key: "nav.library" },
  { href: "/documents", key: "nav.documents" },
  { href: "/brief", key: "nav.brief" },
  { href: "/chat", key: "nav.chat" },
  { href: "/tools", key: "nav.tools" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>XAVIER</strong>
          <span>{t("brand.workspace")}</span>
        </div>
        <nav>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? "active" : ""}
            >
              {t(link.key)}
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p className="foot-blurb">{t("foot.blurb")}</p>
          <CrossAppLink port={3001}>
            <div className="brand brand-cross">
              <strong>ADMIN</strong>
              <span>{t("foot.adminHint")}</span>
            </div>
          </CrossAppLink>
          <PrefsPanel />
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
