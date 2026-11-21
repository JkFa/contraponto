import type { CreateEpisodeForm } from "../api/types";

const HISTORY_KEY = "contraponto.history.v1";
const GEMINI_KEY = "contraponto.gemini-key";
const MAX_HISTORY = 30;

export interface HistoryEntry {
  id: string;
  title: string;
  created_at: string;
  status?: "script_ready" | "ready" | "expired" | "pending";
}

function safeGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode) */
  }
}

export function getHistory(): HistoryEntry[] {
  try {
    const parsed = JSON.parse(safeGet(HISTORY_KEY) ?? "[]");
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function upsertHistory(entry: HistoryEntry): HistoryEntry[] {
  const list = getHistory().filter((e) => e.id !== entry.id);
  const prev = getHistory().find((e) => e.id === entry.id);
  const next = [{ ...prev, ...entry }, ...list].slice(0, MAX_HISTORY);
  safeSet(HISTORY_KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("contraponto:history"));
  return next;
}

export function markHistory(id: string, patch: Partial<HistoryEntry>): void {
  const list = getHistory();
  const idx = list.findIndex((e) => e.id === id);
  if (idx < 0) return;
  list[idx] = { ...list[idx]!, ...patch };
  safeSet(HISTORY_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("contraponto:history"));
}

export function removeHistory(id: string): void {
  safeSet(HISTORY_KEY, JSON.stringify(getHistory().filter((e) => e.id !== id)));
  window.dispatchEvent(new Event("contraponto:history"));
}

/** BYOK: kept only in this browser, sent as a header, never to our logs. */
export function getGeminiKey(): string {
  return safeGet(GEMINI_KEY) ?? "";
}

export function setGeminiKey(key: string): void {
  safeSet(GEMINI_KEY, key.trim() || null);
}

/** Forms are kept in memory (Files can't be serialized) so a failed transcript can be retried. */
const pendingForms = new Map<string, CreateEpisodeForm>();

export function rememberForm(id: string, form: CreateEpisodeForm): void {
  pendingForms.set(id, form);
}

export function recallForm(id: string): CreateEpisodeForm | undefined {
  return pendingForms.get(id);
}
