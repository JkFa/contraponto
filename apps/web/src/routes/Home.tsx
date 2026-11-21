import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createEpisode, health } from "../api/client";
import type { CreateEpisodeForm, Mode, Tone } from "../api/types";
import { BRAND } from "../brand";
import { Composer } from "../components/Composer";
import { ConfrontoInput } from "../components/ConfrontoInput";
import { HistoryRail } from "../components/HistoryRail";
import { ModeSwitch } from "../components/ModeSwitch";
import { draftError, draftToInput, emptyDraft, type SourceDraft } from "../components/SourceField";
import { getGeminiKey, rememberForm, setGeminiKey, upsertHistory } from "../lib/storage";

const DURATIONS = [3, 5, 8, 12] as const;
const TONES: { id: Tone; label: string }[] = [
  { id: "analitico", label: "Analítico" },
  { id: "descontraido", label: "Descontraído" },
  { id: "provocativo", label: "Provocativo, com respeito" },
];

type Wake = "unknown" | "ok" | "waking" | "down";

export default function Home() {
  const navigate = useNavigate();
  const [primary, setPrimary] = useState<SourceDraft>(emptyDraft());
  const [confrontoOpen, setConfrontoOpen] = useState(false);
  const [confronto, setConfronto] = useState<SourceDraft>(emptyDraft("text"));
  const [mode, setMode] = useState<Mode>("react");
  const [thesis, setThesis] = useState("");
  const [focus, setFocus] = useState("");
  const [duration, setDuration] = useState<(typeof DURATIONS)[number]>(5);
  const [tone, setTone] = useState<Tone>("analitico");
  const [host1, setHost1] = useState("Davi");
  const [host2, setHost2] = useState("Lia");
  const [apiKey, setApiKey] = useState(() => getGeminiKey());
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wake, setWake] = useState<Wake>("unknown");

  useEffect(() => {
    let done = false;
    const slow = window.setTimeout(() => { if (!done) setWake("waking"); }, 2500);
    health()
      .then(() => setWake("ok"))
      .catch(() => setWake("down"))
      .finally(() => { done = true; window.clearTimeout(slow); });
    return () => window.clearTimeout(slow);
  }, []);

  const primaryInput = draftToInput(primary);
  const confrontoInput = confrontoOpen ? draftToInput(confronto) : null;
  const thesisMissing = mode === "critica" && !thesis.trim();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setError(null);
    if (!primaryInput) {
      setError(draftError(primary) ?? "Cole um link ou um texto. O resto é com a gente.");
      document.querySelector<HTMLElement>("#composer-title + * [role=tab][aria-selected=true], .source input, .source textarea")?.focus();
      return;
    }
    if (confrontoOpen && draftError(confronto)) {
      setError(draftError(confronto));
      return;
    }
    if (thesisMissing) {
      setError("No modo Crítica, escreva a sua tese (pode ser em tópicos soltos).");
      document.getElementById("thesis")?.focus();
      return;
    }
    setGeminiKey(apiKey);
    const form: CreateEpisodeForm = {
      mode,
      primary: primaryInput,
      confronto: confrontoInput,
      thesis: mode === "critica" ? thesis : undefined,
      focus_points: mode === "react" ? focus : undefined,
      duration_min: duration,
      tone,
      host1_name: host1,
      host2_name: host2,
    };
    setSending(true);
    try {
      const { id } = await createEpisode(form);
      rememberForm(id, form);
      upsertHistory({ id, title: "Episódio em preparo", created_at: new Date().toISOString(), status: "pending" });
      navigate(`/e/${id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Algo deu errado. Tente de novo.");
      setSending(false);
    }
  };

  return (
    <div className="home">
      <div className="home__main">
        <header className="hero">
          <h1 className="hero__title">{BRAND.tagline}</h1>
          <p className="hero__sub">{BRAND.subtitle}</p>
        </header>

        {wake === "waking" && (
          <p className="banner" role="status">Acordando o estúdio… leva até um minuto na primeira vez.</p>
        )}
        {wake === "down" && (
          <p className="banner banner--error" role="alert">
            O estúdio não respondeu. Confira sua conexão ou tente de novo em instantes.
          </p>
        )}

        <form className="composer" onSubmit={onSubmit} noValidate>
          <Composer draft={primary} onChange={setPrimary} disabled={sending} showErrors={submitted} />
          <ConfrontoInput open={confrontoOpen} onOpenChange={setConfrontoOpen} draft={confronto}
            onChange={setConfronto} disabled={sending} showErrors={submitted} />

          <hr className="rule" />

          <ModeSwitch value={mode} onChange={setMode} disabled={sending} />

          {mode === "critica" ? (
            <div className="field">
              <label className="field__label" htmlFor="thesis">Sua tese</label>
              <textarea id="thesis" className="textarea" rows={4} maxLength={2000} value={thesis}
                disabled={sending} aria-invalid={submitted && thesisMissing ? true : undefined}
                aria-describedby="thesis-hint"
                placeholder="Ex.: o vídeo confunde correlação com causa; os números de 2019 estão desatualizados."
                onChange={(e) => setThesis(e.target.value)} />
              <p id="thesis-hint" className="field__hint">
                Pode ser em tópicos soltos. <span className="mono">{thesis.length}/2000</span>
              </p>
            </div>
          ) : (
            <div className="field">
              <label className="field__label" htmlFor="focus">Pontos de atenção <span className="dim">(opcional)</span></label>
              <textarea id="focus" className="textarea" rows={2} maxLength={2000} value={focus} disabled={sending}
                placeholder="Algo que você quer que a IA olhe com mais cuidado."
                onChange={(e) => setFocus(e.target.value)} />
            </div>
          )}

          <details className="settings">
            <summary>Ajustes</summary>
            <div className="settings__grid">
              <fieldset className="field">
                <legend className="field__label">Duração</legend>
                <div className="segmented">
                  {DURATIONS.map((d) => (
                    <label key={d} className={duration === d ? "is-selected" : ""}>
                      <input type="radio" name="duration" className="visually-hidden" checked={duration === d}
                        onChange={() => setDuration(d)} />
                      {d} min
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="field settings__wide">
                <label className="field__label" htmlFor="tone">Tom</label>
                <select id="tone" className="select" value={tone} onChange={(e) => setTone(e.target.value as Tone)}>
                  {TONES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
              </div>
              <div className="field">
                <label className="field__label" htmlFor="host1">Apresentador 1</label>
                <input id="host1" className="input" maxLength={40} value={host1} onChange={(e) => setHost1(e.target.value)} />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="host2">Apresentadora 2</label>
                <input id="host2" className="input" maxLength={40} value={host2} onChange={(e) => setHost2(e.target.value)} />
              </div>
              <div className="field settings__wide">
                <label className="field__label" htmlFor="apikey">Usar minha chave Gemini <span className="dim">(opcional)</span></label>
                <input id="apikey" className="input mono" type="password" autoComplete="off" value={apiKey}
                  placeholder="AIza…" aria-describedby="apikey-hint" onChange={(e) => setApiKey(e.target.value)} />
                <p id="apikey-hint" className="field__hint">
                  Fica guardada só neste navegador e vai direto para o estúdio a cada pedido. Nunca é registrada.
                </p>
              </div>
            </div>
          </details>

          <div className="composer__submit">
            <button type="submit" className="btn btn--primary btn--big" disabled={sending}>
              {sending ? "Enviando…" : "Gerar roteiro"}
            </button>
            {error && <p className="field__error" role="alert">{error}</p>}
            <p className="fineprint">
              O roteiro sai para a sua revisão antes de virar áudio. As vozes são sintéticas. O conteúdo enviado
              (fonte e confronto) passa por um serviço de IA gratuito que pode usá-lo para melhorar seus produtos:
              não envie material confidencial.
            </p>
          </div>
        </form>
      </div>
      <HistoryRail />
    </div>
  );
}
