# Padrão de trabalho — site GBC Foods

> **For agents that don't read Portuguese:** these instructions are in Portuguese
> because the team is Brazilian. They apply to you regardless of which model or tool
> you are. Translate them if you must, but follow them. The one non-negotiable rule is
> in the next section.

Este arquivo vale para **qualquer pessoa ou agente, de qualquer modelo ou ferramenta**,
que mexa neste repositório. Leia-o inteiro antes da primeira alteração.

---

## 1. A regra única

**Nada entra em `main` sem uma Issue e um Pull Request.**

`main` é o que está publicado. Cada merge em `main` dispara o deploy do site na
Cloudflare. Por isso:

- Não se faz commit direto em `main`. Nunca. Nem "só um typo".
- Não se faz `git push --force` em `main`.
- Não existe deploy manual fora do fluxo (nada de arrastar `dist/` no Cloudflare Drop
  ou rodar `wrangler deploy` à mão, exceto em emergência documentada numa Issue).

Se você é um agente e **não consegue** abrir Issues ou PRs (sem acesso ao GitHub, sem
token, sem ferramenta), **pare e diga isso**. Entregue a branch ou o patch e o texto da
Issue para um humano criar. Commitar em `main` "porque não tinha outro jeito" é a
violação mais grave deste padrão.

---

## 2. O fluxo, passo a passo

### 2.1 Issue primeiro

Toda tarefa começa por uma Issue — antes de tocar em código ou conteúdo. Se já existe
uma Issue para a tarefa, use-a; se não, abra. Uma Issue por tarefa. Tarefa grande se
quebra em Issues menores.

Toda Issue recebe **exatamente um** destes três labels, que são os três tipos de tarefa
que existem aqui:

| Label | Quando usar | Exemplos |
|---|---|---|
| `Correção` | Algo está errado e precisa ser consertado | link quebrado, texto errado, tradução ruim, build falhando, foto esticada |
| `Melhoria` | Algo existe e vai ficar melhor | SEO, desempenho, texto mais claro, foto própria no lugar da de banco |
| `Nova função` | Algo que não existia passa a existir | página nova, categoria nova, integração nova, idioma novo |

Formato da Issue (os templates em `.github/ISSUE_TEMPLATE/` já pedem isso):

- **Título** curto, no imperativo: "Corrigir hreflang da página de cotação em RU",
  "Ativar a categoria Produtos embalados".
- **O que** precisa ser feito, em uma ou duas frases.
- **Por quê** — o problema ou o ganho.
- **Critério de pronto** — como se sabe que acabou. Sem isso a Issue não está pronta
  para ser trabalhada.

### 2.2 Branch por Issue

Sempre a partir de `main` atualizada. Nome da branch pelo tipo:

```
fix/<slug-curto>        → Correção
melhoria/<slug-curto>   → Melhoria
feat/<slug-curto>       → Nova função
chore/<slug-curto>      → manutenção do repositório (CI, templates, este arquivo)
```

Exemplos: `fix/hreflang-cotacao-ru`, `feat/produtos-embalados`, `melhoria/fotos-castanha`.

### 2.3 Commits

- Mensagem em português. Primeira linha ≤ 72 caracteres, no imperativo ou descritiva,
  sem ponto final. Corpo explicando **o porquê** quando não for óbvio.
- Commits pequenos e coerentes. Não misturar duas Issues no mesmo commit.
- Agentes assinam o commit com um trailer `Co-Authored-By:` que identifique o agente e
  o modelo. Isso é rastreabilidade, não vaidade.

### 2.4 Antes de abrir o PR — verificação obrigatória

Rode, na raiz do repositório, e só siga se tudo passar:

```bash
# instalar uma vez: pip install -r requirements.txt -r requirements-dev.txt && npm ci
ruff check . && ruff format --check .   # Python: lint e formatação (build.py, check_*.py, cf-deploy.py)
npm run lint                            # Biome (JS/CSS/JSON) + knip (código sem uso) + dependency-cruiser (fronteiras)
python3 check_contract.py               # contratos de arquitetura (URLs estáveis, segredos, templates, produtos)
python3 build.py --check                # conteúdo completo nos 4 idiomas (PT/EN/ES/RU)
python3 build.py                        # gera dist/ sem erro
python3 check_links.py                  # 0 links internos quebrados em dist/
npm run test:py                         # pytest: unitários de build.py + integração sobre dist/ + scripts (cobertura)
npm test                                # Vitest: módulos JS puros e de DOM (npm run test:coverage para o relatório)
npm run test:e2e                        # Playwright: desktop e móvel sobre dist/ servida localmente
npm run test:mutation                   # Stryker (≈3 min): score mínimo 70 %; rode quando mexer em static/js/
```

`ruff format .` e `npm run lint:fix` corrigem o que é automático. O CI roda exatamente isso
em cada PR (workflow `CI`), mais o **commitlint** sobre as mensagens de commit do PR e a
conferência de que a descrição do PR menciona a Issue (workflow `PR menciona a Issue`).
Abrir PR com verificação quebrada é perder tempo do revisor.

