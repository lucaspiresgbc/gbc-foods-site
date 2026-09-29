import { describe, expect, it } from "vitest";
import {
  buildMessage,
  EMAIL_RE,
  leadPayload,
  validateQuote,
  whatsappUrl,
} from "../../static/js/quote-message.js";

const T = {
  err_name: "Informe o nome",
  err_email: "E-mail inválido",
  err_product: "Escolha o produto",
  err_consent: "Aceite a política",
  wa_greeting: "Olá, GBC Foods. Gostaria de uma cotação.",
  product: "Produto",
  volume: "Volume",
  incoterm: "Incoterm",
  port: "Porto",
  window: "Janela",
  payment: "Pagamento",
  message: "Mensagem",
  name: "Nome",
  company: "Empresa",
  email: "E-mail",
  phone: "Telefone",
  country: "País",
};

const full = {
  nome: "Ana",
  empresa: "Importadora X",
  email: "ana@x.com",
  telefone: "+34 600",
  pais: "Espanha",
  produto: "coffee-arabica",
  produtoNome: "Café verde arábica",
  volume: "2 x 40' HC",
  incoterm: "CIF",
  portoDestino: "Valencia",
  janelaEmbarque: "Nov 2026",
  condPagamento: "LC",
  mensagem: "Peneira 17/18",
  website: "",
};

describe("validateQuote", () => {
  it("aceita dados completos", () => {
    expect(validateQuote(full, true, T)).toEqual({
      errors: [],
      fields: { nome: false, email: false, produto: false },
    });
  });
  it("marca nome curto, e-mail inválido e produto ausente, na ordem", () => {
    const r = validateQuote({ nome: "A", email: "x@", produto: "" }, true, T);
    expect(r.errors).toEqual([T.err_name, T.err_email, T.err_product]);
    expect(r.fields).toEqual({ nome: true, email: true, produto: true });
  });
  it("exige o consentimento por último", () => {
    const r = validateQuote(full, false, T);
    expect(r.errors).toEqual([T.err_consent]);
  });
  it("tolera espaços e campos ausentes", () => {
    expect(validateQuote({ nome: "  Jo  ", email: " a@b.co ", produto: "x" }, true, T).errors).toEqual([]);
    expect(validateQuote({}, true, T).errors).toHaveLength(3);
  });
  it("EMAIL_RE recusa espaços e TLD de 1 letra", () => {
    expect(EMAIL_RE.test("a@b.c")).toBe(false);
    expect(EMAIL_RE.test("a b@c.de")).toBe(false);
    expect(EMAIL_RE.test("comprador@empresa.com.br")).toBe(true);
  });
});

describe("buildMessage", () => {
  it("monta a mensagem completa, com linha em branco entre blocos e a origem no fim", () => {
    const m = buildMessage(full, T, { lang: "pt", domain: "https://gbc-foods.com" });
    const lines = m.split("\n");
    expect(lines[0]).toBe(T.wa_greeting);
    expect(lines[1]).toBe("");
    expect(lines).toContain("Produto: Café verde arábica");
    expect(lines).toContain("Incoterm: CIF");
    expect(lines).toContain("Mensagem: Peneira 17/18");
    expect(lines).toContain("País: Espanha");
    expect(lines[lines.length - 1]).toBe("(gbc-foods.com/pt)");
    expect(lines[lines.length - 2]).toBe("");
  });
  it("omite campos vazios em vez de escrever 'Volume: '", () => {
    const m = buildMessage({ nome: "Ana", produtoNome: "Açúcar" }, T, {
      lang: "en",
      domain: "gbc-foods.com",
    });
    expect(m).not.toContain("Volume:");
    expect(m).not.toContain("Empresa:");
    expect(m).toContain("Produto: Açúcar");
    expect(m).toContain("Nome: Ana");
    expect(m.endsWith("(gbc-foods.com/en)")).toBe(true);
  });
  it("usa saudação padrão em inglês quando falta tradução", () => {
    const m = buildMessage({}, {}, {});
    expect(m.startsWith("Hello GBC Foods, I would like a quote.")).toBe(true);
    expect(m.endsWith("(/en)")).toBe(true);
  });
});

describe("whatsappUrl", () => {
  it("codifica o texto e usa o número", () => {
    expect(whatsappUrl("5513999", "Olá & tchau")).toBe("https://wa.me/5513999?text=Ol%C3%A1%20%26%20tchau");
  });
  it("tolera número ausente", () => {
    expect(whatsappUrl("", "x")).toBe("https://wa.me/?text=x");
    expect(whatsappUrl(undefined, "x")).toBe("https://wa.me/?text=x");
  });
});

describe("leadPayload", () => {
  it("mapeia os campos para os nomes da função site-lead", () => {
    const p = leadPayload(full, { lang: "es", page: "https://gbc-foods.com/es/cotizacion/" });
    expect(p).toMatchObject({
      tipo: "cotacao",
      idioma: "es",
      nome: "Ana",
      produto: "Café verde arábica",
      portoDestino: "Valencia",
      pagina: "https://gbc-foods.com/es/cotizacion/",
      website: "",
    });
    expect(Object.keys(p)).toHaveLength(16);
    expect(p).not.toHaveProperty("produtoNome");
  });
});
