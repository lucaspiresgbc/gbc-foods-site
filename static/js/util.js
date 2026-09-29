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