### 2.5 Pull Request

- **Um PR por Issue.** Título = título da Issue.
- A descrição **obrigatoriamente menciona a Issue** com uma palavra-chave de fechamento:
  `Closes #12`, `Fixes #12` ou `Resolves #12`. Isso liga o PR à Issue e a fecha sozinha
  no merge. PR sem `Closes #N` na descrição está incompleto e não deve ser mesclado.
- A descrição segue o template em `.github/PULL_REQUEST_TEMPLATE.md`: o que mudou, como
  foi verificado, o que o revisor deve olhar com atenção. Mudança visual leva print.
- Agentes: terminem a descrição do PR com uma linha identificando o agente e, se
  houver, o link da sessão em que o trabalho foi feito.
- **Agentes não mesclam o próprio PR**, a menos que a pessoa tenha pedido isso
  explicitamente na mesma conversa. O merge é o ato de aprovação humana — e é o que
  publica o site.

### 2.6 Merge = deploy

- Só se mescla com o CI verde.
- Método: **Squash and merge**. `main` fica linear, um commit por Issue, com a mensagem
  do PR. A branch é apagada depois do merge.
- O merge em `main` dispara `.github/workflows/deploy.yml`, que gera o site e publica na
  Cloudflare. Se o deploy falhar, o site anterior continua no ar; abre-se uma Issue de
  `Correção` e conserta-se pelo fluxo normal. Não se "arruma direto na Cloudflare".
- Emergência (site fora do ar, formulário quebrado): mesmo fluxo, só que rápido. Issue
  `Correção`, branch `fix/`, PR, merge. Nada de atalho — o atalho é o que costuma
  derrubar o que ainda estava de pé.

---

## 3. Como o site funciona (o mínimo para não quebrar nada)

- **Gerador estático em Python**: `build.py` + Jinja2. Dependências em
  `requirements.txt` (ferramentas de desenvolvimento em `requirements-dev.txt` e
  `package.json`). Não há CMS, banco nem servidor, e **não há bundler**: o JavaScript vai
  para o navegador como está.
- **Tudo o que aparece no site vem de `content/`**: `pages/*.json`, `products/*.json`
  (um arquivo por produto), `blog/`, `legal/`, `ui.json`, `routes.json`, `config.json`.
  Os templates HTML ficam em `templates/`; o visual em `static/`.
- **`dist/` é gerada e não é versionada.** Nunca edite nada dentro de `dist/`; a
  alteração some no próximo build.
- **JavaScript em módulos ES**, em `static/js/`: `site.js` é o único ponto de entrada
  (carregado com `type="module"`); `util.js` e `quote-message.js` são **puros** (sem DOM,
  testáveis em Node); `nav.js`, `consent.js` e `quote-form.js` tocam o DOM. Módulo novo:
  puro se puder, importado por `site.js`, sem dependência externa — o dependency-cruiser
  (`.dependency-cruiser.cjs`) recusa import de módulo de DOM a partir de módulo puro,
  ciclos, órfãos e pacotes npm no código do site.
- **URLs são um contrato.** `routes.lock.json` registra todos os slugs publicados (rotas,
  produtos, artigos). `check_contract.py` falha se algum mudar ou sumir. Só se atualiza o
  lock (`python3 check_contract.py --update`) com decisão registrada na Issue e redirect
  da URL antiga.
- **Quatro idiomas, sempre.** Toda chave de texto existe em `pt`, `en`, `es` e `ru`.
  Chave nova em um bloco = chave nova nos quatro. `build.py --check` reclama se faltar.
- **`routes.json` define as URLs.** Depois que o site está no ar, **não se troca slug**:
  o Google perde a página. Página nova, sim; renomear, não (o lock acima garante).
- **Segredos não entram no repositório.** Token da Cloudflare, chaves do Supabase,
  `.env`: nunca. No CI eles vivem em *Secrets* do GitHub (`CF_API_TOKEN`,
  `CF_ACCOUNT_ID`). O site só conhece a URL pública da função `site-lead`, nunca uma
  chave.
- **Testes acompanham o código.** Função nova em `build.py` → teste em `tests/test_build_unit.py`;
  regra nova sobre o site gerado → `tests/test_site_integration.py`; módulo JS novo → `tests/js/`
  (puro em Node, DOM em happy-dom) e o Stryker precisa continuar ≥ 70 %; fluxo novo que o
  visitante usa → `e2e/site.spec.js` (roda em desktop e Pixel 5). O CI recusa PR com cobertura
  do código alterado abaixo de 70 % (Codecov, `codecov.yml`). O `vitest` fica **fixado em 4.1**:
  com o 5 o Stryker não ativa os mutantes (score cai a 2 %) — só subir quando o
  `@stryker-mutator/vitest-runner` suportar.
