export const WORDS_PER_MIN = 150;

/** 0 → "00:00"; 3725 → "1:02:05" (tape counter). */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(Number.isFinite(totalSeconds) ? totalSeconds : 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** "mm:ss" | "h:mm:ss" → seconds (null if malformed). */
export function parseTimestamp(ts: string | null | undefined): number | null {
  if (!ts) return null;
  const parts = ts.trim().split(":").map((p) => Number(p));
  if (parts.some((p) => !Number.isInteger(p) || p < 0)) return null;
  if (parts.length === 2) return parts[0]! * 60 + parts[1]!;
  if (parts.length === 3) return parts[0]! * 3600 + parts[1]! * 60 + parts[2]!;
  return null;
}

export function countWords(text: string): number {
  const t = text.trim();
  return t ? t.split(/\s+/).length : 0;
}

/** Estimated spoken duration in seconds for a word count (~150 wpm in pt-BR). */
export function estimateSeconds(words: number): number {
  return Math.round((words / WORDS_PER_MIN) * 60);
}

/** YouTube link that opens the video at a given timestamp. */
export function youtubeAt(url: string | null | undefined, ts: string | null | undefined): string | null {
  if (!url) return null;
  const secs = parseTimestamp(ts);
  if (secs === null) return url;
  return `${url}${url.includes("?") ? "&" : "?"}t=${secs}s`;
}

export function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

const YT_RE = /^(https?:\/\/)?((www|m)\.)?(youtube\.com\/(watch\?(.*&)?v=|shorts\/|embed\/|live\/)|youtu\.be\/)[A-Za-z0-9_-]{11}/;

export function isYouTubeUrl(url: string): boolean {
  return YT_RE.test(url.trim());
}

export function slugify(text: string): string {
  return (
    text
      .normalize("NFKD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .toLowerCase()
      .slice(0, 60) || "episodio"
  );
}
