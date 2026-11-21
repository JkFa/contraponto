export interface ShareData {
  title: string;
  shareUrl: string;
  audioUrl?: string;
  fileName?: string;
}

export type ShareResult = "shared-file" | "shared-url" | "fallback" | "cancelled";

export function shareText(title: string, url: string): string {
  return `🎙️ ${title} — ouça o episódio: ${url}`;
}

export function fallbackLinks(title: string, url: string): { label: string; href: string }[] {
  const text = shareText(title, url);
  const enc = encodeURIComponent;
  return [
    { label: "WhatsApp", href: `https://wa.me/?text=${enc(text)}` },
    { label: "Telegram", href: `https://t.me/share/url?url=${enc(url)}&text=${enc(`🎙️ ${title}`)}` },
    { label: "E-mail", href: `mailto:?subject=${enc(title)}&body=${enc(text)}` },
    { label: "X/Twitter", href: `https://twitter.com/intent/tweet?text=${enc(text)}` },
  ];
}

function isAbort(err: unknown): boolean {
  return typeof err === "object" && err !== null && (err as { name?: string }).name === "AbortError";
}

/**
 * Order (docs/05 §6): 1) share the MP3 file, 2) share the URL, 3) desktop fallback menu.
 * Throws for real errors; returns "cancelled" when the user dismisses the sheet.
 */
export async function shareEpisode(
  data: ShareData,
  nav: Navigator = navigator,
  fetcher: typeof fetch = fetch,
): Promise<ShareResult> {
  const text = shareText(data.title, data.shareUrl);
  const canShareFiles = typeof nav.canShare === "function" && typeof File !== "undefined";
  try {
    if (canShareFiles && data.audioUrl && typeof nav.share === "function") {
      const probe = new File([new Blob([""], { type: "audio/mpeg" })], data.fileName ?? "episodio.mp3", {
        type: "audio/mpeg",
      });
      if (nav.canShare({ files: [probe] })) {
        const blob = await (await fetcher(data.audioUrl)).blob();
        const file = new File([blob], data.fileName ?? "episodio.mp3", { type: "audio/mpeg" });
        await nav.share({ files: [file], title: data.title, text, url: data.shareUrl });
        return "shared-file";
      }
    }
    if (typeof nav.share === "function") {
      await nav.share({ title: data.title, text, url: data.shareUrl });
      return "shared-url";
    }
  } catch (err) {
    if (isAbort(err)) return "cancelled";
    throw err;
  }
  return "fallback";
}

export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}
