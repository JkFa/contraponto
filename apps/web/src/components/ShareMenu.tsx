import { useEffect, useRef, useState } from "react";
import { copyText, fallbackLinks, shareEpisode, type ShareData } from "../lib/share";
import { IconLink, IconShare } from "./Icons";
import { useToast } from "./Toast";

/** Native share (file → URL) with a desktop fallback menu (docs/05 §6). */
export function ShareMenu({ data }: { data: ShareData }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const onShare = async () => {
    try {
      const result = await shareEpisode(data);
      if (result === "fallback") setOpen((v) => !v);
    } catch {
      toast.show("Não consegui abrir o compartilhamento. Copie o link no lugar.", "error");
      setOpen(true);
    }
  };

  const onCopy = async () => {
    const ok = await copyText(data.shareUrl);
    toast.show(ok ? "Link copiado." : "Não consegui copiar. Selecione o link e copie manualmente.", ok ? "success" : "error");
    setOpen(false);
  };

  return (
    <div className="share" ref={wrap}>
      <button type="button" className="btn" onClick={onShare} aria-haspopup="menu" aria-expanded={open}>
        <IconShare /> Compartilhar
      </button>
      {open && (
        <div className="share__menu" role="menu" aria-label="Compartilhar episódio">
          <button type="button" role="menuitem" onClick={onCopy}><IconLink width={18} height={18} /> Copiar link</button>
          {fallbackLinks(data.title, data.shareUrl).map((l) => (
            <a key={l.label} role="menuitem" href={l.href} target="_blank" rel="noopener noreferrer"
              onClick={() => setOpen(false)}>{l.label}</a>
          ))}
        </div>
      )}
    </div>
  );
}
