import { expect, test } from "@playwright/test";

const LANGS = ["en", "pt", "es", "ru"];

/**
 * Clica num botão do banner de cookies. O banner é `position: fixed` no rodapé e entra com transição; na emulação
 * móvel do Chromium, o "scroll into view" do Playwright desloca a viewport visual (visualViewport.offsetTop) e o
 * ponto do clique cai no conteúdo atrás do banner — artefato da emulação, não do site (no navegador real e no
 * hit-test da própria página o alvo é o botão). Por isso: espera a transição assentar e dispara o clique direto.
 */
async function clickBanner(page, id) {
  const banner = page.locator("#cookie");
  await expect(banner).toBeVisible();
  await banner.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished.catch(() => {}))));
  await page.locator(`#${id}`).dispatchEvent("click");
}

test.describe("idioma", () => {
  test("a raiz redireciona pelo idioma do navegador e a escolha fica no cookie", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "es-ES" });
    const page = await ctx.newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/es\/$/);
    await ctx.close();
  });

  test("cookie gbc_lang manda mais que o navegador", async ({ browser, baseURL }) => {
    const ctx = await browser.newContext({ locale: "en-US" });
    await ctx.addCookies([{ name: "gbc_lang", value: "ru", url: baseURL }]);
    const page = await ctx.newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/ru\/$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    await ctx.close();
  });

  test("idioma sem correspondência cai no padrão (en)", async ({ browser }) => {
    const ctx = await browser.newContext({ locale: "ja-JP" });
    const page = await ctx.newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/en\/$/);
    await ctx.close();
  });

  for (const lang of LANGS) {
    test(`home em ${lang} carrega sem erro de JS e com o seletor dos 4 idiomas`, async ({ page }) => {
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(`/${lang}/`);
      await expect(page.locator("h1")).toBeVisible();
      for (const other of LANGS) {
        await expect(page.locator(`.lang-list a[data-lang="${other}"]`)).toHaveCount(1);
      }
      expect(errors).toEqual([]);
    });
  }
});

test.describe("navegação", () => {
  test("submenu de Serviços leva aos produtos a granel; ficha de produto tem breadcrumbs e cotação pré-preenchida", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/pt/");
    if (isMobile) {
      await page.click("#burger");
      await page.click(".has-sub .sub-toggle");
    } else {
      await page.hover(".has-sub > a");
    }
    await page.click('.sub a[href="/pt/produtos/a-granel/"]');
    await expect(page).toHaveURL(/\/pt\/produtos\/a-granel\/$/);
    await page.click(".pcard h3 a >> nth=0");
    await expect(page.locator(".crumbs")).toContainText("Produtos");
    const quote = page.locator('a[href^="/pt/cotacao/?produto="]').first();
    await expect(quote).toBeVisible();
    await quote.click();
    await expect(page.locator("[name=produto]")).not.toHaveValue("");
  });

  test("página 404 é multilíngue e não indexável", async ({ page }) => {
    const res = await page.goto("/404.html");
    expect(res.ok()).toBe(true);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
    for (const lang of LANGS) await expect(page.locator(`a[href="/${lang}/"]`).first()).toBeVisible();
  });

  test("sitemap e robots existem", async ({ request }) => {
    const sm = await request.get("/sitemap.xml");
    expect(sm.ok()).toBe(true);
    expect(await sm.text()).toContain("<urlset");
    const rb = await request.get("/robots.txt");
    expect(await rb.text()).toContain("Sitemap:");
  });
});

test.describe("cotação", () => {
  test("monta a mensagem no idioma, abre o WhatsApp e mostra o botão de reabrir", async ({ page }) => {
    await page.goto("/es/cotizacion/");
    await clickBanner(page, "cookie-reject");
    await page.evaluate(() => {
      window.__opened = [];
      window.open = (u) => {
        window.__opened.push(u);
        return { opener: null };
      };
    });
    await page.fill("[name=nome]", "Ana Pérez");
    await page.fill("[name=empresa]", "Importadora X");
    await page.fill("[name=email]", "ana@example.com");
    await page.selectOption("[name=produto]", { index: 1 });
    await page.fill("[name=volume]", "2 x 40' HC");
    await page.check("[name=consent]");
    await page.click("#quote-form button[type=submit]");
    const opened = await page.evaluate(() => window.__opened);
    expect(opened).toHaveLength(1);
    const text = decodeURIComponent(opened[0].replace(/^https:\/\/wa\.me\/\d*\?text=/, ""));
    expect(text).toContain("Ana Pérez");
    expect(text).toContain("2 x 40' HC");
    expect(text.trim().endsWith("/es)")).toBe(true);
    await expect(page.locator("#form-status a.btn")).toBeVisible();
    await expect(page.locator("#form-status")).toHaveClass(/pop/);
  });

  test("validação: sem e-mail válido não abre nada e marca o campo", async ({ page }) => {
    await page.goto("/en/quote/");
    await clickBanner(page, "cookie-reject");
    await page.evaluate(() => {
      window.__opened = 0;
      window.open = () => {
        window.__opened++;
        return {};
      };
    });
    await page.fill("[name=nome]", "QA");
    await page.fill("[name=email]", "nope");
    await page.check("[name=consent]");
    await page.click("#quote-form button[type=submit]");
    await expect(page.locator("[name=email]")).toHaveClass(/invalid/);
    await expect(page.locator("#form-status")).toHaveClass(/err/);
    expect(await page.evaluate(() => window.__opened)).toBe(0);
  });
});

