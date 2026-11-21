import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = (p: P): P => ({
  width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true, ...p,
});

export const IconPlay = (p: P) => <svg {...base(p)}><path d="M7 4.5v15l13-7.5z" fill="currentColor" stroke="none" /></svg>;
export const IconPause = (p: P) => <svg {...base(p)}><path d="M7 4h3.5v16H7zM13.5 4H17v16h-3.5z" fill="currentColor" stroke="none" /></svg>;
export const IconBack15 = (p: P) => <svg {...base(p)}><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 4v5h5" /><text x="12" y="15.5" fontSize="7.5" textAnchor="middle" fill="currentColor" stroke="none" fontFamily="sans-serif" fontWeight="700">15</text></svg>;
export const IconFwd15 = (p: P) => <svg {...base(p)}><path d="M21 12a9 9 0 1 1-3-6.7" /><path d="M21 4v5h-5" /><text x="12" y="15.5" fontSize="7.5" textAnchor="middle" fill="currentColor" stroke="none" fontFamily="sans-serif" fontWeight="700">15</text></svg>;
export const IconDownload = (p: P) => <svg {...base(p)}><path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 19.5h14" /></svg>;
export const IconShare = (p: P) => <svg {...base(p)}><path d="M12 15V4m0 0L8 8m4-4 4 4M5 13v6h14v-6" /></svg>;
export const IconLink = (p: P) => <svg {...base(p)}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" /></svg>;
export const IconClose = (p: P) => <svg {...base(p)}><path d="M6 6l12 12M18 6 6 18" /></svg>;
export const IconPlus = (p: P) => <svg {...base(p)}><path d="M12 5v14M5 12h14" /></svg>;
export const IconFile = (p: P) => <svg {...base(p)}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /></svg>;
export const IconRefresh = (p: P) => <svg {...base(p)}><path d="M20 11a8 8 0 0 0-14.3-4.9L4 8" /><path d="M4 4v4h4" /><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16" /><path d="M20 20v-4h-4" /></svg>;
export const IconMic = (p: P) => <svg {...base(p)}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></svg>;
export const IconSun = (p: P) => <svg {...base(p)}><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4" /></svg>;
export const IconMoon = (p: P) => <svg {...base(p)}><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" /></svg>;

/* Status marks: shape differs per status so color is never the only signal. */
export const MarkApoiada = (p: P) => <svg {...base({ width: 14, height: 14, strokeWidth: 2.6, ...p })}><path d="M4.5 12.5 10 18 19.5 6.5" /></svg>;
export const MarkContestada = (p: P) => <svg {...base({ width: 14, height: 14, strokeWidth: 2.6, ...p })}><path d="M6 6l12 12M18 6 6 18" /></svg>;
export const MarkParcial = (p: P) => <svg {...base({ width: 14, height: 14, strokeWidth: 2.2, ...p })}><circle cx="12" cy="12" r="8" /><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" /></svg>;
export const MarkNaoVerificavel = (p: P) => <svg {...base({ width: 14, height: 14, strokeWidth: 2.4, ...p })}><path d="M9 9a3 3 0 1 1 4 2.8c-.7.3-1 .9-1 1.7V14" /><circle cx="12" cy="18" r=".6" fill="currentColor" /></svg>;
