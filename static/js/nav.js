/* Navegação: seletor de idioma, menu móvel e submenus. */
import { setCookie } from "./util.js";

export function initLanguage(doc = document) {
  for (const a of doc.querySelectorAll("a[data-lang]")) {
    a.addEventListener("click", () => setCookie("gbc_lang", a.getAttribute("data-lang"), 365));
  }
  const langBox = doc.getElementById("lang");
  if (!langBox) return;
  const langBtn = langBox.querySelector(".lang-btn");
  const close = () => {
    langBox.classList.remove("open");
    langBtn.setAttribute("aria-expanded", "false");
  };
  langBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = langBox.classList.toggle("open");
    langBtn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  doc.addEventListener("click", close);
  langBox.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      close();
      langBtn.focus();
    }
  });
}

export function initMenu(doc = document) {
  const burger = doc.getElementById("burger");
  const nav = doc.getElementById("nav");
  if (burger && nav) {
    burger.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      doc.body.style.overflow = open ? "hidden" : "";
    });
  }
  for (const li of doc.querySelectorAll(".has-sub")) {
    const btn = li.querySelector(".sub-toggle");
    if (!btn) continue;
    btn.addEventListener("click", () => {
      const open = li.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
}
