import { defineConfig } from "vitest/config";

// Unitários do JavaScript do site. Os módulos puros rodam em Node; os de DOM usam happy-dom.
export default defineConfig({
  test: {
    include: ["tests/js/**/*.test.js"],
    environment: "happy-dom",
    // o site injeta <script> de terceiros (gtag, Sentry); no teste basta ver a tag, não baixar o arquivo
    environmentOptions: {
      happyDOM: {
        settings: {
          disableJavaScriptFileLoading: true,
          disableCSSFileLoading: true,
          handleDisabledFileLoadingAsSuccess: true,
        },
      },
    },
    coverage: {
      provider: "v8",
      include: ["static/js/**/*.js"],
      reporter: ["text", "lcov"],
      reportsDirectory: "coverage-js",
      thresholds: { lines: 85, functions: 85, branches: 80 },
    },
  },
});
