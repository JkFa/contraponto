import type {
  CreateEpisodeForm, Episode, EpisodeEvent, Script, SourceInput,
} from "./types";
import { getGeminiKey } from "../lib/storage";

export const API_URL: string = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

const NETWORK_MSG = "Não consegui falar com o estúdio. Confira sua conexão e tente de novo.";

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = 30_000): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, signal: ctrl.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new ApiError("TIMEOUT", "O estúdio demorou demais para responder. Tente de novo.", 0);
    }
    throw new ApiError("NETWORK", NETWORK_MSG, 0);
  } finally {
    clearTimeout(timer);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    throw new ApiError(e?.code ?? "HTTP", e?.message ?? "Algo deu errado. Tente de novo.", res.status);
  }
  return body as T;
}

function keyHeader(): Record<string, string> {
  const key = getGeminiKey();
  return key ? { "X-Gemini-Key": key } : {};
}

export function health(): Promise<{ ok: boolean; version: string; llm: string; tts: string }> {
  return request("/api/health", {}, 90_000);
}

function appendSource(fd: FormData, input: SourceInput, prefix: "" | "confronto_"): void {
  if (input.kind === "youtube") fd.append(`${prefix}youtube_url`, input.url.trim());
  else if (input.kind === "text") fd.append(`${prefix}text`, input.text);
  else fd.append(`${prefix}file`, input.file, input.file.name);
}

/** Builds the multipart body; only includes fields the user filled in. */
export function buildEpisodeFormData(form: CreateEpisodeForm): FormData {
  const fd = new FormData();
  fd.append("mode", form.mode);
  appendSource(fd, form.primary, "");
  if (form.confronto) appendSource(fd, form.confronto, "confronto_");
  if (form.mode === "critica" && form.thesis) fd.append("thesis", form.thesis);
  if (form.mode === "react" && form.focus_points?.trim()) fd.append("focus_points", form.focus_points);
  if (form.duration_min) fd.append("duration_min", String(form.duration_min));
  if (form.tone) fd.append("tone", form.tone);
  if (form.host1_name?.trim()) fd.append("host1_name", form.host1_name.trim());
  if (form.host2_name?.trim()) fd.append("host2_name", form.host2_name.trim());
  return fd;
}

export function createEpisode(form: CreateEpisodeForm): Promise<{ id: string; status: string }> {
  return request("/api/episodes", {
    method: "POST",
    body: buildEpisodeFormData(form),
    headers: keyHeader(),
  });
}

export function getEpisode(id: string): Promise<Episode> {
  return request(`/api/episodes/${encodeURIComponent(id)}`);
}

/**
 * Subscribes to SSE progress. Closes itself on done/error. On reconnect,
 * reconciles via GET /api/episodes/{id}. Returns an unsubscribe function.
 */
export function watchEpisode(id: string, onEvent: (ev: EpisodeEvent) => void): () => void {
  let closed = false;
  const es = new EventSource(`${API_URL}/api/episodes/${encodeURIComponent(id)}/events`);
  const close = () => {
    closed = true;
    es.close();
  };
  const parse = (e: MessageEvent) => {
    try {
      return JSON.parse(e.data);
    } catch {
      return null;
    }
  };
  es.addEventListener("progress", (e) => {
    const data = parse(e as MessageEvent);
    if (data) onEvent({ type: "progress", data });
  });
  es.addEventListener("done", (e) => {
    const data = parse(e as MessageEvent);
    close();
    if (data) onEvent({ type: "done", data });
  });
  es.addEventListener("error", (e) => {
    const data = parse(e as MessageEvent);
    if (data) {
      close();
      onEvent({ type: "error", data });
      return;
    }
    // Connection error: EventSource will retry; reconcile with the real state.
    if (closed) return;
    getEpisode(id)
      .then((ep) => {
        if (closed) return;
        if (ep.status === "script_ready" || ep.status === "ready") {
          close();
          onEvent({ type: "done", data: { status: ep.status } });
        } else if (ep.status === "failed" && ep.error) {
          close();
          onEvent({ type: "error", data: ep.error });
        }
      })
      .catch((err: ApiError) => {
        if (err.status === 404) {
          close();
          onEvent({ type: "error", data: { code: "EXPIRED", message: err.message } });
        }
      });
  });
  return close;
}

export function saveScript(id: string, script: Script): Promise<Episode> {
  return request(`/api/episodes/${encodeURIComponent(id)}/script`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(script),
  });
}

export function regenerate(id: string, instructions?: string): Promise<{ status: string }> {
  return request(`/api/episodes/${encodeURIComponent(id)}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...keyHeader() },
    body: JSON.stringify(instructions?.trim() ? { instructions: instructions.trim() } : {}),
  });
}

export function render(id: string, opts?: { music?: boolean }): Promise<{ status: string }> {
  return request(`/api/episodes/${encodeURIComponent(id)}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts ?? {}),
  });
}

export function audioUrl(id: string, download = false): string {
  return `${API_URL}/api/episodes/${encodeURIComponent(id)}/audio.mp3${download ? "?download=1" : ""}`;
}

export function fileUrl(id: string, name: "script.md" | "script.json" | "verification.md" | "sources.md"): string {
  return `${API_URL}/api/episodes/${encodeURIComponent(id)}/${name}`;
}

export function shareUrl(id: string): string {
  return `${API_URL}/s/${encodeURIComponent(id)}`;
}

export function deleteEpisode(id: string): Promise<void> {
  return request(`/api/episodes/${encodeURIComponent(id)}`, { method: "DELETE" });
}
