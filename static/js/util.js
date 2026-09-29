/* Utilitários puros — sem acesso ao DOM. Testáveis unitariamente. */

/** Lê um cookie de uma string `document.cookie`. */
export function readCookie(cookieString, name) {
  const m = String(cookieString || "").match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

/** Monta o valor de `document.cookie` para gravar um cookie que dura `days` dias. */
export function cookieString(name, value, days, { secure = false, now = new Date() } = {}) {
  const d = new Date(now.getTime() + days * 864e5);
  return `${name}=${encodeURIComponent(value)}; expires=${d.toUTCString()}; path=/; SameSite=Lax${secure ? "; Secure" : ""}`;
}

export function getCookie(name) {
  return readCookie(document.cookie, name);
}

export function setCookie(name, value, days) {
  document.cookie = cookieString(name, value, days, { secure: location.protocol === "https:" });
}

/** Extrai o domínio de uma URL para exibição (sem protocolo). */
export function bareDomain(url) {
  return String(url || "").replace(/^https?:\/\//, "");
}

/**
 * URL do loader do Sentry a partir do DSN (https://<chave>@o<org>.ingest.sentry.io/<projeto>).
 * Devolve "" para DSN inválido — e aí nada é carregado.
 */
export function sentryLoaderUrl(dsn) {
  const m = /^https:\/\/([a-f0-9]{16,})@/i.exec(String(dsn || ""));
  return m ? `https://js.sentry-cdn.com/${m[1]}.min.js` : "";
}

/** Ambiente para a telemetria: production no domínio oficial, preview em workers.dev, development no resto. */
export function environmentFor(host, domain) {
  const official = bareDomain(domain).replace(/\/.*$/, "");
  if (host === official || host === `www.${official}`) return "production";
  if (/\.workers\.dev$/.test(host)) return "preview";
  return "development";
}

/**
 * Um clique num link vai carregar outra página deste site? (Serve para a barra de progresso de navegação.)
 * `a` precisa de target/hasAttribute/getAttribute/host/pathname/search/hash; `e` do evento (botão e modificadores).
 */
export function isInternalNavigation(a, e, loc) {
  if (e.defaultPrevented || e.button !== 0) return false;
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return false;
  if (a.target && a.target !== "_self") return false;
  if (a.hasAttribute("download")) return false;
  const href = a.getAttribute("href") || "";
  if (!href || href.startsWith("#") || /^(mailto|tel|javascript):/i.test(href)) return false;
  if (a.host && a.host !== loc.host) return false;
  if (a.pathname === loc.pathname && a.search === loc.search && a.hash) return false;
  return true;
}