- **Motion tem regras** (`static/motion.css` + `static/js/motion.js`, feitos com a skill
  *design-motion-principles*, ponderação Jakub · Jhey · Emil): só `transform`, `opacity`
  e `filter` animam; entrada = opacidade + `translateY` + blur com `var(--ease-out)`,
  saída sempre mais curta com `var(--ease-in)`; durações pelos tokens `--d-fast`
  (menus, hover), `--d-base` (fades), `--d-slow` (blocos ao rolar) — nunca `ease` puro,
  nunca `width/height/top/left`. Toda animação nova entra também no bloco
  `@media (prefers-reduced-motion: reduce)` com o estado final. Nada pode depender de JS
  para ficar visível: o estado "escondido" só existe sob `html.js`, e há uma rede de
  segurança de 2,5 s. Bloco novo que deve entrar ao rolar: acrescente o seletor nas
  duas listas iguais (`motion.css` e `REVEAL_SELECTOR` em `motion.js`). Sem loops
  chamativos (pulsar, brilhar): o único loop é o shimmer do skeleton e o spinner do
  botão, ambos funcionais.
- **Observabilidade** (`static/js/observability.js`): Sentry no navegador (erros de JS,
  erros de recurso, Web Vitals), carregado **só depois do consentimento** — o mesmo
  gancho `onConsentAll` do GA4 — e só se `sentry_dsn` estiver preenchido em
  `content/config.json`. `sendDefaultPii: false`, sem session replay, tag `lang`,
  `release` = SHA curto gravado por `build.py` em `window.GBC.release` e registrado no
  Sentry pelo `deploy.yml` (Secrets `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`).
  Qualquer script de terceiro novo entra pelo mesmo gancho de consentimento e ganha um
  parágrafo em `content/legal/cookies/*.md` nos 4 idiomas. O monitor de disponibilidade
  (`uptime.yml`) lê a variável `SITE_URL` e abre Issue de `Correção` quando o site não
  responde. Datadog, New Relic e OpenTelemetry não se aplicam: o site não tem backend
  próprio (o único é a função `site-lead`, no Supabase, fora deste repositório).
- O manual completo de administração é o `README.md`; o roteiro de publicação e domínio
  é o `COMO-PUBLICAR.md`.

---

## 4. Regras de conteúdo (decisões já tomadas — não reabrir)

Estas regras vieram de correções feitas pela GBC. Um agente que as ignora refaz
trabalho já rejeitado.

- **Não publicar** volumes ou posições de negociação: contagem de contêineres da
  originação, margens, preço máximo de compra, preço de referência de cooperativa,
  contato direto de cooperativa ou fornecedor.
- **Nunca** texto do tipo "o que não fazemos" / "não compramos em mercado aberto".
- **Certificações.** A GBC confirmou em 09/2026 que **é detentora** de Rainforest Alliance
  e Fairtrade para o café verde. Daí em diante:
  - certificação **da GBC** pode ser afirmada em nome da GBC, com o número de certificado
    informado na cotação — não no site;
  - certificação **da origem** (produtor, cooperativa, C.A.F.E. Practices) continua
    atribuída à origem: "origem certificada mediante solicitação";
  - **imagem de selo só entra no repositório com a licença de uso da certificadora
    arquivada.** Rainforest Alliance e Fairtrade aprovam cada aplicação antes do uso.
    Enquanto a licença não chegar, a certificação aparece só em texto.

  Esta regra substituiu a anterior ("a GBC não é a detentora"), que estava errada. Se
  você é um agente e leu essa frase em algum lugar, ela é histórica — não reverta o
  texto do café por causa dela.
- Cada produto tem a **sua própria página dentro deste site**. Nada de link para site
  externo do café ou de qualquer outro produto.
- "Serviços" é uma seção **informativa** sobre a trading e a logística. O nome fica.
- Fotos com pessoas só com autorização assinada. Sem logos de terceiros quando evitável.
  Fotos nunca esticadas. Toda foto de banco de imagens entra em
  `content/creditos-fotos.md`.
- Nenhum número institucional ("GBC em números") sem confirmação escrita da GBC.
- A categoria **Produtos embalados** já existe no código e fica invisível até ter o
  primeiro produto (ver README, seção "A terceira família").

---

## 5. Checklist de um agente, do início ao fim

1. Li este arquivo.
2. Existe Issue para a tarefa? Se não, abri uma com o label certo e critério de pronto.
3. Criei a branch a partir de `main` atualizada, com o prefixo certo.
4. Fiz a alteração em `content/`, `templates/` ou `static/` — nunca em `dist/`.
5. Chave nova? Está nos quatro idiomas.
6. `ruff`, `npm run lint`, `check_contract.py`, `build.py --check`, `build.py`,
   `check_links.py`, `npm run test:py`, `npm test` e `npm run test:e2e` passaram (seção 2.4);
   mexeu em `static/js/`? `npm run test:mutation` também.
7. Abri o PR com `Closes #N`, descrição pelo template, print se for visual.
8. Não mesclei. Entreguei o link do PR para a pessoa e disse o que ela vai ver.
9. Se algo neste fluxo estava fora do meu alcance, disse isso claramente em vez de
   contornar.
