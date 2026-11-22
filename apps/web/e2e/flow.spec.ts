import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const SCREENS = "../../docs/screens";
const PRIMARY =
  "O consumo de café cresceu trinta por cento no Brasil na última década. " +
  "Segundo o autor, todo mundo que toma café vive mais. " +
  "A pesquisa citada ouviu duzentas pessoas em uma única cidade. " +
  "Por isso, o café deveria ser recomendado a todas as crianças.";
const CONFRONTO =
  "Dados oficiais mostram que o consumo de café cresceu doze por cento no período. " +
  "Estudos de longo prazo não encontraram relação causal entre café e longevidade. " +
  "Pediatras não recomendam cafeína para crianças.";

const VIEWPORTS = [
  { name: "390", width: 390, height: 844 },
  { name: "1280", width: 1280, height: 800 },
];

async function axe(page: Page, label: string) {
  // Measure after entrance animations settle (infinite ones, like the NO AR glow, stay).
  await page.waitForFunction(() =>
    document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
  const result = await new AxeBuilder({ page }).analyze();
  const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious.map((v) => `${label}: ${v.id} — ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
}

async function noHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/${name}.png`, fullPage: true, animations: "disabled" });
}

for (const vp of VIEWPORTS) {
  test.describe(`viewport ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("crítica com confronto: home → revisão → episódio", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Cole um material. Ouça o exame." })).toBeVisible();
      await axe(page, "home");
      await noHorizontalScroll(page);
      await shot(page, `home-${vp.name}`);

      await page.getByRole("tab", { name: "Texto" }).first().click();
      await page.getByLabel("Fonte primária: texto").fill(PRIMARY);
      await page.getByRole("button", { name: "Adicionar material de confronto" }).click();
      await page.getByLabel("Material de confronto: texto").fill(CONFRONTO);
      await page.getByText("Crítica", { exact: true }).click();
      await page.getByLabel("Sua tese").fill("- confunde correlação com causa\n- amostra pequena");
      await page.getByText("Ajustes").click();
      await page.getByText("3 min").click();
      await noHorizontalScroll(page);
      await shot(page, `home-confronto-open-${vp.name}`);

      await page.getByRole("button", { name: "Gerar roteiro" }).click();
      await expect(page).toHaveURL(/#\/e\/[^/]+\/revisar$/, { timeout: 30_000 });
      await expect(page.getByRole("heading", { name: "Verificação" })).toBeVisible();
      for (const label of ["Apoiada", "Contestada", "Parcial", "Não verificável"]) {
        await expect(page.locator(".stamp", { hasText: label }).first()).toBeVisible();
      }
      await expect(page.locator(".chip--mono", { hasText: "confronto" }).first()).toBeVisible();
      await axe(page, "revisão");
      await noHorizontalScroll(page);
      await shot(page, `review-${vp.name}`);

      // locate a claim in the script
      await page.getByRole("button", { name: "Ver no roteiro" }).nth(1).click();
      await expect(page.locator(".turn.is-flash")).toHaveCount(1);

      // edit a line, approve, render
      const first = page.locator("#turn-text-0");
      await first.fill("Olá! Fala editada na revisão.");
      await expect(page.getByText("Alterações não salvas")).toBeVisible();
      await page.getByRole("button", { name: "Aprovar e gerar áudio" }).click();
      await expect(page).toHaveURL(/#\/e\/[^/]+\/ouvir$/, { timeout: 60_000 });
      await expect(page.getByText("No ar. Seu episódio está pronto.")).toBeVisible();
      await expect(page.getByText("Olá! Fala editada na revisão.")).toBeVisible();
      await expect(page.getByRole("button", { name: "Tocar" })).toBeVisible();
      await page.waitForTimeout(800); // waveform peaks
      await axe(page, "episódio");
      await noHorizontalScroll(page);
      await shot(page, `episode-${vp.name}`);

      const mp3 = page.getByRole("link", { name: /Baixar MP3/ });
      // A real browser download (Chromium engine, as in Brave/Chrome), not just headers.
      const [download] = await Promise.all([page.waitForEvent("download"), mp3.click()]);
      expect(download.suggestedFilename()).toMatch(/\.mp3$/);
      expect((await import("node:fs")).statSync((await download.path())!).size).toBeGreaterThan(1000);
      const href = await mp3.getAttribute("href");
      const res = await page.request.get(href!);
      expect(res.headers()["content-type"]).toBe("audio/mpeg");
      expect(res.headers()["content-disposition"]).toContain("attachment");
      const [verDownload] = await Promise.all([
        page.waitForEvent("download"),
        page.getByRole("link", { name: "Verificação (.md)" }).click(),
      ]);
      expect(verDownload.suggestedFilename()).toBe("verificacao.md");
      const verText = (await import("node:fs")).readFileSync((await verDownload.path())!, "utf-8");
      expect(verText).toContain("**Veredito:**");

      await page.goto("/#/historico");
      await expect(page.getByRole("heading", { name: "Histórico" })).toBeVisible();
      await axe(page, "histórico");
      await shot(page, `history-${vp.name}`);
    });

    test("react sem confronto: exame interno", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("tab", { name: "Texto" }).first().click();
      await page.getByLabel("Fonte primária: texto").fill(PRIMARY);
      await page.getByRole("button", { name: "Gerar roteiro" }).click();
      await expect(page).toHaveURL(/revisar$/, { timeout: 30_000 });
      await expect(page.getByText("por exame interno").first()).toBeVisible();
      await expect(page.getByText("pelo confronto")).toHaveCount(0);
      await expect(page.locator(".chip--kind.chip--confronto")).toHaveCount(0);
    });
  });
}

test.describe("estados do estúdio", () => {
  test("progresso com luz NO AR e painel 'cole o texto'", async ({ page }) => {
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.route("**/api/episodes/fake1", (r) =>
        r.fulfill({ json: { id: "fake1", status: "scripting", mode: "react", created_at: "", expires_at: "", sources: [] } }));
      await page.route("**/api/episodes/fake1/events", (r) =>
        r.fulfill({
          headers: { "content-type": "text/event-stream" },
          body: 'retry: 600000\nevent: progress\ndata: {"status":"scripting","step":"Cruzando as informações","pct":40}\n\n',
        }));
      await page.goto("/#/e/fake1");
      await expect(page.getByText("Cruzando as informações…")).toBeVisible();
      await expect(page.locator(".studio .onair.is-live")).toBeVisible();
      await axe(page, "estúdio");
      await noHorizontalScroll(page);
      await shot(page, `studio-${vp.name}`);

      await page.route("**/api/episodes/fake2", (r) =>
        r.fulfill({
          json: {
            id: "fake2", status: "failed", mode: "react", created_at: "", expires_at: "", sources: [],
            error: { code: "CONFRONTO_TRANSCRIPT_UNAVAILABLE", message: "Não consegui ler a transcrição do material de confronto. Cole o texto ou remova essa fonte." },
          },
        }));
      await page.goto("/#/e/fake2");
      await expect(page.getByRole("heading", { name: /material de confronto/ })).toBeVisible();
      await noHorizontalScroll(page);
      await shot(page, `studio-paste-${vp.name}`);
    }
  });

  test("backend dormindo mostra 'Acordando o estúdio'", async ({ page }) => {
    await page.route("**/api/health", async (r) => {
      await new Promise((res) => setTimeout(res, 4000));
      await r.fulfill({ json: { ok: true } });
    });
    await page.goto("/");
    await expect(page.getByText(/Acordando o estúdio/)).toBeVisible({ timeout: 6000 });
  });

  test("tema claro (papel)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await page.getByRole("button", { name: "Usar tema claro" }).click();
    await axe(page, "home claro");
    await shot(page, "home-light-1280");
  });
});
