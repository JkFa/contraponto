import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, createEpisode, getEpisode, watchEpisode } from "../api/client";
import type { CreateEpisodeForm, Episode, ProgressEvent } from "../api/types";
import { useOnAir } from "../components/OnAir";
import { ProgressStudio } from "../components/ProgressStudio";
import { MAX_TEXT } from "../components/SourceField";
import { markHistory, recallForm, rememberForm, upsertHistory } from "../lib/storage";

type View =
  | { kind: "loading" }
  | { kind: "progress"; ev: ProgressEvent }
  | { kind: "failed"; code: string; message: string }
  | { kind: "expired" };

const TRANSCRIPT_CODES = new Set(["TRANSCRIPT_UNAVAILABLE", "CONFRONTO_TRANSCRIPT_UNAVAILABLE"]);

export default function Studio() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { setLive } = useOnAir();
  const [view, setView] = useState<View>({ kind: "loading" });
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    let stop: (() => void) | undefined;
    let alive = true;
    const slowTimer = window.setTimeout(() => alive && setSlow(true), 4000);

    const route = (ep: Episode) => {
      if (ep.script) markHistory(ep.id, { title: ep.script.title });
      if (ep.status === "script_ready") {
        markHistory(ep.id, { status: "script_ready" });
        navigate(`/e/${ep.id}/revisar`, { replace: true });
        return true;
      }
      if (ep.status === "ready") {
        markHistory(ep.id, { status: "ready" });
        navigate(`/e/${ep.id}/ouvir`, { replace: true });
        return true;
      }
      if (ep.status === "failed") {
        setView({ kind: "failed", code: ep.error?.code ?? "INTERNAL", message: ep.error?.message ?? "Algo deu errado." });
        return true;
      }
      return false;
    };

    getEpisode(id)
      .then((ep) => {
        if (!alive) return;
        setSlow(false);
        if (route(ep)) return;
        setView({ kind: "progress", ev: { status: ep.status, step: ep.status === "rendering" ? "Gravando as vozes" : "Lendo a fonte primária", pct: 5 } });
        stop = watchEpisode(id, (ev) => {
          if (!alive) return;
          if (ev.type === "progress") setView({ kind: "progress", ev: ev.data });
          else if (ev.type === "error") {
            if (ev.data.code === "EXPIRED") setView({ kind: "expired" });
            else setView({ kind: "failed", code: ev.data.code, message: ev.data.message });
          } else {
            getEpisode(id).then((fresh) => alive && route(fresh)).catch(() => undefined);
          }
        });
      })
      .catch((err: ApiError) => {
        if (!alive) return;
        if (err.status === 404) {
          markHistory(id, { status: "expired" });
          setView({ kind: "expired" });
        } else setView({ kind: "failed", code: err.code, message: err.message });
      })
      .finally(() => window.clearTimeout(slowTimer));
    return () => {
      alive = false;
      stop?.();
      window.clearTimeout(slowTimer);
    };
  }, [id, navigate]);

  const live = view.kind === "progress";
  useEffect(() => {
    setLive(live);
    return () => setLive(false);
  }, [live, setLive]);

  if (view.kind === "loading") {
    return (
      <div className="page page--narrow">
        <ProgressStudio step="Conectando ao estúdio" pct={2} phase="script" waking={slow} />
      </div>
    );
  }
  if (view.kind === "expired") {
    return (
      <div className="page page--narrow empty-state">
        <h1>Esse episódio expirou.</h1>
        <p className="dim">Os episódios ficam disponíveis por 24 horas. Gere um novo a partir do mesmo material.</p>
        <Link className="btn btn--primary" to="/">Novo episódio</Link>
      </div>
    );
  }
  if (view.kind === "failed") {
    return (
      <div className="page page--narrow">
        {TRANSCRIPT_CODES.has(view.code) ? (
          <PasteFallback id={id} code={view.code} message={view.message} />
        ) : (
          <div className="failure" role="alert">
            <h1>O estúdio parou.</h1>
            <p>{view.message}</p>
            <div className="actions-row">
              <Link className="btn btn--primary" to="/">Voltar e tentar de novo</Link>
            </div>
          </div>
        )}
      </div>
    );
  }
  const phase = ["rendering", "ready"].includes(view.ev.status) ? "audio" : "script";
  return (
    <div className="page page--narrow">
      <ProgressStudio step={view.ev.step} pct={view.ev.pct} phase={phase} />
      <p className="fineprint studio__note">
        {phase === "script"
          ? "Você vai revisar o roteiro e a verificação antes de qualquer áudio ser gravado."
          : "Pode deixar esta aba aberta: o episódio fica pronto em alguns minutos."}
      </p>
    </div>
  );
}

/** "Cole o texto aqui": resubmits keeping mode, thesis and the other source. */
function PasteFallback({ id, code, message }: { id: string; code: string; message: string }) {
  const navigate = useNavigate();
  const isConfronto = code === "CONFRONTO_TRANSCRIPT_UNAVAILABLE";
  const form = recallForm(id);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resend = async (next: CreateEpisodeForm) => {
    setBusy(true);
    setError(null);
    try {
      const { id: newId } = await createEpisode(next);
      rememberForm(newId, next);
      upsertHistory({ id: newId, title: "Episódio em preparo", created_at: new Date().toISOString(), status: "pending" });
      navigate(`/e/${newId}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo deu errado. Tente de novo.");
      setBusy(false);
    }
  };

  const submit = () => {
    if (!form) return;
    const pasted = { kind: "text" as const, text };
    void resend(isConfronto ? { ...form, confronto: pasted } : { ...form, primary: pasted });
  };

  return (
    <section className="paste" aria-labelledby="paste-title">
      <h1 id="paste-title">
        {isConfronto ? "Não deu para ler o material de confronto." : "Esse vídeo não deixou a gente ler a transcrição."}
      </h1>
      <p>{message}</p>
      {form ? (
        <>
          <div className="field">
            <label className="field__label" htmlFor="paste-text">
              Cole aqui o texto {isConfronto ? "do material de confronto" : "da fonte primária"}
            </label>
            <textarea id="paste-text" className="textarea" rows={9} maxLength={MAX_TEXT} value={text}
              onChange={(e) => setText(e.target.value)} disabled={busy}
              placeholder="No YouTube: … (mais) → Mostrar transcrição → copie o texto." />
            <p className="field__hint">O modo, a tese e {isConfronto ? "a fonte primária" : "o material de confronto"} continuam como estavam.</p>
          </div>
          <div className="actions-row">
            <button type="button" className="btn btn--primary" onClick={submit} disabled={busy || !text.trim()}>
              {busy ? "Enviando…" : "Seguir com este texto"}
            </button>
            {isConfronto && (
              <button type="button" className="btn" disabled={busy}
                onClick={() => void resend({ ...form, confronto: null })}>
                Seguir sem confronto
              </button>
            )}
          </div>
          {error && <p className="field__error" role="alert">{error}</p>}
        </>
      ) : (
        <div className="actions-row">
          <Link className="btn btn--primary" to="/">Voltar e colar o texto</Link>
        </div>
      )}
    </section>
  );
}
