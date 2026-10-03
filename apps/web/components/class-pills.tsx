"use client";

import { localizeTaxonomy } from "@/lib/catalog-i18n";
import { useI18n } from "@/lib/i18n";
import { taxonomyStyle, taxonomyTone } from "@/lib/taxonomy-color";

export function ClassPills({
  l1,
  l2,
  empty,
}: {
  l1?: string;
  l2?: string;
  empty: string;
}) {
  const { locale } = useI18n();
  if (!l1) {
    return <span className="tax-pill tax-pill-empty">{empty}</span>;
  }
  return (
    <span className="tax-pills">
      <span className="tax-pill" style={taxonomyStyle(l1)}>
        {localizeTaxonomy(l1, locale)}
      </span>
      {l2 ? (
        <span className="tax-pill" style={taxonomyStyle(l1, l2)}>
          {localizeTaxonomy(l2, locale)}
        </span>
      ) : null}
    </span>
  );
}

export function ClassDot({ l1, l2 }: { l1: string; l2?: string }) {
  const tone = taxonomyTone(l1, l2);
  return <span className="tax-dot" style={{ background: tone.bg, boxShadow: `0 0 0 2px ${tone.border}` }} />;
}
