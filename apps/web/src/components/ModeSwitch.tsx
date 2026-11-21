import type { Mode } from "../api/types";

const OPTIONS: { id: Mode; title: string; line: string }[] = [
  { id: "critica", title: "Crítica", line: "Você traz a tese" },
  { id: "react", title: "React", line: "A IA dá a opinião" },
];

/** Two big selectable cards. Native radios give arrow-key navigation for free. */
export function ModeSwitch({ value, onChange, disabled }: { value: Mode; onChange: (m: Mode) => void; disabled?: boolean }) {
  return (
    <fieldset className="modes" role="radiogroup" aria-label="Modo do episódio" disabled={disabled}>
      <legend className="block__title">Modo</legend>
      <div className="modes__grid">
        {OPTIONS.map((o) => (
          <label key={o.id} className={`mode${value === o.id ? " is-selected" : ""}`}>
            <input type="radio" name="mode" value={o.id} checked={value === o.id}
              onChange={() => onChange(o.id)} className="visually-hidden" />
            <span className="mode__title">{o.title}</span>
            <span className="mode__line">{o.line}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
