import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, audioUrl, fileUrl, getEpisode, shareUrl } from "../api/client";
import type { Episode as EpisodeT } from "../api/types";
import { IconDownload, IconLink, IconPlus } from "../components/Icons";
import { Player } from "../components/Player";
import { ScriptEditor } from "../components/ScriptEditor";
import { ShareMenu } from "../components/ShareMenu";
import { SourceChips } from "../components/SourceChips";
import { useToast } from "../components/Toast";
import { VerificationPanel } from "../components/VerificationPanel";
import { formatBytes, slugify } from "../lib/format";
import { copyText } from "../lib/share";
import { markHistory } from "../lib/storage";

export default function Episode() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [ep, setEp] = useState<EpisodeT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getEpisode(id)
      .then((e) => {
        if (!alive) return;
        if (e.status !== "ready") return navigate(e.status === "script_ready" ? `/e/${id}/revisar` : `/e/${id}`, { replace: true });
        markHistory(id, { title: e.script?.title ?? "Episódio", status: "ready" });
        setEp(e);
      })
      .catch((err: ApiError) => {
        if (!alive) return;
        if (err.status === 404) markHistory(id, { status: "expired" });
        setError(err.message);
      });
    return () => { alive = false; };
  }, [id, navigate]);

  if (error) {
    return (
      <div className="page page--narrow empty-state">
        <h1>Esse episódio não está mais no ar.</h1>
        <p className="dim">{error} Os episódios ficam disponíveis por 24 horas.</p>
        <Link className="btn btn--primary" to="/">Novo episódio</Link>
      </div>
    );
  }
  if (!ep || !ep.script) return <div className="page page--narrow"><p className="dim">Carregando o episódio…</p></div>;

  const script = ep.script;
  const link = ep.share_url ?? shareUrl(id);
  const onCopy = async () => {
    const ok = await copyText(link);
    toast.show(ok ? "Link copiado." : "Não consegui copiar. Selecione o link e copie manualmente.", ok ? "success" : "error");
  };

  return (
    <div className="episode">
      <header className="episode__head">
        <p className="episode__ready">No ar. Seu episódio está pronto.</p>
        <h1 className="episode__title">{script.title}</h1>
        <p className="episode__summary">{script.summary}</p>
        <p className="episode__hosts">Com {script.hosts.HOST_1} e {script.hosts.HOST_2}</p>
      </header>

      <Player src={audioUrl(id)} title={script.title} initialDuration={ep.audio?.duration_s ?? 0} />
      <p className="seal">Vozes sintéticas · Gerado com IA</p>

      <figure className="verdict verdict--hero">
        <figcaption>Veredito do episódio</figcaption>
        <blockquote className="verdict__text">{script.verdict}</blockquote>
      </figure>

      <nav className="actions" aria-label="Ações do episódio">
        <a className="btn btn--primary" href={audioUrl(id, true)} download={`${slugify(script.title)}.mp3`}>
          <IconDownload /> Baixar MP3{ep.audio ? <span className="btn__meta mono">{formatBytes(ep.audio.bytes)}</span> : null}
        </a>
        <ShareMenu data={{ title: script.title, shareUrl: link, audioUrl: audioUrl(id), fileName: `${slugify(script.title)}.mp3` }} />
        <button type="button" className="btn" onClick={onCopy}><IconLink /> Copiar link</button>
        <div className="actions__files">
          <a className="btn btn--ghost" href={fileUrl(id, "script.md")}>Roteiro (.md)</a>
          <a className="btn btn--ghost" href={fileUrl(id, "verification.md")}>Verificação (.md)</a>
          <a className="btn btn--ghost" href={fileUrl(id, "sources.md")}>Fontes (.md)</a>
        </div>
        <Link className="btn btn--ghost" to="/"><IconPlus /> Novo episódio</Link>
      </nav>

      <p className="expiry">Este episódio fica disponível por 24 h. Baixe para guardar.</p>

      <SourceChips sources={ep.sources} />

      <div className="episode__body">
        <VerificationPanel items={script.verification} verdict={script.verdict} hideVerdict />
        <section aria-labelledby="transcript-title">
          <h2 id="transcript-title" className="section-title">Transcrição</h2>
          <ScriptEditor script={script} sources={ep.sources} onTurnChange={() => undefined} readOnly />
        </section>
      </div>
    </div>
  );
}
