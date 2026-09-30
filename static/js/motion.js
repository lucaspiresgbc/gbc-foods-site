/* Motion: skeleton das imagens, revelação ao rolar e barra de progresso de navegação.
 * O CSS (static/motion.css) faz o movimento; este módulo só marca estados. Sem JS nada fica escondido. */
import { isInternalNavigation } from "./util.js";

/** Os mesmos seletores de motion.css — blocos que entram quando aparecem na tela. */
export const REVEAL_SELECTOR =
  ".grid3>*,.steps>li,.strip-grid>div,.duo>*,.head,.origin-row,.roof-card,.svc-item,.channel,.panel,.cup-photo,.cup h2,.cup .prose,.cta-in>*,.form,.spec-card,.mosaic-grid>*,.gallery>div,.two>*,.two-1>*,.coffee-text>*,.contact-photo,.mini-steps,.etapa,.origem-texto>*,.certificacao>.wrap>*";

export const MAX_STAGGER = 5;
export const PROGRESS_DELAY_MS = 300;

/** Marca cada <picture> como carregada (com ou sem fade) para o CSS tirar o skeleton. */
export function initImageSkeletons(doc = document) {
  for (const pic of doc.querySelectorAll("picture")) {
    const img = pic.querySelector("img");
    if (!img) continue;
    const done = (instant) => {
      pic.classList.add("is-loaded");
      if (instant) pic.classList.add("instant");
    };
    if (img.complete && img.naturalWidth > 0) done(true);
    else {
      img.addEventListener("load", () => done(false), { once: true });
      img.addEventListener("error", () => done(true), { once: true });
    }
  }
}

/** Índice de stagger: posição do elemento entre os irmãos revelados, limitado a MAX_STAGGER. */
export function staggerIndex(el, counts) {
  const parent = el.parentElement;
  const i = counts.get(parent) || 0;
  counts.set(parent, i + 1);
  return Math.min(i, MAX_STAGGER);
}

/** Revela os blocos quando entram na tela; com movimento reduzido ou sem IntersectionObserver, revela tudo já. */
export function initReveal(doc = document, win = window) {
  const items = doc.querySelectorAll(REVEAL_SELECTOR);
  const reduced = win.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !("IntersectionObserver" in win)) {
    for (const el of items) el.classList.add("in");
    return;
  }
  const counts = new Map();
  for (const el of items) el.style.setProperty("--i", String(staggerIndex(el, counts)));
  const io = new win.IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
  );
  for (const el of items) io.observe(el);
}

/** Barra de progresso: só aparece se a navegação demorar mais de PROGRESS_DELAY_MS. */
export function initNavigationProgress(doc = document, win = window) {
  const bar = doc.getElementById("progress");
  if (!bar) return;
  let timer = 0;
  doc.addEventListener("click", (e) => {
    const a = e.target.closest?.("a[href]");
    if (!a || !isInternalNavigation(a, e, win.location)) return;
    win.clearTimeout(timer);
    timer = win.setTimeout(() => bar.classList.add("on"), PROGRESS_DELAY_MS);
  });
  // volta do bfcache ou navegação cancelada: some com a barra
  win.addEventListener("pageshow", () => {
    win.clearTimeout(timer);
    bar.classList.remove("on");
  });
}

export function initMotion(doc = document, win = window) {
  initImageSkeletons(doc);
  initReveal(doc, win);
  initNavigationProgress(doc, win);
}
