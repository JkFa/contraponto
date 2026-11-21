import { useId, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import type { SourceInput } from "../api/types";
import { isYouTubeUrl } from "../lib/format";
import { IconFile } from "./Icons";

export type SourceTab = "youtube" | "text" | "file";
export interface SourceDraft { tab: SourceTab; url: string; text: string; file: File | null }

export const emptyDraft = (tab: SourceTab = "youtube"): SourceDraft => ({ tab, url: "", text: "", file: null });

export const MAX_TEXT = 60_000;
export const MAX_FILE = 5 * 1024 * 1024;
const ACCEPT = [".txt", ".srt", ".pdf"];

/** Returns an error message for the active tab, or null. Empty is not an error here. */
export function draftError(d: SourceDraft): string | null {
  if (d.tab === "youtube" && d.url.trim() && !isYouTubeUrl(d.url)) return "Esse link não parece ser do YouTube.";
  if (d.tab === "text" && d.text.length > MAX_TEXT) return "O texto passa de 60 000 caracteres. Use um trecho menor.";
  if (d.tab === "file" && d.file) {
    if (!ACCEPT.some((ext) => d.file!.name.toLowerCase().endsWith(ext))) return "Envie um arquivo .txt, .srt ou .pdf com texto.";
    if (d.file.size > MAX_FILE) return "O arquivo passa de 5 MB. Envie um arquivo menor.";
  }
  return null;
}

export function draftToInput(d: SourceDraft): SourceInput | null {
  if (draftError(d)) return null;
  if (d.tab === "youtube" && d.url.trim()) return { kind: "youtube", url: d.url.trim() };
  if (d.tab === "text" && d.text.trim()) return { kind: "text", text: d.text };
  if (d.tab === "file" && d.file) return { kind: "file", file: d.file };
  return null;
}

export function draftSummary(d: SourceDraft): string | null {
  const input = draftToInput(d);
  if (!input) return null;
  if (input.kind === "youtube") return "Link do YouTube";
  if (input.kind === "text") return `Texto · ${input.text.length.toLocaleString("pt-BR")} caracteres`;
  return `Arquivo · ${input.file.name}`;
}

const TABS: { id: SourceTab; label: string }[] = [
  { id: "youtube", label: "Link do YouTube" },
  { id: "text", label: "Texto" },
  { id: "file", label: "Arquivo" },
];

interface Props {
  label: string;
  draft: SourceDraft;
  onChange: (d: SourceDraft) => void;
  disabled?: boolean;
  textPlaceholder?: string;
  showErrors?: boolean;
}

/** Tabs Link | Texto | Arquivo. Only one kind of input is active at a time. */
export function SourceField({ label, draft, onChange, disabled, textPlaceholder, showErrors }: Props) {
  const uid = useId();
  const [touched, setTouched] = useState(false);
  const [dragging, setDragging] = useState(false);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const error = draftError(draft);
  const visibleError = (touched || showErrors) ? error : null;

  const select = (tab: SourceTab) => {
    // values of other tabs are kept, but only the active tab is ever submitted
    onChange({ ...draft, tab });
    setTouched(false);
  };

  const onTabKey = (e: KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = (i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length;
    select(TABS[next]!.id);
    tabRefs.current[next]?.focus();
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      onChange({ ...emptyDraft("file"), file });
      setTouched(true);
    }
  };

  const errId = `${uid}-err`;
  return (
    <div className="source">
      <div className="source__tabs" role="tablist" aria-label={label}>
        {TABS.map((t, i) => (
          <button key={t.id} type="button" role="tab" id={`${uid}-tab-${t.id}`}
            ref={(el) => { tabRefs.current[i] = el; }}
            aria-selected={draft.tab === t.id} aria-controls={`${uid}-panel`}
            tabIndex={draft.tab === t.id ? 0 : -1} disabled={disabled}
            className="source__tab" onClick={() => select(t.id)} onKeyDown={(e) => onTabKey(e, i)}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="source__panel" role="tabpanel" id={`${uid}-panel`} aria-labelledby={`${uid}-tab-${draft.tab}`}>
        {draft.tab === "youtube" && (
          <>
            <label className="visually-hidden" htmlFor={`${uid}-url`}>{label}: link do YouTube</label>
            <input id={`${uid}-url`} className="input" type="url" inputMode="url" autoComplete="off"
              placeholder="https://www.youtube.com/watch?v=…" value={draft.url} disabled={disabled}
              aria-invalid={visibleError ? true : undefined} aria-describedby={visibleError ? errId : undefined}
              onChange={(e) => onChange({ ...draft, url: e.target.value })} onBlur={() => setTouched(true)} />
          </>
        )}
        {draft.tab === "text" && (
          <>
            <label className="visually-hidden" htmlFor={`${uid}-text`}>{label}: texto</label>
            <textarea id={`${uid}-text`} className="textarea" rows={7} value={draft.text} disabled={disabled}
              placeholder={textPlaceholder ?? "Cole aqui a transcrição, o artigo ou as anotações."}
              aria-invalid={visibleError ? true : undefined} aria-describedby={`${uid}-count${visibleError ? ` ${errId}` : ""}`}
              onChange={(e) => { onChange({ ...draft, text: e.target.value }); setTouched(true); }} />
            <p id={`${uid}-count`} className="source__count mono">
              {draft.text.length.toLocaleString("pt-BR")} / 60.000
            </p>
          </>
        )}
        {draft.tab === "file" && (
          <div className={`dropzone${dragging ? " is-dragging" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)} onDrop={onDrop}>
            <IconFile width={26} height={26} />
            {draft.file ? (
              <p><strong>{draft.file.name}</strong> <span className="dim">· {(draft.file.size / 1024).toFixed(0)} KB</span></p>
            ) : (
              <p>Arraste um arquivo .txt, .srt ou .pdf até aqui</p>
            )}
            <label className="btn" htmlFor={`${uid}-file`}>
              {draft.file ? "Trocar arquivo" : "Escolher arquivo"}
            </label>
            <input id={`${uid}-file`} className="visually-hidden" type="file"
              accept=".txt,.srt,.pdf,text/plain,application/pdf" disabled={disabled}
              aria-describedby={visibleError ? errId : undefined}
              onChange={(e) => { onChange({ ...draft, file: e.target.files?.[0] ?? null }); setTouched(true); }} />
          </div>
        )}
        {visibleError && <p id={errId} className="field__error" role="alert">{visibleError}</p>}
      </div>
    </div>
  );
}
