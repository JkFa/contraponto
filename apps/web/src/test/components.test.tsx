import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { buildEpisodeFormData } from "../api/client";
import type { VerificationItem } from "../api/types";
import { ConfrontoInput } from "../components/ConfrontoInput";
import { ModeSwitch } from "../components/ModeSwitch";
import { ShareMenu } from "../components/ShareMenu";
import { draftToInput, emptyDraft, type SourceDraft } from "../components/SourceField";
import { ToastProvider } from "../components/Toast";
import { VerificationPanel, findRelatedTurn } from "../components/VerificationPanel";
import { Composer } from "../components/Composer";

function ConfrontoHarness({ onDraft }: { onDraft: (d: SourceDraft, open: boolean) => void }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<SourceDraft>(emptyDraft("text"));
  return (
    <ConfrontoInput open={open} draft={draft}
      onOpenChange={(o) => setOpen(o)}
      onChange={(d) => { setDraft(d); onDraft(d, open); }} />
  );
}

describe("ConfrontoInput", () => {
  it("is closed by default and shows the internal-exam hint", () => {
    render(<ConfrontoHarness onDraft={() => undefined} />);
    expect(screen.getByRole("button", { name: /adicionar material de confronto/i })).toBeInTheDocument();
    expect(screen.getByText(/sem confronto, a ia examina a consistência interna/i)).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("opens, fills the right FormData field, and removing clears it", async () => {
    const user = userEvent.setup();
    let last: { d: SourceDraft; open: boolean } = { d: emptyDraft("text"), open: false };
    render(<ConfrontoHarness onDraft={(d, open) => { last = { d, open }; }} />);
    await user.click(screen.getByRole("button", { name: /adicionar material de confronto/i }));
    await user.click(screen.getByRole("tab", { name: "Texto" }));
    await user.type(screen.getByLabelText(/material de confronto: texto/i), "Dados oficiais");
    const input = draftToInput(last.d);
    expect(input).toEqual({ kind: "text", text: "Dados oficiais" });

    const fd = buildEpisodeFormData({ mode: "react", primary: { kind: "text", text: "fonte" }, confronto: input });
    expect(fd.get("confronto_text")).toBe("Dados oficiais");
    expect(fd.get("confronto_youtube_url")).toBeNull();
    expect(fd.get("confronto_file")).toBeNull();

    await user.click(screen.getByRole("button", { name: /remover material de confronto/i }));
    expect(screen.getByRole("button", { name: /adicionar material de confronto/i })).toBeInTheDocument();
    expect(draftToInput(last.d)).toBeNull();
  });

  it("accepts only one kind of input at a time (active tab wins)", async () => {
    const user = userEvent.setup();
    let last = emptyDraft("text");
    render(<ConfrontoHarness onDraft={(d) => { last = d; }} />);
    await user.click(screen.getByRole("button", { name: /adicionar material de confronto/i }));
    await user.click(screen.getByRole("tab", { name: "Texto" }));
    await user.type(screen.getByLabelText(/material de confronto: texto/i), "abc");
    await user.click(screen.getByRole("tab", { name: "Link do YouTube" }));
    await user.type(screen.getByLabelText(/material de confronto: link/i), "https://youtu.be/dQw4w9WgXcQ");
    expect(draftToInput(last)).toEqual({ kind: "youtube", url: "https://youtu.be/dQw4w9WgXcQ" });
  });

  it("flags an invalid URL", async () => {
    const user = userEvent.setup();
    render(<ConfrontoHarness onDraft={() => undefined} />);
    await user.click(screen.getByRole("button", { name: /adicionar material de confronto/i }));
    await user.click(screen.getByRole("tab", { name: "Link do YouTube" }));
    const field = screen.getByLabelText(/material de confronto: link/i);
    await user.type(field, "https://evil.com/x");
    await user.tab();
    expect(screen.getByRole("alert")).toHaveTextContent("Esse link não parece ser do YouTube.");
    expect(field).toHaveAttribute("aria-invalid", "true");
  });
});

describe("Composer + FormData", () => {
  it("only includes filled fields", () => {
    const fd = buildEpisodeFormData({
      mode: "critica", primary: { kind: "youtube", url: " https://youtu.be/dQw4w9WgXcQ " }, thesis: "tese",
      focus_points: "ignorado", duration_min: 8,
    });
    expect([...fd.keys()].sort()).toEqual(["duration_min", "mode", "thesis", "youtube_url"]);
    expect(fd.get("youtube_url")).toBe("https://youtu.be/dQw4w9WgXcQ");
  });

  it("renders the three tabs for the primary source", () => {
    render(<Composer draft={emptyDraft()} onChange={() => undefined} />);
    const tabs = within(screen.getByRole("tablist", { name: "Fonte primária" })).getAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual(["Link do YouTube", "Texto", "Arquivo"]);
  });
});

describe("ModeSwitch", () => {
  it("is a keyboard-navigable radiogroup", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ModeSwitch value="react" onChange={onChange} />);
    expect(screen.getByRole("radiogroup", { name: /modo/i })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /crítica/i }));
    expect(onChange).toHaveBeenCalledWith("critica");
  });
});

