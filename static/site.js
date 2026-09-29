/* GBC Foods — comportamento do site: menu, idioma, cookies/consentimento, formulário de cotação. */
(function () {
  "use strict";
  var G = window.GBC || {};
  var T = G.t || {};

  // ---------- cookies utilitários
  function getCookie(name) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : null;
  }
  function setCookie(name, value, days) {
    var d = new Date(); d.setTime(d.getTime() + days * 864e5);
    document.cookie = name + "=" + encodeURIComponent(value) + "; expires=" + d.toUTCString() + "; path=/; SameSite=Lax" + (location.protocol === "https:" ? "; Secure" : "");
  }

  // ---------- idioma: lembra a escolha feita no seletor
  document.querySelectorAll("a[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () { setCookie("gbc_lang", a.getAttribute("data-lang"), 365); });
  });
  var langBox = document.getElementById("lang");
  if (langBox) {
    var langBtn = langBox.querySelector(".lang-btn");
    langBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = langBox.classList.toggle("open");
      langBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", function () { langBox.classList.remove("open"); langBtn.setAttribute("aria-expanded", "false"); });
    langBox.addEventListener("keydown", function (e) { if (e.key === "Escape") { langBox.classList.remove("open"); langBtn.focus(); } });
  }

  // ---------- menu móvel e submenus
  var burger = document.getElementById("burger"), nav = document.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      document.body.style.overflow = open ? "hidden" : "";
    });
  }
  document.querySelectorAll(".has-sub").forEach(function (li) {
    var btn = li.querySelector(".sub-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var open = li.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  });

  // ---------- consentimento (Google Consent Mode v2, modo básico: o gtag só carrega após aceite)
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  gtag("consent", "default", { ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied", analytics_storage: "denied", wait_for_update: 500 });

  function loadAnalytics() {
    if (!G.ga || window.__gbcGA) return;
    window.__gbcGA = true;
    gtag("consent", "update", { analytics_storage: "granted" });
    var s = document.createElement("script");
    s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(G.ga);
    document.head.appendChild(s);
    gtag("js", new Date());
    gtag("config", G.ga, { anonymize_ip: true, page_language: G.lang });
  }
  var banner = document.getElementById("cookie");
  function showBanner() { if (banner) { banner.hidden = false; document.body.classList.add("has-cookie"); } }
  function hideBanner() { if (banner) { banner.hidden = true; document.body.classList.remove("has-cookie"); } }
  function applyConsent(v) {
    setCookie("gbc_consent", v, 365);
    hideBanner();
    if (v === "all") loadAnalytics();
  }
  var consent = getCookie("gbc_consent");
  if (consent === "all") loadAnalytics();
  else if (consent !== "essential") showBanner();
  var acc = document.getElementById("cookie-accept"), rej = document.getElementById("cookie-reject"), man = document.getElementById("manage-cookies");
  if (acc) acc.addEventListener("click", function () { applyConsent("all"); });
  if (rej) rej.addEventListener("click", function () { applyConsent("essential"); });
  if (man) man.addEventListener("click", function () { showBanner(); window.scrollTo({ top: document.body.scrollHeight }); });

  // ---------- formulário de cotação → WhatsApp (+ cópia silenciosa para o ERP)
  var form = document.getElementById("quote-form");
  if (!form) return;
  var status = document.getElementById("form-status");
  var params = new URLSearchParams(location.search);
  var pre = params.get("produto");
  if (pre) { var sel = form.querySelector("[name=produto]"); if (sel) { sel.value = pre; if (sel.value !== pre) sel.value = ""; } }

  function val(n) { var el = form.querySelector("[name=" + n + "]"); return el ? String(el.value || "").trim() : ""; }
  function mark(n, bad) { var el = form.querySelector("[name=" + n + "]"); if (el) el.classList.toggle("invalid", !!bad); }
  function productName() {
    var sel = form.querySelector("[name=produto]");
    if (!sel || !sel.value) return "";
    var opt = sel.options[sel.selectedIndex];
    return opt.getAttribute("data-name") || opt.textContent.trim();
  }
  function buildMessage(d) {
    var lines = [T.wa_greeting || "Hello GBC Foods, I would like a quote.", ""];
    var add = function (label, v) { if (v) lines.push(label + ": " + v); };
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
    lines.push("", "(" + (G.domain || "").replace(/^https?:\/\//, "") + "/" + G.lang + ")");
    return lines.join("\n");
  }
  function sendLead(d) {
    if (!G.lead) return;
    try {
      var body = JSON.stringify({
        tipo: "cotacao", idioma: G.lang, nome: d.nome, empresa: d.empresa, email: d.email, telefone: d.telefone,
        pais: d.pais, produto: d.produtoNome, volume: d.volume, incoterm: d.incoterm, portoDestino: d.portoDestino,
        janelaEmbarque: d.janelaEmbarque, condPagamento: d.condPagamento, mensagem: d.mensagem,
        pagina: location.href, website: d.website
      });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(G.lead, new Blob([body], { type: "text/plain" }));
      } else {
        fetch(G.lead, { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true }).catch(function () {});
      }
    } catch (e) { /* o WhatsApp é o canal principal; a cópia para o ERP nunca bloqueia o envio */ }
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    status.className = "form-status"; status.textContent = "";
    var d = {
      nome: val("nome"), empresa: val("empresa"), email: val("email"), telefone: val("telefone"), pais: val("pais"),
      produto: val("produto"), produtoNome: productName(), volume: val("volume"), incoterm: val("incoterm"),
      portoDestino: val("portoDestino"), janelaEmbarque: val("janelaEmbarque"), condPagamento: val("condPagamento"),
      mensagem: val("mensagem"), website: val("website")
    };
    var consentOk = form.querySelector("[name=consent]").checked;
    var errors = [];
    mark("nome", d.nome.length < 2); if (d.nome.length < 2) errors.push(T.err_name);
    var emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(d.email);
    mark("email", !emailOk); if (!emailOk) errors.push(T.err_email);
    mark("produto", !d.produto); if (!d.produto) errors.push(T.err_product);
    if (!consentOk) errors.push(T.err_consent);
    if (errors.length) { status.className = "form-status err"; status.textContent = errors[0]; return; }

    var text = buildMessage(d);
    var url = "https://wa.me/" + (G.wa || "") + "?text=" + encodeURIComponent(text);
    status.textContent = T.opening || "";
    sendLead(d);
    var w = null;
    try { w = window.open(url, "_blank"); if (w) { try { w.opener = null; } catch (e2) {} } } catch (err) { w = null; }
    if (!w) location.href = url;   // bloqueador de pop-up: abre na mesma aba
    status.innerHTML = "";
    var p = document.createElement("span"); p.textContent = T.sent || ""; status.appendChild(p);
    var a = document.createElement("a"); a.className = "btn solid small"; a.href = url; a.target = "_blank"; a.rel = "noopener"; a.textContent = T.open_again || "WhatsApp";
    status.appendChild(document.createElement("br")); status.appendChild(a);
  });
})();
