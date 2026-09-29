/* Mensagens de commit no padrão do AGENTS.md (seção 2.3): português, primeira linha curta e sem ponto final,
 * corpo separado por linha em branco. Não exige prefixo "feat:"/"fix:" — o tipo da tarefa está no label da Issue. */
module.exports = {
  rules: {
    "header-max-length": [2, "always", 72],
    "header-min-length": [2, "always", 10],
    "header-full-stop": [2, "never", "."],
    "body-leading-blank": [2, "always"],
    "body-max-line-length": [2, "always", 100],
    "footer-leading-blank": [1, "always"],
  },
  ignores: [(msg) => /^Merge /.test(msg)],
};
