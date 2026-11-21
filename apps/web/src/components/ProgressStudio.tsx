import { OnAirSign } from "./OnAir";

interface Props {
  step: string;
  pct: number;
  phase: "script" | "audio";
  waking?: boolean;
}

const SCRIPT_STEPS = ["Lendo as fontes", "Cruzando as informações", "Escrevendo o roteiro"];
const AUDIO_STEPS = ["Gravando vozes", "Mixando"];

/** The studio while it works: lit sign, human step, thin tape bar. */
export function ProgressStudio({ step, pct, phase, waking }: Props) {
  const steps = phase === "script" ? SCRIPT_STEPS : AUDIO_STEPS;
  const current = phase === "script"
    ? (pct < 40 ? 0 : pct < 60 ? 1 : 2)
    : (pct < 90 ? 0 : 1);
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <section className="studio" aria-labelledby="studio-step">
      <OnAirSign live size="l" />
      <p id="studio-step" className="studio__step" aria-live="polite">
        {waking ? "Acordando o estúdio… leva até um minuto na primeira vez." : `${step}…`}
      </p>
      <div className="tape" role="progressbar" aria-label="Progresso" aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={clamped} aria-valuetext={`${clamped}%`}>
        <span className="tape__fill" style={{ width: `${clamped}%` }} />
      </div>
      <ol className="studio__steps" aria-label="Etapas">
        {steps.map((s, i) => (
          <li key={s} className={i < current ? "is-done" : i === current ? "is-now" : ""}
            aria-current={i === current ? "step" : undefined}>
            {s}
          </li>
        ))}
      </ol>
    </section>
  );
}
