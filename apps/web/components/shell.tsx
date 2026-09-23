"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CrossAppLink, LanguageSelect, useI18n } from "@/lib/i18n";

const LINKS = [
  { href: "/", key: "nav.overview" },
  { href: "/documents", key: "nav.documents" },
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
          <strong>ATRIUM</strong>
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
          <LanguageSelect />
          {t("foot.blurb")}
          <div style={{ marginTop: 10 }}>
            <CrossAppLink port={3001}>{t("foot.admin")}</CrossAppLink>
          </div>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
