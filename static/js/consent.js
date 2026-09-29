/* Consentimento de cookies (Google Consent Mode v2, modo básico): nada do Google carrega antes do aceite. */
import { getCookie, setCookie } from "./util.js";

/** O banner entra depois que o herói assentou, para não competir com ele. */
export const BANNER_DELAY_MS = 600;

export function initConsent(G, doc = document) {
  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied",
    wait_for_update: 500,
  });

  function loadAnalytics() {
    if (!G.ga || window.__gbcGA) return;
    window.__gbcGA = true;
    gtag("consent", "update", { analytics_storage: "granted" });
    const s = doc.createElement("script");
    s.async = true;
    s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(G.ga)}`;
    doc.head.appendChild(s);
    gtag("js", new Date());
    gtag("config", G.ga, { anonymize_ip: true, page_language: G.lang });
  }

  const banner = doc.getElementById("cookie");
  const showBanner = (delay = 0) => {
    if (!banner) return;
    window.setTimeout(() => {
      banner.hidden = false;
      doc.body.classList.add("has-cookie");
    }, delay);
  };
  const hideBanner = () => {
    if (!banner) return;
    banner.hidden = true;
    doc.body.classList.remove("has-cookie");
  };
  function applyConsent(v) {
    setCookie("gbc_consent", v, 365);
    hideBanner();
    if (v === "all") loadAnalytics();
  }

  const consent = getCookie("gbc_consent");
  if (consent === "all") loadAnalytics();
  else if (consent !== "essential") showBanner(BANNER_DELAY_MS);

  doc.getElementById("cookie-accept")?.addEventListener("click", () => applyConsent("all"));
  doc.getElementById("cookie-reject")?.addEventListener("click", () => applyConsent("essential"));
  doc.getElementById("manage-cookies")?.addEventListener("click", () => {
    showBanner();
    window.scrollTo({ top: doc.body.scrollHeight });
  });
}
