import type { Script, Source, Turn, TurnKind } from "../api/types";
import { youtubeAt } from "../lib/format";
import { AutoTextarea } from "./AutoTextarea";

export const KIND_LABEL: Record<TurnKind, string> = {
  contexto: "Contexto",
  citacao: "Citação",
  confronto: "Confronto",
  opiniao: "Opinião",
  pergunta: "Pergunta",
  transicao: "Transição",
};

export type SaveState = "idle" | "editing" | "saving" | "saved" | "conflict" | "error";

/** Turn numbers flagged by fidelity notes ("turno N"). */
export function flaggedTurns(notes: string[]): Set<number> {
  const out = new Set<number>();
  notes.forEach((n) => {
    const m = /turno (\d+)/i.exec(n);
    if (m) out.add(Number(m[1]) - 1);
  });
  return out;
}

interface Props {
  script: Script;
  sources: Source[];
  onTurnChange: (index: number, turn: Turn) => void;
  flashTurn?: number | null;
  readOnly?: boolean;
}

export function ScriptEditor({ script, sources, onTurnChange, flashTurn, readOnly }: Props) {
  const flagged = flaggedTurns(script.fidelity_notes);
  const byRole = Object.fromEntries(sources.map((s) => [s.role, s]));
  return (
    <ol className="turns stagger" aria-label="Falas do roteiro">
      {script.turns.map((turn, i) => {
        const name = script.hosts[turn.speaker];
        const src = turn.role ? byRole[turn.role] : undefined;
        const tsLink = turn.source_ts && src?.kind === "youtube" ? youtubeAt(src.url, turn.source_ts) : null;
        return (
          <li key={i} id={`turn-${i}`} tabIndex={-1}
            className={`turn turn--${turn.speaker === "HOST_1" ? "h1" : "h2"}${flagged.has(i) ? " is-flagged" : ""}${flashTurn === i ? " is-flash" : ""}`}
            style={{ "--i": i } as React.CSSProperties}>
            <div className="turn__meta">
              <span className="turn__who">{name}</span>
              <span className={`chip chip--kind chip--${turn.kind}`}>{KIND_LABEL[turn.kind]}</span>
              {turn.role && (turn.kind === "citacao" || turn.kind === "confronto") && (
                <span className="chip chip--mono">{turn.role === "primaria" ? "primária" : "confronto"}</span>
              )}
              {turn.source_ts && (tsLink ? (
                <a className="chip chip--mono chip--ts" href={tsLink} target="_blank" rel="noopener noreferrer"
                  aria-label={`Abrir o vídeo em ${turn.source_ts} (nova aba)`}>{turn.source_ts}</a>
              ) : (
                <span className="chip chip--mono">{turn.source_ts}</span>
              ))}
              {flagged.has(i) && <span className="chip chip--warn">Confira a citação</span>}
            </div>
            {readOnly ? (
              <p className={`turn__text${turn.kind === "citacao" ? " turn__text--quote" : ""}`}>{turn.text}</p>
            ) : (
              <>
                <label className="visually-hidden" htmlFor={`turn-text-${i}`}>Fala {i + 1}, {name}</label>
                <AutoTextarea id={`turn-text-${i}`}
                  className={`turn__text turn__text--edit${turn.kind === "citacao" ? " turn__text--quote" : ""}`}
                  maxLength={600} value={turn.text}
                  aria-invalid={!turn.text.trim() || undefined}
                  onChange={(e) => onTurnChange(i, { ...turn, text: e.target.value })} />
              </>
            )}
          </li>
        );
      })}
    </ol>
  );
}
