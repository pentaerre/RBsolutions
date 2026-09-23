export type Locale = "en" | "es";

export const LOCALE_COOKIE = "atrium_lang";

export function parseLocale(value: string | null | undefined): Locale {
  return value === "es" ? "es" : "en";
}
