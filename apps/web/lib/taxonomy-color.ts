export type TaxTone = { bg: string; fg: string; border: string };

const FAMILY_HUES = [208, 262, 16, 148, 38, 328, 186, 82, 300, 52];

function hash(id: string): number {
  let n = 2166136261;
  for (let i = 0; i < id.length; i += 1) {
    n ^= id.charCodeAt(i);
    n = Math.imul(n, 16777619);
  }
  return n >>> 0;
}

function hsl(h: number, s: number, l: number): string {
  return `hsl(${h} ${s}% ${l}%)`;
}

function tone(h: number, s: number, l: number): TaxTone {
  return {
    bg: hsl(h, s, l),
    fg: l > 46 ? "#14120c" : "#f7f4ea",
    border: hsl(h, Math.min(s + 8, 80), Math.min(l + 12, 72)),
  };
}

export function taxonomyTone(l1: string, l2?: string): TaxTone {
  const family = FAMILY_HUES[hash(l1 || "other") % FAMILY_HUES.length];
  if (!l2) {
    return tone(family, 70, 42);
  }
  const shift = 18 + (hash(l2) % 16);
  return tone((family + shift) % 360, 64, 32);
}

export function taxonomyStyle(l1: string, l2?: string): { background: string; color: string; borderColor: string } {
  const next = taxonomyTone(l1, l2);
  return { background: next.bg, color: next.fg, borderColor: next.border };
}
