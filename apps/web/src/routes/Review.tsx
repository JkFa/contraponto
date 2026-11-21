import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, getEpisode, regenerate, render, saveScript } from "../api/client";
import type { Episode, Script, Turn, VerificationItem } from "../api/types";
import { AutoTextarea } from "../components/AutoTextarea";
import { IconRefresh } from "../components/Icons";
import { ScriptEditor, flaggedTurns, type SaveState } from "../components/ScriptEditor";
import { SourceChips } from "../components/SourceChips";
import { useToast } from "../components/Toast";
import { VerificationPanel, findRelatedTurn } from "../components/VerificationPanel";
import { countWords, estimateSeconds, formatClock } from "../lib/format";
import { markHistory } from "../lib/storage";

const SAVE_LABEL: Record<SaveState, string> = {
  idle: "Sem alterações",
  editing: "Alterações não salvas",
  saving: "Salvando…",
  saved: "Edições salvas",
  conflict: "O episódio mudou de estado. Recarregue a página.",
  error: "Não consegui salvar. Confira os campos destacados.",
};

export default function Review() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [save, setSave] = useState<SaveState>("idle");
  const [busy, setBusy] = useState<null | "render" | "regen">(null);
  const [regenOpen, setRegenOpen] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [flash, setFlash] = useState<number | null>(null);
  const [highlight, setHighlight] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getEpisode(id)
      .then((ep) => {
        if (!alive) return;
        if (ep.status === "ready") return navigate(`/e/${id}/ouvir`, { replace: true });
        if (ep.status !== "script_ready" || !ep.script) return navigate(`/e/${id}`, { replace: true });
        markHistory(id, { title: ep.script.title, status: "script_ready" });
        setEpisode(ep);
        setScript(ep.script);
      })
      .catch((err: ApiError) => {
        if (!alive) return;
        if (err.status === 404) markHistory(id, { status: "expired" });
        setLoadError(err.message);
      });
    return () => { alive = false; };
  }, [id, navigate]);

  const words = useMemo(() => (script ? script.turns.reduce((n, t) => n + countWords(t.text), 0) : 0), [script]);

  if (loadError) {
    return (
      <div className="page page--narrow empty-state">
        <h1>Não consegui abrir este roteiro.</h1>
        <p className="dim">{loadError}</p>
        <Link className="btn btn--primary" to="/">Novo episódio</Link>
      </div>
    );
  }
  if (!episode || !script) {
    return <div className="page"><VerificationPanel items={[]} verdict="" loading /></div>;
  }

  const edit = (next: Script) => {
    setScript(next);
    setSave("editing");
  };
  const onTurn = (i: number, turn: Turn) => edit({ ...script, turns: script.turns.map((t, j) => (j === i ? turn : t)) });
  const onItem = (i: number, item: VerificationItem) =>
    edit({ ...script, verification: script.verification.map((v, j) => (j === i ? item : v)) });

  const locate = (i: number) => {
    const item = script.verification[i];
    if (!item) return;
    const idx = findRelatedTurn(item, script.turns);
    setHighlight(i);
    if (idx < 0) {
      toast.show("Não achei uma fala que trate diretamente desta afirmação.");
      return;
    }
    const el = document.getElementById(`turn-${idx}`);
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el?.scrollIntoView?.({ behavior: reduce ? "auto" : "smooth", block: "center" });
    el?.focus({ preventScroll: true });
    setFlash(idx);
    window.setTimeout(() => setFlash(null), 1600);
  };

  const persist = async (): Promise<boolean> => {
    if (save !== "editing" && save !== "error") return true;
    setSave("saving");
    try {
      const ep = await saveScript(id, script);
      setEpisode(ep);
      setScript(ep.script ?? script);
      setSave("saved");
      markHistory(id, { title: ep.script?.title ?? script.title });
      return true;
    } catch (err) {
      const e = err as ApiError;
      setSave(e.status === 409 ? "conflict" : "error");
      toast.show(e.message, "error");
      return false;
    }
  };

  const approve = async () => {
    setBusy("render");
    if (!(await persist())) { setBusy(null); return; }
    try {
      await render(id);
      navigate(`/e/${id}`);
    } catch (err) {
      toast.show((err as ApiError).message, "error");
      setBusy(null);
    }
  };

  const doRegenerate = async () => {
    setBusy("regen");
    try {
      await regenerate(id, instructions);
      navigate(`/e/${id}`);
    } catch (err) {
      toast.show((err as ApiError).message, "error");
      setBusy(null);
    }
  };

  const flagged = flaggedTurns(script.fidelity_notes);
  return (
    <div className="review">
      <header className="review__head">
        <label className="visually-hidden" htmlFor="title">Título do episódio</label>
        <AutoTextarea id="title" className="review__title" maxLength={90} value={script.title}
          onChange={(e) => edit({ ...script, title: e.target.value })} />
        <label className="visually-hidden" htmlFor="summary">Resumo</label>
        <AutoTextarea id="summary" className="review__summary" maxLength={280} value={script.summary}
          onChange={(e) => edit({ ...script, summary: e.target.value })} />
        <SourceChips sources={episode.sources} />
      </header>

      <div className="review__grid">
        <div className="review__verify">
          <VerificationPanel items={script.verification} verdict={script.verdict} editable
            highlighted={highlight} onItemChange={onItem}
            onVerdictChange={(v) => edit({ ...script, verdict: v })} onLocate={locate} />

          {script.fidelity_notes.length > 0 && (
            <details className="fidelity" open>
              <summary>Fidelidade: {script.fidelity_notes.length} {script.fidelity_notes.length === 1 ? "aviso" : "avisos"}</summary>
              <ul>
                {script.fidelity_notes.map((note, i) => {
                  const m = /turno (\d+)/i.exec(note);
                  const turnIdx = m ? Number(m[1]) - 1 : null;
                  return (
                    <li key={i}>
                      {note}{" "}
                      {turnIdx !== null && flagged.has(turnIdx) && (
                        <a href={`#turn-${turnIdx}`} onClick={(e) => {
                          e.preventDefault();
                          document.getElementById(`turn-${turnIdx}`)?.scrollIntoView({ block: "center" });
                          document.getElementById(`turn-text-${turnIdx}`)?.focus({ preventScroll: true });
                        }}>Ir para a fala</a>
                      )}
                    </li>
                  );
                })}
              </ul>
            </details>
          )}
        </div>

        <section className="review__script" aria-labelledby="script-title">
          <h2 id="script-title" className="section-title">Roteiro</h2>
          <ScriptEditor script={script} sources={episode.sources} onTurnChange={onTurn} flashTurn={flash} />
        </section>
      </div>

      <footer className="dock" aria-label="Ações da revisão">
        <div className="dock__info">
          <span className="mono">{words} palavras · ~{formatClock(estimateSeconds(words))}</span>
          <span className={`dock__save dock__save--${save}`} aria-live="polite">{SAVE_LABEL[save]}</span>
        </div>
        {regenOpen && (
          <div className="dock__regen">
            <label className="visually-hidden" htmlFor="instructions">Instruções para regenerar</label>
            <input id="instructions" className="input" maxLength={1000} value={instructions}
              placeholder="Ex.: mais curto, menos jargão" onChange={(e) => setInstructions(e.target.value)} />
            <button type="button" className="btn" onClick={doRegenerate} disabled={busy !== null}>
              {busy === "regen" ? "Regenerando…" : "Regenerar agora"}
            </button>
          </div>
        )}
        <div className="dock__actions">
          {save === "editing" && (
            <button type="button" className="btn btn--ghost" onClick={() => void persist()} disabled={busy !== null}>
              Salvar edições
            </button>
          )}
          <button type="button" className="btn" onClick={() => setRegenOpen((v) => !v)} aria-expanded={regenOpen}
            disabled={busy !== null}>
            <IconRefresh /> Regenerar
          </button>
          <button type="button" className="btn btn--primary" onClick={approve} disabled={busy !== null || save === "conflict"}>
            {busy === "render" ? "Enviando ao estúdio…" : "Aprovar e gerar áudio"}
          </button>
        </div>
        <p className="dock__legal">Você é responsável pelo que publica.</p>
      </footer>
    </div>
  );
}
