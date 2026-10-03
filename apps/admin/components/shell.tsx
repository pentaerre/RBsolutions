"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CrossAppLink, useI18n } from "@/lib/i18n";
import { PrefsPanel } from "@/lib/theme";

const LINKS = [
  { href: "/", key: "nav.overview" },
  { href: "/graph", key: "nav.graph" },
  { href: "/utilities", key: "nav.utilities" },
  { href: "/apps", key: "nav.apps" },
  { href: "/tools", key: "nav.tools" },
  { href: "/agents", key: "nav.agents" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>ATRIUM</strong>
          <span>{t("brand.admin")}</span>
        </div>
        <nav>
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href)) ? "active" : ""}
            >
              {t(link.key)}
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p className="foot-blurb">{t("foot.blurb")}</p>
          <CrossAppLink port={3000}>
            <div className="brand brand-cross">
              <strong>XAVIER</strong>
              <span>{t("foot.workspaceHint")}</span>
            </div>
          </CrossAppLink>
          <PrefsPanel />
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
