import { SourceField, draftSummary, emptyDraft, type SourceDraft } from "./SourceField";
import { IconClose, IconPlus } from "./Icons";

interface Props {
  open: boolean;
  draft: SourceDraft;
  onOpenChange: (open: boolean) => void;
  onChange: (d: SourceDraft) => void;
  disabled?: boolean;
  showErrors?: boolean;
}

/** Optional confronto material. Collapsed by default; removable chip when filled. */
export function ConfrontoInput({ open, draft, onOpenChange, onChange, disabled, showErrors }: Props) {
  const summary = draftSummary(draft);
  const remove = () => {
    onChange(emptyDraft());
    onOpenChange(false);
  };

  if (!open) {
    return (
      <section className="block block--quiet" aria-labelledby="confronto-title">
        <h2 id="confronto-title" className="visually-hidden">Material de confronto</h2>
        <button type="button" className="btn btn--ghost confronto__add" onClick={() => onOpenChange(true)}
          aria-expanded="false" aria-controls="confronto-body" disabled={disabled}>
          <IconPlus /> Adicionar material de confronto
        </button>
        <p className="block__hint">Sem confronto, a IA examina a consistência interna da fonte.</p>
      </section>
    );
  }

  return (
    <section className="block block--confronto" aria-labelledby="confronto-title" id="confronto-body">
      <div className="block__head">
        <h2 id="confronto-title" className="block__title">Material de confronto</h2>
        {summary ? (
          <span className="chip chip--removable">
            {summary}
            <button type="button" onClick={remove} aria-label="Remover material de confronto" disabled={disabled}>
              <IconClose width={16} height={16} />
            </button>
          </span>
        ) : (
          <button type="button" className="btn btn--ghost btn--small" onClick={remove} disabled={disabled}>
            Fechar
          </button>
        )}
      </div>
      <p className="block__hint">Um texto, link ou arquivo para checar o que a fonte primária afirma.</p>
      <SourceField label="Material de confronto" draft={draft} onChange={onChange} disabled={disabled}
        showErrors={showErrors}
        textPlaceholder="Cole um artigo divergente, dados oficiais, uma errata ou suas notas." />
      <p className="block__hint">
        Este material também passa pelo serviço de IA gratuito, que pode usá-lo para melhorar seus produtos. Não envie
        nada confidencial.
      </p>
    </section>
  );
}
