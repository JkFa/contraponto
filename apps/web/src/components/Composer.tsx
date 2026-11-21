import { SourceField, type SourceDraft } from "./SourceField";

interface Props {
  draft: SourceDraft;
  onChange: (d: SourceDraft) => void;
  disabled?: boolean;
  showErrors?: boolean;
}

/** Primary source (required). */
export function Composer({ draft, onChange, disabled, showErrors }: Props) {
  return (
    <section className="block" aria-labelledby="composer-title">
      <div className="block__head">
        <h2 id="composer-title" className="block__title">Fonte primária</h2>
        <p className="block__hint">O material que vai ser examinado.</p>
      </div>
      <SourceField label="Fonte primária" draft={draft} onChange={onChange} disabled={disabled}
        showErrors={showErrors} />
    </section>
  );
}
