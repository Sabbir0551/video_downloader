export interface HistoryItem {
  id: string;
  title: string;
  url: string;
  thumbnailUrl?: string | null;
  qualityLabel?: string | null;
  fileSize?: number | null;
  downloadUrl: string;
  timestamp: number;
}

const HISTORY_KEY = "anystream_download_history";
const LANG_KEY = "anystream_lang";
const THEME_KEY = "anystream_theme";

export function getStoredHistory(): HistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveHistoryItem(item: HistoryItem): void {
  if (typeof window === "undefined") return;
  try {
    const history = getStoredHistory().filter((i) => i.id !== item.id);
    history.unshift(item);
    // Keep last 25 items max
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 25)));
  } catch {
    // Ignore storage quota errors
  }
}

export function clearStoredHistory(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {}
}

export function getStoredLang(): "en" | "bn" {
  if (typeof window === "undefined") return "bn";
  try {
    const val = localStorage.getItem(LANG_KEY);
    return val === "en" || val === "bn" ? val : "bn";
  } catch {
    return "bn";
  }
}

export function setStoredLang(lang: "en" | "bn"): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {}
}

export function getStoredTheme(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  try {
    const val = localStorage.getItem(THEME_KEY);
    if (val === "dark" || val === "light") return val;
    // Check system preference
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  } catch {
    return "dark";
  }
}

export function setStoredTheme(theme: "dark" | "light"): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(THEME_KEY, theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } catch {}
}

