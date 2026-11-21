import type { ReactNode } from "react";
import type { Turn, VerificationItem, VerificationStatus } from "../api/types";
import { AutoTextarea } from "./AutoTextarea";
import { MarkApoiada, MarkContestada, MarkNaoVerificavel, MarkParcial } from "./Icons";

export const STATUS_META: Record<VerificationStatus, { label: string; tone: "sage" | "rust" | "sand"; Mark: () => ReactNode }> = {
  apoiada: { label: "Apoiada", tone: "sage", Mark: () => <MarkApoiada /> },
  contestada: { label: "Contestada", tone: "rust", Mark: () => <MarkContestada /> },
  parcial: { label: "Parcial", tone: "sand", Mark: () => <MarkParcial /> },
  nao_verificavel: { label: "Não verificável", tone: "sand", Mark: () => <MarkNaoVerificavel /> },
};

const EVIDENCE: Record<VerificationItem["evidence_role"], string> = {
  confronto: "pelo confronto",
  primaria: "pela fonte primária",
  interna: "por exame interno",
};

export function StatusStamp({ status }: { status: VerificationStatus }) {
  const meta = STATUS_META[status];
  return (
    <span className={`stamp stamp--${meta.tone}`} data-status={status}>
      <meta.Mark />
      {meta.label}
    </span>
  );
}

const STOP = new Set("a o e de da do das dos que em um uma para com por na no nas nos se é ao os as".split(" "));
const words = (s: string) => new Set(s.toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "")
  .split(/[^a-z0-9]+/).filter((w) => w.length > 2 && !STOP.has(w)));

/** Best-effort link from a claim to the turn that discusses it (timestamp first, then word overlap). */
export function findRelatedTurn(item: VerificationItem, turns: Turn[]): number {
  if (item.claim_ts) {
    const byTs = turns.findIndex((t) => t.source_ts === item.claim_ts);
    if (byTs >= 0) return byTs;
  }
  const claim = words(item.claim);
  let best = -1;
  let bestScore = 0;
  turns.forEach((t, i) => {
    let score = 0;
    words(t.text).forEach((w) => { if (claim.has(w)) score++; });
    if (score > bestScore) { best = i; bestScore = score; }
  });
  return best;
}

interface Props {
  items: VerificationItem[];
  verdict: string;
  editable?: boolean;
  loading?: boolean;
  highlighted?: number | null;
  onItemChange?: (index: number, item: VerificationItem) => void;
  onVerdictChange?: (v: string) => void;
  onLocate?: (index: number) => void;
  hideVerdict?: boolean;
}

/** "Mesa de checagem": one row per claim, status stamp (icon + text, never color alone), verdict. */
export function VerificationPanel({ items, verdict, editable, loading, highlighted, onItemChange, onVerdictChange, onLocate, hideVerdict }: Props) {
  if (loading) {
    return <section className="verify" aria-busy="true"><p className="dim">Carregando a verificação…</p></section>;
  }
  const counts = items.reduce<Record<string, number>>((acc, i) => ({ ...acc, [i.status]: (acc[i.status] ?? 0) + 1 }), {});
  return (
    <section className="verify" aria-labelledby="verify-title">
      <header className="verify__head">
        <h2 id="verify-title">Verificação</h2>
        <p className="verify__tally">
          {(Object.keys(STATUS_META) as VerificationStatus[]).filter((s) => counts[s]).map((s) => (
            <span key={s}>{counts[s]} {STATUS_META[s].label.toLowerCase()}</span>
          ))}
        </p>
      </header>

      {items.length === 0 ? (
        <p className="verify__empty">Este roteiro veio sem verificação. Regenere para que a IA aplique o exame.</p>
      ) : (
        <ol className="verify__list stagger">
          {items.map((item, i) => (
            <li key={i} className={`claim${highlighted === i ? " is-highlighted" : ""}`} style={{ "--i": i } as React.CSSProperties}>
              <div className="claim__top">
                {editable ? (
                  <label className="claim__status-edit">
                    <span className="visually-hidden">Status da afirmação {i + 1}</span>
                    <select className="select select--stamp" value={item.status}
                      onChange={(e) => onItemChange?.(i, { ...item, status: e.target.value as VerificationStatus })}>
                      {(Object.keys(STATUS_META) as VerificationStatus[]).map((s) => (
                        <option key={s} value={s}>{STATUS_META[s].label}</option>
                      ))}
                    </select>
                    <StatusStamp status={item.status} />
                  </label>
                ) : (
                  <StatusStamp status={item.status} />
                )}
                <span className="claim__evidence">
                  {EVIDENCE[item.evidence_role]}
                  {item.claim_ts && <span className="mono"> · {item.claim_ts}</span>}
                </span>
              </div>
              {editable ? (
                <>
                  <label className="visually-hidden" htmlFor={`claim-${i}`}>Afirmação {i + 1}</label>
                  <AutoTextarea id={`claim-${i}`} className="claim__text claim__text--edit" maxLength={220} 
                    value={item.claim} onChange={(e) => onItemChange?.(i, { ...item, claim: e.target.value })} />
                  <label className="visually-hidden" htmlFor={`note-${i}`}>Nota da afirmação {i + 1}</label>
                  <AutoTextarea id={`note-${i}`} className="claim__note claim__note--edit" maxLength={280} 
                    aria-invalid={!item.note.trim() || undefined}
                    value={item.note} onChange={(e) => onItemChange?.(i, { ...item, note: e.target.value })} />
                </>
              ) : (
                <>
                  <p className="claim__text">{item.claim}</p>
                  <p className="claim__note">{item.note}</p>
                </>
              )}
              {onLocate && (
                <button type="button" className="claim__locate" onClick={() => onLocate(i)}>
                  Ver no roteiro
                </button>
              )}
            </li>
          ))}
        </ol>
      )}

      {!hideVerdict && <figure className="verdict">
        <figcaption>Veredito do episódio</figcaption>
        {editable ? (
          <>
            <label className="visually-hidden" htmlFor="verdict">Veredito</label>
            <AutoTextarea id="verdict" className="verdict__text verdict__text--edit" maxLength={300} 
              aria-invalid={!verdict.trim() || undefined}
              value={verdict} onChange={(e) => onVerdictChange?.(e.target.value)} />
          </>
        ) : (
          <blockquote className="verdict__text">{verdict}</blockquote>
        )}
      </figure>}
    </section>
  );
}
