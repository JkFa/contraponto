import { fallbackLinks, shareEpisode, shareText } from "../lib/share";

const data = { title: "Ep", shareUrl: "https://x/s/1", audioUrl: "https://x/a.mp3", fileName: "ep.mp3" };
const fetcher = vi.fn(async () => ({ blob: async () => new Blob(["mp3"], { type: "audio/mpeg" }) })) as unknown as typeof fetch;

describe("shareEpisode fallback order", () => {
  it("1) shares the MP3 file when canShare({files}) is true", async () => {
    const share = vi.fn(async () => undefined);
    const nav = { canShare: () => true, share } as unknown as Navigator;
    expect(await shareEpisode(data, nav, fetcher)).toBe("shared-file");
    const arg = (share.mock.calls[0] as unknown as [ShareData])[0];
    expect(arg.files?.[0]?.name).toBe("ep.mp3");
    expect(arg.url).toBe("https://x/s/1");
  });
  it("2) shares the URL when files are not shareable", async () => {
    const share = vi.fn(async () => undefined);
    const nav = { canShare: () => false, share } as unknown as Navigator;
    expect(await shareEpisode(data, nav, fetcher)).toBe("shared-url");
    const arg = (share.mock.calls[0] as unknown as [ShareData])[0];
    expect(arg.files).toBeUndefined();
    expect(arg.text).toBe(shareText("Ep", "https://x/s/1"));
  });
  it("3) falls back to the desktop menu without navigator.share", async () => {
    expect(await shareEpisode(data, {} as Navigator, fetcher)).toBe("fallback");
  });
  it("treats AbortError as a silent cancel", async () => {
    const nav = { share: vi.fn(async () => { throw new DOMException("x", "AbortError"); }) } as unknown as Navigator;
    expect(await shareEpisode(data, nav, fetcher)).toBe("cancelled");
  });
  it("rethrows other errors", async () => {
    const nav = { share: vi.fn(async () => { throw new Error("boom"); }) } as unknown as Navigator;
    await expect(shareEpisode(data, nav, fetcher)).rejects.toThrow("boom");
  });
  it("builds fallback links without hashtags", () => {
    const links = fallbackLinks("Ep", "https://x/s/1");
    expect(links.map((l) => l.label)).toEqual(["WhatsApp", "Telegram", "E-mail", "X/Twitter"]);
    expect(links[0]!.href).toContain(encodeURIComponent("🎙️ Ep — ouça o episódio: https://x/s/1"));
    expect(links.every((l) => !l.href.includes("%23"))).toBe(true);
  });
});
