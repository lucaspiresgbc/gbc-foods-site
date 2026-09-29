/* Contratos de arquitetura do JavaScript do site (dependency-cruiser).
 * Módulos puros (sem DOM) não podem depender de módulos que tocam o DOM; site.js é o único ponto de entrada.
 * Rodar: npx depcruise static/js --config .dependency-cruiser.cjs */
const PURE = "^static/js/(util|quote-message)\\.js$";
// tudo o que não é puro toca o DOM (nav, consent, quote-form, motion, site…)

module.exports = {
  forbidden: [
    {
      name: "puro-nao-depende-do-dom",
      comment:
        "util.js e quote-message.js são puros e testáveis sem navegador; não podem importar módulos de DOM.",
      severity: "error",
      from: { path: PURE },
      to: { path: "^static/js/", pathNot: PURE },
    },
    {
      name: "ninguem-importa-o-entrypoint",
      comment: "site.js é o ponto de entrada; nenhum módulo pode importá-lo.",
      severity: "error",
      from: {},
      to: { path: "^static/js/site\\.js$" },
    },
    {
      name: "sem-ciclos",
      severity: "error",
      from: {},
      to: { circular: true },
    },
    {
      name: "sem-orfaos",
      comment: "Todo módulo em static/js precisa ser alcançável a partir de site.js.",
      severity: "error",
      from: { orphan: true, path: "^static/js/" },
      to: {},
    },
    {
      name: "sem-dependencia-externa-no-site",
      comment: "O site não tem bundler: os módulos só podem importar arquivos locais (./x.js).",
      severity: "error",
      from: { path: "^static/js/" },
      to: {
        dependencyTypes: ["npm", "npm-dev", "npm-optional", "npm-peer", "npm-bundled", "npm-no-pkg", "core"],
      },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: false,
    reporterOptions: { text: { highlightFocused: true } },
  },
};