test.describe("consentimento", () => {
  test("banner aparece, 'só essenciais' grava o cookie e nada do Google carrega", async ({
    page,
    context,
  }) => {
    const external = [];
    page.on("request", (r) => {
      if (/googletagmanager|google-analytics|sentry/.test(r.url())) external.push(r.url());
    });
    await page.goto("/pt/");
    await clickBanner(page, "cookie-reject");
    await expect(page.locator("#cookie")).toBeHidden();
    const cookies = await context.cookies();
    expect(cookies.find((c) => c.name === "gbc_consent")?.value).toBe("essential");
    await page.goto("/pt/empresa/");
    await expect(page.locator("#cookie")).toBeHidden();
    expect(external).toEqual([]);
  });

  test("'Gerenciar cookies' no rodapé reabre o banner", async ({ page }) => {
    await page.goto("/en/");
    await clickBanner(page, "cookie-accept");
    await expect(page.locator("#cookie")).toBeHidden();
    await page.click("#manage-cookies");
    await expect(page.locator("#cookie")).toBeVisible();
  });
});

test.describe("motion e carregamento", () => {
  test("imagens perdem o skeleton ao carregar; blocos abaixo da dobra entram ao rolar", async ({ page }) => {
    await page.goto("/pt/produtos/");
    await clickBanner(page, "cookie-reject");
    await expect(page.locator("html")).toHaveClass(/js/);
    const first = page.locator("picture").first();
    await expect(first).toHaveClass(/is-loaded/);
    const cards = page.locator(".grid3 > *");
    const last = cards.last();
    const lastInBefore = await last.evaluate((el) => el.classList.contains("in"));
    expect(lastInBefore).toBe(false); // ainda fora da tela: escondido até rolar
    await cards.first().scrollIntoViewIfNeeded();
    await expect(cards.first()).toHaveClass(/in/);
    await expect(cards.first()).toHaveAttribute("style", /--i:\s*0/);
    await last.scrollIntoViewIfNeeded();
    await expect(last).toHaveClass(/in/);
  });

  test("com movimento reduzido tudo fica visível de imediato", async ({ browser }) => {
    const ctx = await browser.newContext({ reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto("/pt/produtos/");
    const total = await page.locator(".grid3 > *").count();
    await expect(page.locator(".grid3 > *.in")).toHaveCount(total);
    const opacity = await page
      .locator("picture img")
      .first()
      .evaluate((el) => getComputedStyle(el).opacity);
    expect(opacity).toBe("1");
    await ctx.close();
  });

  test("sem JavaScript nada fica escondido", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/en/products/");
    const card = page.locator(".grid3 > *").first();
    expect(await card.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
    expect(
      await page
        .locator("picture img")
        .first()
        .evaluate((el) => getComputedStyle(el).opacity),
    ).toBe("1");
    await ctx.close();
  });

  test("artigo do blog tem a barra de leitura e a home tem a barra de progresso", async ({ page }) => {
    await page.goto("/pt/blog/");
    await page.click(".bcard h3 a >> nth=0");
    await expect(page.locator("body")).toHaveClass(/post-page/);
    await expect(page.locator("#progress")).toHaveCount(1);
  });
});

test.describe("landing de produto (Issue #24)", () => {
  test("a página do café conta a origem, mostra as etapas e chega na cotação", async ({ page }) => {
    await page.goto("/pt/produtos/cafe-verde-arabica/");

    // a origem
    const origem = page.locator("section.origem");
    await expect(origem).toHaveCount(1);
    await expect(origem.locator("h2")).toContainText("Sudoeste de Minas");
    await expect(origem.locator(".origem-foto img")).toBeVisible();

    // três etapas numeradas, cada uma com foto e texto
    const etapas = page.locator(".etapa");
    await expect(etapas).toHaveCount(3);
    for (let i = 0; i < 3; i++) {
      await expect(etapas.nth(i).locator(".etapa-foto img")).toHaveAttribute("alt", /.+/);
      await expect(etapas.nth(i).locator("h3")).not.toBeEmpty();
    }

    // certificação em nome da GBC, sem imagem de selo
    const cert = page.locator("section.certificacao");
    await expect(cert).toContainText("Rainforest");
    await expect(cert).toContainText("Fairtrade");
    await expect(cert.locator("img")).toHaveCount(0);

    // a landing termina levando para a cotação daquele produto
    await page.locator('.spec-card a[href*="produto=coffee-arabica"]').click();
    await expect(page).toHaveURL(/cotacao/);
  });

  test("o amendoim revela os blocos ao rolar e não repete foto", async ({ page }) => {
    await page.goto("/pt/produtos/amendoim-runner-cru/");
    const etapas = page.locator(".etapa");
    await expect(etapas).toHaveCount(3);
    await etapas.last().scrollIntoViewIfNeeded();
    await expect(etapas.last()).toHaveClass(/\bin\b/, { timeout: 4000 });

    const fontes = await page
      .locator(".origem-foto img, .etapa-foto img")
      .evaluateAll((els) => els.map((el) => el.getAttribute("src")));
    expect(new Set(fontes).size).toBe(fontes.length);
  });

  test("um produto sem story continua na ficha antiga", async ({ page }) => {
    await page.goto("/pt/produtos/acucar-cristal/");
    await expect(page.locator("section.origem")).toHaveCount(0);
    await expect(page.locator(".spec-card")).toHaveCount(1);
  });
});
