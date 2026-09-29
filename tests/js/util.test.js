import { describe, expect, it } from "vitest";
import {
  bareDomain,
  cookieString,
  environmentFor,
  isInternalNavigation,
  readCookie,
  sentryLoaderUrl,
} from "../../static/js/util.js";

describe("readCookie", () => {
  it("lê um cookie no meio da string", () => {
    expect(readCookie("a=1; gbc_lang=pt; b=2", "gbc_lang")).toBe("pt");
  });
  it("lê o primeiro cookie e decodifica", () => {
    expect(readCookie("gbc_consent=all%20ok", "gbc_consent")).toBe("all ok");
  });
  it("devolve null quando não existe ou a string é vazia", () => {
    expect(readCookie("a=1", "gbc_lang")).toBeNull();
    expect(readCookie("", "gbc_lang")).toBeNull();
    expect(readCookie(undefined, "x")).toBeNull();
  });
  it("não confunde prefixo de nome", () => {
    expect(readCookie("xgbc_lang=en", "gbc_lang")).toBeNull();
  });
});

describe("cookieString", () => {
  const now = new Date("2026-09-29T12:00:00Z");
  it("monta nome, valor codificado, validade, path e SameSite", () => {
    const s = cookieString("gbc_lang", "pt", 365, { now });
    expect(s).toMatch(/^gbc_lang=pt; expires=.*GMT; path=\/; SameSite=Lax$/);
    expect(s).toContain("2027");
  });
  it("marca Secure só em https", () => {
    expect(cookieString("a", "b", 1, { now, secure: true })).toMatch(/; Secure$/);
    expect(cookieString("a", "b", 1, { now, secure: false })).not.toContain("Secure");
  });
  it("codifica o valor", () => {
    expect(cookieString("a", "x y;z", 1, { now })).toContain("a=x%20y%3Bz;");
  });
});

describe("bareDomain", () => {
  it("tira o protocolo", () => {
    expect(bareDomain("https://gbc-foods.com")).toBe("gbc-foods.com");
    expect(bareDomain("http://x.dev/")).toBe("x.dev/");
    expect(bareDomain("")).toBe("");
    expect(bareDomain(undefined)).toBe("");
  });
});

describe("sentryLoaderUrl", () => {
  it("deriva a chave pública do DSN", () => {
    expect(sentryLoaderUrl("https://0123456789abcdef0123456789abcdef@o1.ingest.us.sentry.io/42")).toBe(
      "https://js.sentry-cdn.com/0123456789abcdef0123456789abcdef.min.js",
    );
  });
  it("devolve vazio para DSN inválido ou ausente", () => {
    expect(sentryLoaderUrl("")).toBe("");
    expect(sentryLoaderUrl("https://curta@o1.ingest.sentry.io/1")).toBe("");
    expect(sentryLoaderUrl("http://0123456789abcdef0123456789abcdef@x/1")).toBe("");
    expect(sentryLoaderUrl(undefined)).toBe("");
  });
});

describe("environmentFor", () => {
  const domain = "https://gbc-foods.com";
  it("production no domínio oficial, com ou sem www", () => {
    expect(environmentFor("gbc-foods.com", domain)).toBe("production");
    expect(environmentFor("www.gbc-foods.com", domain)).toBe("production");
  });
  it("preview em workers.dev", () => {
    expect(environmentFor("gbc-foods-site.conta.workers.dev", domain)).toBe("preview");
  });
  it("development no resto", () => {
    expect(environmentFor("localhost:8811", domain)).toBe("development");
    expect(environmentFor("gbc-foods.com.evil.com", domain)).toBe("development");
  });
});

describe("isInternalNavigation", () => {
  const loc = { host: "gbc-foods.com", pathname: "/pt/", search: "" };
  const link = (over = {}) => ({
    target: "",
    host: "gbc-foods.com",
    pathname: "/pt/produtos/",
    search: "",
    hash: "",
    href: "https://gbc-foods.com/pt/produtos/",
    attrs: { href: "/pt/produtos/" },
    hasAttribute(n) {
      return n in this.attrs;
    },
    getAttribute(n) {
      return this.attrs[n] ?? null;
    },
    ...over,
  });
  const click = (over = {}) => ({
    defaultPrevented: false,
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    ...over,
  });

  it("link interno comum: sim", () => {
    expect(isInternalNavigation(link(), click(), loc)).toBe(true);
  });
  it("clique com modificador, botão do meio ou já tratado: não", () => {
    expect(isInternalNavigation(link(), click({ ctrlKey: true }), loc)).toBe(false);
    expect(isInternalNavigation(link(), click({ metaKey: true }), loc)).toBe(false);
    expect(isInternalNavigation(link(), click({ shiftKey: true }), loc)).toBe(false);
    expect(isInternalNavigation(link(), click({ altKey: true }), loc)).toBe(false);
    expect(isInternalNavigation(link(), click({ button: 1 }), loc)).toBe(false);
    expect(isInternalNavigation(link(), click({ defaultPrevented: true }), loc)).toBe(false);
  });
  it("target _blank ou download: não; target _self: sim", () => {
    expect(isInternalNavigation(link({ target: "_blank" }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ attrs: { href: "/x/", download: "" } }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ target: "_self" }), click(), loc)).toBe(true);
  });
  it("âncora na mesma página, mailto, tel, javascript e href vazio: não", () => {
    expect(isInternalNavigation(link({ attrs: { href: "#main" } }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ attrs: { href: "mailto:a@b.c" } }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ attrs: { href: "tel:+55" } }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ attrs: { href: "javascript:void(0)" } }), click(), loc)).toBe(false);
    expect(isInternalNavigation(link({ attrs: {} }), click(), loc)).toBe(false);
    expect(
      isInternalNavigation(
        link({ pathname: "/pt/", hash: "#topo", attrs: { href: "/pt/#topo" } }),
        click(),
        loc,
      ),
    ).toBe(false);
  });
  it("outro host: não", () => {
    expect(
      isInternalNavigation(link({ host: "wa.me", attrs: { href: "https://wa.me/55" } }), click(), loc),
    ).toBe(false);
  });
});
