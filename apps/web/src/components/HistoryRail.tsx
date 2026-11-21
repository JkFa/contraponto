import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory, type HistoryEntry } from "../lib/storage";
import { formatDate } from "../lib/format";

export function useHistory(): HistoryEntry[] {
  const [list, setList] = useState<HistoryEntry[]>(() => getHistory());
  useEffect(() => {
    const sync = () => setList(getHistory());
    window.addEventListener("contraponto:history", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("contraponto:history", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return list;
}

export function episodeHref(e: HistoryEntry): string {
  if (e.status === "ready") return `/e/${e.id}/ouvir`;
  if (e.status === "script_ready") return `/e/${e.id}/revisar`;
  return `/e/${e.id}`;
}

export function HistoryRail() {
  const list = useHistory().slice(0, 6);
  return (
    <aside className="rail" aria-labelledby="rail-title">
      <h2 id="rail-title" className="rail__title">Últimos episódios</h2>
      {list.length === 0 ? (
        <p className="rail__empty">Os episódios que você gerar aparecem aqui, neste navegador.</p>
      ) : (
        <ul className="rail__list">
          {list.map((e) => (
            <li key={e.id}>
              <Link to={episodeHref(e)} className={e.status === "expired" ? "is-expired" : ""}>
                <span className="rail__name">{e.title}</span>
                <span className="rail__date mono">{e.status === "expired" ? "expirado" : formatDate(e.created_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {list.length > 0 && <Link className="rail__all" to="/historico">Ver todo o histórico</Link>}
    </aside>
  );
}
