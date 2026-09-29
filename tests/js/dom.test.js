/* Módulos que tocam o DOM, testados em happy-dom: consentimento, navegação, motion, observabilidade, formulário. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BANNER_DELAY_MS, initConsent, onConsentAll } from "../../static/js/consent.js";
import {
  initImageSkeletons,
  initNavigationProgress,
  initReveal,
  MAX_STAGGER,
  PROGRESS_DELAY_MS,
  REVEAL_SELECTOR,
  staggerIndex,
} from "../../static/js/motion.js";
import { initLanguage, initMenu } from "../../static/js/nav.js";
import { initObservability, loadSentry, sentryOptions } from "../../static/js/observability.js";
import { initQuoteForm } from "../../static/js/quote-form.js";

function clearCookies() {
  for (const c of document.cookie.split(";")) {
    const name = c.split("=")[0].trim();
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
}

beforeEach(() => {
  document.body.innerHTML = "";
  document.head.innerHTML = "";
  clearCookies();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  delete window.__gbcGA;
  delete window.__gbcSentry;
  delete window.sentryOnLoad;
});

describe("consent", () => {
  const html = `
    <div id="cookie" hidden><button id="cookie-accept"></button><button id="cookie-reject"></button></div>
    <button id="manage-cookies"></button>`;

  it("sem cookie: mostra o banner depois do atraso e não carrega o Analytics", () => {
    document.body.innerHTML = html;
    initConsent({ ga: "G-TEST", lang: "pt" });
    expect(document.getElementById("cookie").hidden).toBe(true);
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    expect(document.getElementById("cookie").hidden).toBe(false);
    expect(document.body.classList.contains("has-cookie")).toBe(true);
    expect(document.querySelector("script[src*='googletagmanager']")).toBeNull();
  });

  it("aceitar todos: grava o cookie, esconde o banner, carrega o gtag uma vez e avisa os ouvintes", () => {
    document.body.innerHTML = html;
    const spy = vi.fn();
    onConsentAll(spy);
    initConsent({ ga: "G-TEST", lang: "pt" });
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    document.getElementById("cookie-accept").click();
    expect(document.cookie).toContain("gbc_consent=all");
    expect(document.getElementById("cookie").hidden).toBe(true);
    expect(document.querySelectorAll("script[src*='googletagmanager']")).toHaveLength(1);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(window.dataLayer.some((a) => a[0] === "consent" && a[1] === "update")).toBe(true);
  });

  it("só essenciais: grava o cookie e não carrega nada; gerenciar reabre já", () => {
    document.body.innerHTML = html;
    initConsent({ ga: "G-TEST", lang: "pt" });
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    document.getElementById("cookie-reject").click();
    expect(document.cookie).toContain("gbc_consent=essential");
    expect(document.querySelector("script[src*='googletagmanager']")).toBeNull();
    window.scrollTo = vi.fn();
    document.getElementById("manage-cookies").click();
    vi.advanceTimersByTime(0);
    expect(document.getElementById("cookie").hidden).toBe(false);
  });

  it("cookie 'all' de visita anterior: carrega o Analytics sem banner; sem ID de GA não injeta script", () => {
    document.cookie = "gbc_consent=all; path=/";
    document.body.innerHTML = html;
    initConsent({ ga: "", lang: "pt" });
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    expect(document.getElementById("cookie").hidden).toBe(true);
    expect(document.querySelector("script[src*='googletagmanager']")).toBeNull();
  });

  it("onConsentAll chama já quando o cookie é 'all'", () => {
    document.cookie = "gbc_consent=all; path=/";
    const spy = vi.fn();
    onConsentAll(spy);
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("Consent Mode: padrão tudo negado com espera de 500 ms; config do gtag com IP anônimo e idioma", () => {
    document.body.innerHTML = html;
    window.dataLayer = [];
    initConsent({ ga: "G-TEST", lang: "es" });
    const def = window.dataLayer.find((a) => a[0] === "consent" && a[1] === "default")[2];
    expect(def).toEqual({
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
      analytics_storage: "denied",
      wait_for_update: 500,
    });
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    document.getElementById("cookie-accept").click();
    const cfg = window.dataLayer.find((a) => a[0] === "config");
    expect(cfg[1]).toBe("G-TEST");
    expect(cfg[2]).toEqual({ anonymize_ip: true, page_language: "es" });
    expect(window.dataLayer.some((a) => a[0] === "js" && a[1] instanceof Date)).toBe(true);
    const s = document.querySelector("script[src*='googletagmanager']");
    expect(s.async).toBe(true);
    expect(s.src).toBe("https://www.googletagmanager.com/gtag/js?id=G-TEST");
    expect(document.body.classList.contains("has-cookie")).toBe(false);
  });

  it("gerenciar cookies: reabre e rola até o fim; recusar tira a classe do body", () => {
    document.body.innerHTML = html;
    window.scrollTo = vi.fn();
    initConsent({ ga: "", lang: "pt" });
    vi.advanceTimersByTime(BANNER_DELAY_MS);
    document.getElementById("cookie-reject").click();
    expect(document.body.classList.contains("has-cookie")).toBe(false);
    document.getElementById("manage-cookies").click();
    vi.advanceTimersByTime(0);
    expect(window.scrollTo).toHaveBeenCalledWith({ top: document.body.scrollHeight });
    expect(document.body.classList.contains("has-cookie")).toBe(true);
  });

  it("sem banner na página, aceitar/recusar não quebra", () => {
    document.body.innerHTML = `<button id="cookie-accept"></button>`;
    initConsent({ ga: "", lang: "pt" });
    expect(() => document.getElementById("cookie-accept").click()).not.toThrow();
    expect(document.cookie).toContain("gbc_consent=all");
  });
});

describe("nav", () => {
  it("seletor de idioma abre, fecha com clique fora e com Escape, e grava o idioma escolhido", () => {
    document.body.innerHTML = `
      <div class="lang" id="lang"><button class="lang-btn" aria-expanded="false"></button>
      <ul><li><a data-lang="es" href="/es/">ES</a></li></ul></div>`;
    initLanguage();
    const box = document.getElementById("lang");
    const btn = box.querySelector(".lang-btn");
    btn.click();
    expect(box.classList.contains("open")).toBe(true);
    expect(btn.getAttribute("aria-expanded")).toBe("true");
    document.body.click();
    expect(box.classList.contains("open")).toBe(false);
    btn.click();
    box.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(box.classList.contains("open")).toBe(false);
    box
      .querySelector("a[data-lang]")
      .dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(document.cookie).toContain("gbc_lang=es");
  });

  it("menu móvel e submenus alternam estado e aria", () => {
    document.body.innerHTML = `
      <button id="burger" aria-expanded="false"></button><nav id="nav"></nav>
      <li class="has-sub"><button class="sub-toggle" aria-expanded="false"></button></li>`;
    initMenu();
    document.getElementById("burger").click();
    expect(document.getElementById("nav").classList.contains("open")).toBe(true);
    expect(document.body.style.overflow).toBe("hidden");
    document.getElementById("burger").click();
    expect(document.body.style.overflow).toBe("");
    document.querySelector(".sub-toggle").click();
    expect(document.querySelector(".has-sub").classList.contains("open")).toBe(true);
    expect(document.querySelector(".sub-toggle").getAttribute("aria-expanded")).toBe("true");
  });

  it("sem os elementos, não quebra", () => {
    expect(() => {
      initLanguage();
      initMenu();
    }).not.toThrow();
  });
});

describe("motion", () => {
  it("skeleton: imagem já carregada vira is-loaded instant; a outra só no load; erro também libera", () => {
    document.body.innerHTML = `<picture><img id="a"></picture><picture><img id="b"></picture><picture><img id="c"></picture><picture></picture>`;
    const a = document.getElementById("a");
    Object.defineProperty(a, "complete", { value: true });
    Object.defineProperty(a, "naturalWidth", { value: 640 });
    initImageSkeletons();
    expect(a.parentElement.className).toBe("is-loaded instant");
    const b = document.getElementById("b");
    expect(b.parentElement.classList.contains("is-loaded")).toBe(false);
    b.dispatchEvent(new Event("load"));
    expect(b.parentElement.className).toBe("is-loaded");
    document.getElementById("c").dispatchEvent(new Event("error"));
    expect(document.getElementById("c").parentElement.className).toBe("is-loaded instant");
  });

  it("staggerIndex conta por pai e limita a MAX_STAGGER", () => {
    document.body.innerHTML = `<div class="grid3">${"<div></div>".repeat(8)}</div><div class="grid3"><div></div></div>`;
    const counts = new Map();
    const first = [...document.querySelectorAll(".grid3")[0].children].map((el) => staggerIndex(el, counts));
    expect(first).toEqual([0, 1, 2, 3, 4, 5, 5, 5]);
    expect(MAX_STAGGER).toBe(5);
    expect(staggerIndex(document.querySelectorAll(".grid3")[1].firstElementChild, counts)).toBe(0);
  });

  it("reveal: sem IntersectionObserver, revela tudo; com ele, marca --i e revela ao intersectar", () => {
    document.body.innerHTML = `<div class="grid3"><div>1</div><div>2</div></div><div class="head"></div>`;
    initReveal(document, { matchMedia: () => ({ matches: false }) });
    expect(document.querySelectorAll(".in")).toHaveLength(3);

    document.body.innerHTML = `<div class="grid3"><div>1</div><div>2</div></div>`;
    let callback;
    const observed = [];
    class IO {
      constructor(cb) {
        callback = cb;
      }
      observe(el) {
        observed.push(el);
      }
      unobserve() {}
    }
    initReveal(document, { matchMedia: () => ({ matches: false }), IntersectionObserver: IO });
    expect(observed).toHaveLength(2);
    expect(observed[1].style.getPropertyValue("--i")).toBe("1");
    expect(document.querySelectorAll(".in")).toHaveLength(0);
    callback([
      { isIntersecting: true, target: observed[0] },
      { isIntersecting: false, target: observed[1] },
    ]);
    expect(observed[0].classList.contains("in")).toBe(true);
    expect(observed[1].classList.contains("in")).toBe(false);
  });

  it("reveal: movimento reduzido revela tudo sem observar", () => {
    document.body.innerHTML = `<div class="grid3"><div>1</div></div>`;
    initReveal(document, { matchMedia: () => ({ matches: true }), IntersectionObserver: class {} });
    expect(document.querySelector(".grid3>div").classList.contains("in")).toBe(true);
    expect(REVEAL_SELECTOR).toContain(".grid3>*");
  });

  it("barra de progresso: liga só após o atraso em link interno; some no pageshow; ignora link externo", () => {
    document.body.innerHTML = `<div id="progress"></div><a id="in" href="/pt/produtos/">x</a><a id="out" href="https://wa.me/1" target="_blank">y</a>`;
    const win = {
      location: { host: "localhost", pathname: "/pt/", search: "" },
      setTimeout,
      clearTimeout,
      addEventListener: vi.fn(),
    };
    initNavigationProgress(document, win);
    document
      .getElementById("out")
      .dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    vi.advanceTimersByTime(PROGRESS_DELAY_MS + 50);
    expect(document.getElementById("progress").classList.contains("on")).toBe(false);
    const a = document.getElementById("in");
    Object.defineProperty(a, "host", { value: "localhost" });
    a.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    vi.advanceTimersByTime(PROGRESS_DELAY_MS - 1);
    expect(document.getElementById("progress").classList.contains("on")).toBe(false);
    vi.advanceTimersByTime(2);
    expect(document.getElementById("progress").classList.contains("on")).toBe(true);
    const pageshow = win.addEventListener.mock.calls.find((c) => c[0] === "pageshow")[1];
    pageshow();
    expect(document.getElementById("progress").classList.contains("on")).toBe(false);
  });

  it("barra de progresso: sem o elemento, não registra nada", () => {
    const win = { addEventListener: vi.fn() };
    initNavigationProgress(document, win);
    expect(win.addEventListener).not.toHaveBeenCalled();
  });
});

describe("observability", () => {
  const G = {
    lang: "ru",
    domain: "https://gbc-foods.com",
    release: "abc1234",
    sentry: { dsn: "https://0123456789abcdef0123456789abcdef@o1.ingest.sentry.io/1", tracesSampleRate: 0.5 },
  };

  it("sentryOptions: sem PII, sem replay, release, ambiente e idioma", () => {
    const o = sentryOptions(G, { host: "www.gbc-foods.com" });
    expect(o).toMatchObject({
      dsn: G.sentry.dsn,
      release: "abc1234",
      environment: "production",
      sendDefaultPii: false,
      tracesSampleRate: 0.5,
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 0,
      initialScope: { tags: { lang: "ru" } },
    });
    expect(
      sentryOptions({ ...G, release: "", sentry: { dsn: G.sentry.dsn } }, { host: "x" }).tracesSampleRate,
    ).toBe(0.2);
    expect(sentryOptions({ ...G, release: "" }, { host: "x" }).release).toBeUndefined();
  });

  it("loadSentry injeta o loader uma vez e define sentryOnLoad que chama Sentry.init", () => {
    const win = { location: { host: "gbc-foods.com" } };
    loadSentry(G, document, win);
    loadSentry(G, document, win);
    const scripts = document.querySelectorAll("script[src*='js.sentry-cdn.com']");
    expect(scripts).toHaveLength(1);
    expect(scripts[0].getAttribute("data-lazy")).toBe("no");
    expect(scripts[0].crossOrigin).toBe("anonymous");
    win.Sentry = { init: vi.fn() };
    win.sentryOnLoad();
    expect(win.Sentry.init).toHaveBeenCalledWith(expect.objectContaining({ environment: "production" }));
  });

  it("sem DSN: não injeta nada nem registra gancho", () => {
    loadSentry({ sentry: { dsn: "" } }, document, {});
    initObservability({ sentry: { dsn: "" } }, document, {});
    initObservability({}, document, {});
    expect(document.querySelector("script")).toBeNull();
  });

  it("com DSN e consentimento já dado: carrega na hora", () => {
    document.cookie = "gbc_consent=all; path=/";
    initObservability(G, document, { location: { host: "localhost" } });
    expect(document.querySelector("script[src*='js.sentry-cdn.com']")).not.toBeNull();
  });
});

describe("quote-form", () => {
  const T = {
    err_name: "nome",
    err_email: "email",
    err_product: "produto",
    err_consent: "consent",
    opening: "abrindo",
    sent: "enviado",
    open_again: "abrir",
    wa_greeting: "Oi",
    product: "Produto",
    name: "Nome",
    email: "E-mail",
  };
  const html = `
    <form id="quote-form">
      <input name="nome"><input name="email"><input name="empresa"><input name="telefone"><input name="pais">
      <select name="produto"><option value="">-</option><option value="coffee-arabica" data-name="Café">Café</option></select>
      <input name="volume"><input name="incoterm"><input name="portoDestino"><input name="janelaEmbarque"><input name="condPagamento">
      <textarea name="mensagem"></textarea><input name="website"><input type="checkbox" name="consent">
      <button type="submit">Enviar</button>
    </form><p id="form-status" class="form-status"></p>`;

  it("pré-seleciona o produto da URL quando existe na lista", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "?produto=coffee-arabica", href: "http://x/" });
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    expect(document.querySelector("[name=produto]").value).toBe("coffee-arabica");
  });

  it("produto desconhecido na URL fica vazio", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "?produto=nao-existe", href: "http://x/" });
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    expect(document.querySelector("[name=produto]").value).toBe("");
  });

  it("dados inválidos: mostra o primeiro erro, marca os campos e não abre nada", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    window.open = vi.fn();
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    document.getElementById("quote-form").dispatchEvent(new Event("submit", { cancelable: true }));
    const status = document.getElementById("form-status");
    expect(status.className).toBe("form-status err");
    expect(status.textContent).toBe("nome");
    expect(document.querySelector("[name=nome]").classList.contains("invalid")).toBe(true);
    expect(window.open).not.toHaveBeenCalled();
  });

  it("dados válidos: envia o lead por sendBeacon, abre o WhatsApp e mostra o botão de reabrir", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/pt/cotacao/" });
    const beacon = vi.fn(() => true);
    vi.stubGlobal("navigator", { ...navigator, sendBeacon: beacon });
    window.open = vi.fn(() => ({}));
    initQuoteForm({
      t: T,
      wa: "5513",
      lang: "pt",
      domain: "https://gbc-foods.com",
      lead: "https://lead.example/f",
    });
    document.querySelector("[name=nome]").value = "Ana";
    document.querySelector("[name=email]").value = "ana@x.com";
    document.querySelector("[name=produto]").value = "coffee-arabica";
    document.querySelector("[name=consent]").checked = true;
    document.getElementById("quote-form").dispatchEvent(new Event("submit", { cancelable: true }));
    expect(beacon).toHaveBeenCalledTimes(1);
    expect(beacon.mock.calls[0][0]).toBe("https://lead.example/f");
    expect(window.open).toHaveBeenCalledTimes(1);
    const url = window.open.mock.calls[0][0];
    expect(url.startsWith("https://wa.me/5513?text=Oi")).toBe(true);
    expect(decodeURIComponent(url)).toContain("Produto: Café");
    const status = document.getElementById("form-status");
    expect(status.classList.contains("pop")).toBe(true);
    expect(status.querySelector("a.btn").href).toBe(url);
    expect(status.textContent).toContain("enviado");
    expect(document.querySelector("button[type=submit]").classList.contains("is-loading")).toBe(false);
  });

  it("pop-up bloqueado: navega na mesma aba; sem sendBeacon usa fetch; sem endpoint não envia", () => {
    document.body.innerHTML = html;
    const loc = { ...window.location, search: "", href: "http://x/" };
    vi.stubGlobal("location", loc);
    const fetchMock = vi.fn(() => Promise.resolve());
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("navigator", { userAgent: "test" });
    window.open = vi.fn(() => null);
    initQuoteForm({
      t: T,
      wa: "5513",
      lang: "pt",
      domain: "https://gbc-foods.com",
      lead: "https://lead.example/f",
    });
    document.querySelector("[name=nome]").value = "Ana";
    document.querySelector("[name=email]").value = "ana@x.com";
    document.querySelector("[name=produto]").value = "coffee-arabica";
    document.querySelector("[name=consent]").checked = true;
    document.getElementById("quote-form").dispatchEvent(new Event("submit", { cancelable: true }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(loc.href.startsWith("https://wa.me/5513")).toBe(true);
  });

  it("sem formulário na página, não faz nada", () => {
    expect(() => initQuoteForm({ t: T })).not.toThrow();
  });

  function fill(over = {}) {
    document.querySelector("[name=nome]").value = over.nome ?? "Ana";
    document.querySelector("[name=email]").value = over.email ?? "ana@x.com";
    document.querySelector("[name=produto]").value = over.produto ?? "coffee-arabica";
    document.querySelector("[name=consent]").checked = over.consent ?? true;
  }
  const submit = () =>
    document.getElementById("quote-form").dispatchEvent(new Event("submit", { cancelable: true }));

  it("botão fica ocupado (is-loading + aria-busy) enquanto abre e volta ao normal depois; opener zerado", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    const popup = { opener: {} };
    let stateAtOpen = null;
    window.open = vi.fn(() => {
      const b = document.querySelector("button[type=submit]");
      stateAtOpen = { loading: b.classList.contains("is-loading"), busy: b.getAttribute("aria-busy") };
      return popup;
    });
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    fill();
    submit();
    expect(stateAtOpen).toEqual({ loading: true, busy: "true" });
    expect(popup.opener).toBeNull();
    const b = document.querySelector("button[type=submit]");
    expect(b.classList.contains("is-loading")).toBe(false);
    expect(b.hasAttribute("aria-busy")).toBe(false);
    expect(window.open).toHaveBeenCalledWith(
      expect.stringMatching(/^https:\/\/wa\.me\/5513\?text=/),
      "_blank",
    );
  });

  it("link de reabrir: nova aba, noopener, classe de botão; mensagem 'enviado' em span", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    window.open = vi.fn(() => ({}));
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    fill();
    submit();
    const a = document.querySelector("#form-status a");
    expect(a.target).toBe("_blank");
    expect(a.rel).toBe("noopener");
    expect(a.className).toBe("btn solid small");
    expect(a.textContent).toBe("abrir");
    expect(document.querySelector("#form-status span").textContent).toBe("enviado");
    expect(document.querySelector("#form-status br")).not.toBeNull();
  });

  it("usa o texto da opção quando não há data-name; textos padrão quando faltam traduções", () => {
    document.body.innerHTML = html.replace(' data-name="Café"', "");
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    window.open = vi.fn(() => ({}));
    initQuoteForm({ t: { product: "Produto" }, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    fill();
    submit();
    const url = decodeURIComponent(window.open.mock.calls[0][0]);
    expect(url).toContain("Produto: Café"); // nome vem do texto da <option>
    expect(document.querySelector("#form-status a").textContent).toBe("WhatsApp");
    expect(document.querySelector("#form-status span").textContent).toBe("");
  });

  it("erros por campo: e-mail e produto marcados; consentimento sem marcar campo; nova tentativa limpa as marcas", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    window.open = vi.fn(() => ({}));
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    fill({ email: "ruim", produto: "" });
    submit();
    expect(document.querySelector("[name=email]").classList.contains("invalid")).toBe(true);
    expect(document.querySelector("[name=produto]").classList.contains("invalid")).toBe(true);
    expect(document.querySelector("[name=nome]").classList.contains("invalid")).toBe(false);
    expect(document.getElementById("form-status").textContent).toBe("email");
    fill({ consent: false });
    submit();
    expect(document.getElementById("form-status").textContent).toBe("consent");
    expect(document.querySelector("[name=email]").classList.contains("invalid")).toBe(false);
    expect(document.querySelector("[name=produto]").classList.contains("invalid")).toBe(false);
    expect(window.open).not.toHaveBeenCalled();
    fill();
    submit();
    expect(document.getElementById("form-status").className).toBe("form-status pop");
    expect(window.open).toHaveBeenCalledTimes(1);
  });

  it("fetch de reserva envia JSON com POST e keepalive; falha do fetch não quebra o envio", () => {
    document.body.innerHTML = html;
    const loc = { ...window.location, search: "", href: "http://x/pt/" };
    vi.stubGlobal("location", loc);
    const fetchMock = vi.fn(() => Promise.reject(new Error("offline")));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("navigator", { userAgent: "test" });
    window.open = vi.fn(() => ({}));
    initQuoteForm({
      t: T,
      wa: "5513",
      lang: "pt",
      domain: "https://gbc-foods.com",
      lead: "https://lead.example/f",
    });
    fill();
    submit();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe("https://lead.example/f");
    expect(opts).toMatchObject({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      keepalive: true,
    });
    const body = JSON.parse(opts.body);
    expect(body).toMatchObject({
      tipo: "cotacao",
      idioma: "pt",
      nome: "Ana",
      produto: "Café",
      pagina: "http://x/pt/",
    });
    expect(window.open).toHaveBeenCalledTimes(1);
  });

  it("sendBeacon recebe um Blob text/plain com o JSON do lead", () => {
    document.body.innerHTML = html;
    vi.stubGlobal("location", { ...window.location, search: "", href: "http://x/" });
    const beacon = vi.fn(() => true);
    vi.stubGlobal("navigator", { ...navigator, sendBeacon: beacon });
    window.open = vi.fn(() => ({}));
    initQuoteForm({
      t: T,
      wa: "5513",
      lang: "en",
      domain: "https://gbc-foods.com",
      lead: "https://lead.example/f",
    });
    fill();
    submit();
    const blob = beacon.mock.calls[0][1];
    expect(blob.type).toBe("text/plain");
    expect(blob.size).toBeGreaterThan(50);
  });

  it("window.open que lança erro cai no mesmo fluxo de pop-up bloqueado", () => {
    document.body.innerHTML = html;
    const loc = { ...window.location, search: "", href: "http://x/" };
    vi.stubGlobal("location", loc);
    window.open = vi.fn(() => {
      throw new Error("bloqueado");
    });
    initQuoteForm({ t: T, wa: "5513", lang: "pt", domain: "https://gbc-foods.com" });
    fill();
    submit();
    expect(loc.href.startsWith("https://wa.me/5513")).toBe(true);
    expect(document.getElementById("form-status").classList.contains("pop")).toBe(true);
  });
});
