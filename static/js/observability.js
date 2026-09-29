/* Observabilidade no navegador: Sentry (erros de JS, erros de recurso, Web Vitals) — só depois do consentimento.
 * Sem DSN em content/config.json nada é carregado nem referenciado. Trocar de fornecedor = trocar este módulo. */
import { onConsentAll } from "./consent.js";
import { environmentFor, sentryLoaderUrl } from "./util.js";

/** Configuração passada ao Sentry.init pelo loader (window.sentryOnLoad). Exportada para teste. */
export function sentryOptions(G, loc) {
  return {
    dsn: G.sentry.dsn,
    release: G.release || undefined,
    environment: environmentFor(loc.host, G.domain),
    sendDefaultPii: false,
    tracesSampleRate: Number(G.sentry.tracesSampleRate ?? 0.2),
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    ignoreErrors: [/ResizeObserver loop/, /Non-Error promise rejection captured/, /Load failed/],
    initialScope: { tags: { lang: G.lang || "" } },
  };
}

export function loadSentry(G, doc = document, win = window) {
  if (win.__gbcSentry || !G.sentry?.dsn) return;
  win.__gbcSentry = true;
  win.sentryOnLoad = () => {
    win.Sentry?.init(sentryOptions(G, win.location));
  };
  const s = doc.createElement("script");
  s.src = sentryLoaderUrl(G.sentry.dsn);
  s.crossOrigin = "anonymous";
  s.dataset.lazy = "no"; // com Web Vitals o SDK precisa carregar já, não só no primeiro erro
  doc.head.appendChild(s);
}

export function initObservability(G, doc = document, win = window) {
  if (!G.sentry?.dsn) return;
  onConsentAll(() => loadSentry(G, doc, win));
}
