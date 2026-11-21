import type { Source } from "../api/types";

export function sourceName(s: Source): string {
  if (s.title) return s.title;
  if (s.kind === "youtube") return "Vídeo do YouTube";
  if (s.kind === "file") return "Arquivo enviado";
  return "Texto colado";
}

/** Primary + confronto sources with links (no third-party embeds). */
export function SourceChips({ sources }: { sources: Source[] }) {
  return (
    <ul className="source-chips" aria-label="Fontes do episódio">
      {sources.map((s) => (
        <li key={s.role} className={`source-chip source-chip--${s.role}`}>
          <span className="source-chip__role">{s.role === "primaria" ? "Fonte primária" : "Confronto"}</span>
          {s.url ? (
            <a href={s.url} target="_blank" rel="noopener noreferrer">{sourceName(s)}</a>
          ) : (
            <span>{sourceName(s)}</span>
          )}
          {s.author && <span className="dim"> de {s.author}</span>}
        </li>
      ))}
    </ul>
  );
}
