/* Cotação — regras puras: validação e montagem da mensagem do WhatsApp. Sem DOM. */
import { bareDomain } from "./util.js";

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/**
 * Valida os dados do formulário. Devolve { errors: [texto...], fields: { nome, email, produto } }
 * com `true` nos campos inválidos. O primeiro erro é o que o site mostra.
 */
export function validateQuote(d, consentOk, T) {
  const fields = {
    nome: String(d.nome || "").trim().length < 2,
    email: !EMAIL_RE.test(String(d.email || "").trim()),
    produto: !d.produto,
  };
  const errors = [];
  if (fields.nome) errors.push(T.err_name);
  if (fields.email) errors.push(T.err_email);
  if (fields.produto) errors.push(T.err_product);
  if (!consentOk) errors.push(T.err_consent);
  return { errors, fields };
}

/** Monta o texto da mensagem no idioma do visitante. Linhas vazias só entre blocos. */
export function buildMessage(d, T, { lang = "en", domain = "" } = {}) {
  const lines = [T.wa_greeting || "Hello GBC Foods, I would like a quote.", ""];
  const add = (label, v) => {
    if (v) lines.push(`${label}: ${v}`);
  };
  add(T.product, d.produtoNome);
  add(T.volume, d.volume);
  add(T.incoterm, d.incoterm);
  add(T.port, d.portoDestino);
  add(T.window, d.janelaEmbarque);
  add(T.payment, d.condPagamento);
  add(T.message, d.mensagem);
  lines.push("");
  add(T.name, d.nome);
  add(T.company, d.empresa);
  add(T.email, d.email);
  add(T.phone, d.telefone);
  add(T.country, d.pais);
  lines.push("", `(${bareDomain(domain)}/${lang})`);
  return lines.join("\n");
}

/** URL do WhatsApp com a mensagem já codificada. */
export function whatsappUrl(number, text) {
  return `https://wa.me/${number || ""}?text=${encodeURIComponent(text)}`;
}

/** Corpo enviado ao ERP (função site-lead). */
export function leadPayload(d, { lang, page }) {
  return {
    tipo: "cotacao",
    idioma: lang,
    nome: d.nome,
    empresa: d.empresa,
    email: d.email,
    telefone: d.telefone,
    pais: d.pais,
    produto: d.produtoNome,
    volume: d.volume,
    incoterm: d.incoterm,
    portoDestino: d.portoDestino,
    janelaEmbarque: d.janelaEmbarque,
    condPagamento: d.condPagamento,
    mensagem: d.mensagem,
    pagina: page,
    website: d.website,
  };
}
