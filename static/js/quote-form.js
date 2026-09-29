/* Formulário de cotação → WhatsApp (+ cópia silenciosa para o ERP). A parte pura está em quote-message.js. */
import { buildMessage, leadPayload, validateQuote, whatsappUrl } from "./quote-message.js";

function sendLead(G, d) {
  if (!G.lead) return;
  try {
    const body = JSON.stringify(leadPayload(d, { lang: G.lang, page: location.href }));
    if (navigator.sendBeacon) {
      navigator.sendBeacon(G.lead, new Blob([body], { type: "text/plain" }));
    } else {
      fetch(G.lead, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: true,
      }).catch(() => {});
    }
  } catch (_e) {
    /* o WhatsApp é o canal principal; a cópia para o ERP nunca bloqueia o envio */
  }
}

export function initQuoteForm(G, doc = document) {
  const form = doc.getElementById("quote-form");
  if (!form) return;
  const T = G.t || {};
  const status = doc.getElementById("form-status");
  const pre = new URLSearchParams(location.search).get("produto");
  if (pre) {
    const sel = form.querySelector("[name=produto]");
    if (sel) {
      sel.value = pre;
      if (sel.value !== pre) sel.value = "";
    }
  }

  const val = (n) => {
    const el = form.querySelector(`[name=${n}]`);
    return el ? String(el.value || "").trim() : "";
  };
  const mark = (n, bad) => {
    const el = form.querySelector(`[name=${n}]`);
    if (el) el.classList.toggle("invalid", !!bad);
  };
  const productName = () => {
    const sel = form.querySelector("[name=produto]");
    if (!sel?.value) return "";
    const opt = sel.options[sel.selectedIndex];
    return opt.getAttribute("data-name") || opt.textContent.trim();
  };

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    status.className = "form-status";
    status.textContent = "";
    const d = {
      nome: val("nome"),
      empresa: val("empresa"),
      email: val("email"),
      telefone: val("telefone"),
      pais: val("pais"),
      produto: val("produto"),
      produtoNome: productName(),
      volume: val("volume"),
      incoterm: val("incoterm"),
      portoDestino: val("portoDestino"),
      janelaEmbarque: val("janelaEmbarque"),
      condPagamento: val("condPagamento"),
      mensagem: val("mensagem"),
      website: val("website"),
    };
    const consentOk = form.querySelector("[name=consent]").checked;
    const { errors, fields } = validateQuote(d, consentOk, T);
    mark("nome", fields.nome);
    mark("email", fields.email);
    mark("produto", fields.produto);
    if (errors.length) {
      status.className = "form-status err";
      status.textContent = errors[0];
      return;
    }

    const url = whatsappUrl(G.wa, buildMessage(d, T, { lang: G.lang, domain: G.domain }));
    status.textContent = T.opening || "";
    sendLead(G, d);
    let w = null;
    try {
      w = window.open(url, "_blank");
      if (w) {
        try {
          w.opener = null;
        } catch (_e2) {
          /* alguns navegadores não deixam zerar o opener */
        }
      }
    } catch (_err) {
      w = null;
    }
    if (!w) location.href = url; // bloqueador de pop-up: abre na mesma aba
    status.innerHTML = "";
    const p = doc.createElement("span");
    p.textContent = T.sent || "";
    status.appendChild(p);
    const a = doc.createElement("a");
    a.className = "btn solid small";
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = T.open_again || "WhatsApp";
    status.appendChild(doc.createElement("br"));
    status.appendChild(a);
  });
}