const items: VerificationItem[] = [
  { claim: "O consumo de café cresceu trinta por cento", status: "apoiada", note: "n1", evidence_role: "confronto" },
  { claim: "Quem toma café vive mais", status: "contestada", note: "n2", evidence_role: "confronto" },
  { claim: "Amostra de duzentas pessoas", status: "parcial", note: "n3", evidence_role: "interna" },
  { claim: "Recomendação para crianças", status: "nao_verificavel", note: "n4", evidence_role: "interna" },
];

describe("VerificationPanel", () => {
  it("renders every status as stamp + text label (never color alone)", () => {
    render(<VerificationPanel items={items} verdict="Com base no que temos aqui…" />);
    for (const label of ["Apoiada", "Contestada", "Parcial", "Não verificável"]) {
      const stamp = screen.getAllByText(label).find((el) => el.classList.contains("stamp"));
      expect(stamp).toBeTruthy();
      expect(stamp!.querySelector("svg")).toBeTruthy();
    }
    expect(screen.getByText("Com base no que temos aqui…")).toBeInTheDocument();
  });

  it("calls onLocate with the item index", async () => {
    const user = userEvent.setup();
    const onLocate = vi.fn();
    render(<VerificationPanel items={items} verdict="v" onLocate={onLocate} />);
    await user.click(screen.getAllByRole("button", { name: "Ver no roteiro" })[1]!);
    expect(onLocate).toHaveBeenCalledWith(1);
  });

  it("shows an empty state", () => {
    render(<VerificationPanel items={[]} verdict="v" />);
    expect(screen.getByText(/veio sem verificação/i)).toBeInTheDocument();
  });

  it("finds the related turn by timestamp, then by word overlap", () => {
    const turns = [
      { speaker: "HOST_1" as const, kind: "contexto" as const, text: "Olá a todos" },
      { speaker: "HOST_2" as const, kind: "contexto" as const, text: "O consumo de café cresceu muito", source_ts: "01:00" },
      { speaker: "HOST_1" as const, kind: "opiniao" as const, text: "Viver mais tomando café? Calma." },
    ];
    expect(findRelatedTurn(items[0]!, turns)).toBe(1);
    expect(findRelatedTurn({ ...items[1]!, claim_ts: "01:00" }, turns)).toBe(1);
    expect(findRelatedTurn(items[1]!, turns)).toBe(2);
  });
});

describe("ShareMenu", () => {
  const data = { title: "Ep", shareUrl: "https://x/s/1" };
  const renderMenu = () => render(<MemoryRouter><ToastProvider><ShareMenu data={data} /></ToastProvider></MemoryRouter>);

  afterEach(() => {
    Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
  });

  it("shows the desktop fallback without navigator.share", async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, "share", { value: undefined, configurable: true });
    renderMenu();
    await user.click(screen.getByRole("button", { name: /compartilhar/i }));
    const menu = screen.getByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: /copiar link/i })).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: "WhatsApp" })).toHaveAttribute("href", expect.stringContaining("wa.me"));
  });

  it("does not toast an error when the user cancels", async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, "share", {
      value: vi.fn(async () => { throw new DOMException("x", "AbortError"); }), configurable: true,
    });
    renderMenu();
    await user.click(screen.getByRole("button", { name: /compartilhar/i }));
    expect(screen.queryByText(/não consegui/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
