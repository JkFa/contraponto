import { useEffect } from "react";
import { Link } from "react-router-dom";
import { getEpisode } from "../api/client";
import { episodeHref, useHistory } from "../components/HistoryRail";
import { formatDate } from "../lib/format";
import { markHistory, removeHistory } from "../lib/storage";

const LABEL = { ready: "pronto", script_ready: "roteiro em revisão", pending: "em preparo", expired: "expirado" } as const;

export default function History() {
  const list = useHistory();

  useEffect(() => {
    getHistoryStatuses(list.filter((e) => e.status !== "expired").map((e) => e.id));
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page page--narrow">
      <h1 className="page__title">Histórico</h1>
      <p className="dim page__lead">Episódios gerados neste navegador. O estúdio guarda cada um por 24 horas.</p>
      {list.length === 0 ? (
        <div className="empty-state">
          <p>Nenhum episódio ainda. Cole um link ou um texto. O resto é com a gente.</p>
          <Link className="btn btn--primary" to="/">Novo episódio</Link>
        </div>
      ) : (
        <ul className="history">
          {list.map((e) => (
            <li key={e.id} className={e.status === "expired" ? "is-expired" : ""}>
              {e.status === "expired" ? (
                <span className="history__name">{e.title}</span>
              ) : (
                <Link className="history__name" to={episodeHref(e)}>{e.title}</Link>
              )}
              <span className="history__meta mono">{formatDate(e.created_at)} · {LABEL[e.status ?? "pending"]}</span>
              <button type="button" className="btn btn--ghost btn--small" onClick={() => removeHistory(e.id)}
                aria-label={`Remover "${e.title}" do histórico`}>Remover</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function getHistoryStatuses(ids: string[]): void {
  ids.forEach((id) => {
    getEpisode(id)
      .then((ep) => {
        const status = ep.status === "ready" ? "ready" : ep.status === "script_ready" ? "script_ready" : "pending";
        markHistory(id, { status, ...(ep.script ? { title: ep.script.title } : {}) });
      })
      .catch((err: { status?: number }) => {
        if (err.status === 404) markHistory(id, { status: "expired" });
      });
  });
}
