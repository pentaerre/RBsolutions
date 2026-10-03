export const THEME_COOKIE = "atrium_theme";
export const FRAMES_COOKIE = "atrium_frames";

export type ThemePref = "system" | "light" | "dark";
export type FramePref = "soft" | "firm";
export type ResolvedTheme = "light" | "dark";

export function parseThemePref(value: string | null | undefined): ThemePref {
  return value === "light" || value === "dark" || value === "system" ? value : "system";
}

export function parseFrames(value: string | null | undefined): FramePref {
  return value === "firm" ? "firm" : "soft";
}

export function resolveTheme(pref: ThemePref, systemDark: boolean): ResolvedTheme {
  if (pref === "light") return "light";
  if (pref === "dark") return "dark";
  return systemDark ? "dark" : "light";
}

export const THEME_BOOT = `(function(){try{var k=function(n){var m=document.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));return m?decodeURIComponent(m[1]):''};var p=k('${THEME_COOKIE}')||(function(){try{return localStorage.getItem('${THEME_COOKIE}')||''}catch(e){return ''}})()||'system';var f=k('${FRAMES_COOKIE}')||(function(){try{return localStorage.getItem('${FRAMES_COOKIE}')||''}catch(e){return ''}})()||'soft';if(p!=='light'&&p!=='dark'&&p!=='system')p='system';if(f!=='firm')f='soft';var dark=window.matchMedia('(prefers-color-scheme: dark)').matches;var t=p==='light'?'light':p==='dark'?'dark':(dark?'dark':'light');var el=document.documentElement;el.setAttribute('data-theme',t);el.setAttribute('data-theme-pref',p);el.setAttribute('data-frames',f);el.style.colorScheme=t;}catch(e){}})();`;
