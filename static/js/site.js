/* GBC Foods — ponto de entrada do JavaScript do site. Cada responsabilidade vive no seu módulo. */
import { initConsent } from "./consent.js";
import { initMotion } from "./motion.js";
import { initLanguage, initMenu } from "./nav.js";
import { initQuoteForm } from "./quote-form.js";

const G = window.GBC || {};
initMotion();
initLanguage();
initMenu();
initConsent(G);
initQuoteForm(G);
