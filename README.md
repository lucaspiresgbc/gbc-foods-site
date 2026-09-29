# Site GBC Foods — manual de administração

Este pacote é o site inteiro: os textos, as fotos, o gerador e a versão pronta para publicar. Ninguém depende de agência para mexer nele. Este manual explica **onde cada coisa fica**, **como alterar** e **como publicar**.

> **Como o trabalho acontece neste repositório:** toda tarefa é uma Issue no GitHub
> (`Correção`, `Melhoria` ou `Nova função`), o trabalho vai numa branch e chega a `main`
> só por Pull Request que mencione a Issue (`Closes #N`). Merge em `main` = deploy
> automático na Cloudflare. O padrão completo, que vale para pessoas e para agentes de
> qualquer modelo, está em **[AGENTS.md](AGENTS.md)**.

```
gbc-foods-site/
├── README.md              ← este manual
├── build.py               ← gera o site (python3 build.py)
├── cf-deploy.py           ← publica na Cloudflare pela linha de comando (opcional)
├── wrangler.jsonc         ← configuração para publicar com o wrangler (opcional)
├── content/               ← TUDO o que aparece no site é editado aqui
│   ├── config.json        ← WhatsApp, Google Analytics, e-mail, telefone, domínio
│   ├── ui.json            ← menu, botões, rodapé, formulário, banner de cookies (4 idiomas)
│   ├── routes.json        ← endereço (URL) de cada página em cada idioma
│   ├── steps.json         ← os dez passos de um embarque
│   ├── pages/             ← textos das páginas (home, empresa, serviços, foods, logistics, produtos, cotação/contato/blog)
│   ├── products/          ← UM ARQUIVO POR PRODUTO (11 hoje)
│   ├── blog/              ← UMA PASTA POR ARTIGO, com pt.md, en.md, es.md, ru.md
│   ├── legal/             ← política de privacidade e de cookies (4 idiomas)
│   └── creditos-fotos.md  ← origem e licença de cada foto de banco de imagens
├── static/
│   ├── img/coffee/        ← fotos da cooperativa (café)
│   ├── img/products/      ← fotos dos produtos
│   ├── img/brand/         ← logos
│   ├── site.css           ← visual
│   ├── js/                ← comportamento (site.js é a entrada; módulos puros e de DOM separados)
│   └── favicon, og-image  ← ícones e imagem de compartilhamento
├── templates/             ← a estrutura HTML das páginas (só mexer se quiser mudar o layout)
├── check_links.py         ← confere os links internos de dist/
├── check_contract.py      ← contratos de arquitetura (URLs estáveis, segredos, templates)
├── routes.lock.json       ← registro dos slugs publicados (não editar à mão)
├── AGENTS.md / CLAUDE.md  ← padrão de trabalho para pessoas e agentes
├── biome.json, knip.json, .dependency-cruiser.cjs, commitlint.config.cjs, ruff.toml ← lint
└── dist/                  ← O SITE PRONTO (gerada pelo build; não é versionada no git)
```

O site é **estático**: não tem banco de dados, painel, senha nem servidor para manter. Cada alteração é: editar um arquivo em `content/` → rodar `python3 build.py` para conferir → abrir o Pull Request. O merge publica sozinho (ver `COMO-PUBLICAR.md`).

---

## 1. Antes de publicar pela primeira vez

Abra `content/config.json` e preencha:

| Campo | O que é | Como preencher |
|---|---|---|
| `whatsapp_numero` | Número que recebe as cotações | Só dígitos, com país e DDD: `5513991234567` |
| `ga4_measurement_id` | ID do Google Analytics 4 | Começa com `G-`. Enquanto estiver com `X`, o Analytics não é publicado (o banner de cookies funciona mesmo assim) |
| `google_site_verification` | Código do Google Search Console (opcional) | Só se escolher verificar por tag HTML; por DNS não precisa |
| `email_comercial`, `telefone` | Contato exibido no site | — |
| `dominio` | Endereço público | `https://gbc-foods.com` — muda o canonical, o sitemap e os links compartilhados |

Depois rode `python3 build.py`. Se o WhatsApp ainda estiver com o valor de exemplo, o gerador avisa.

---

## 2. Como gerar o site

Precisa de Python 3.9 ou mais novo (Windows, Mac ou Linux) e, uma vez só:

```
pip install jinja2 markdown pyyaml pillow
```

Depois, na pasta do site:

```
python3 build.py            # gera dist/
python3 build.py --serve    # gera e abre em http://localhost:8080 para conferir
python3 build.py --check    # só confere se todo texto existe nos 4 idiomas
```

O gerador também converte cada foto em três tamanhos WebP e um JPEG de reserva — por isso demora uns 10 segundos.

---

## 3. Como editar

### Textos de página

`content/pages/*.json`. Cada arquivo tem quatro blocos — `"en"`, `"pt"`, `"es"`, `"ru"` — com as mesmas chaves. Mude o texto entre aspas e mantenha a estrutura. Se apagar uma chave num idioma e não no outro, o `--check` avisa.

Regras dos arquivos JSON: texto sempre entre aspas duplas; vírgula entre um item e outro, mas **não** depois do último; para aspas dentro do texto use `\"` ou aspas curvas “ ”. Um editor como o VS Code marca erros em vermelho.

### Produtos

`content/products/`. **Para incluir um produto novo, copie um arquivo existente**, renomeie (o número no nome define a ordem) e troque os campos:

| Campo | Significado |
|---|---|
| `id` | identificador interno, sem espaços (`macadamia`) — usado no link da cotação |
| `category` | `granel` (Produtos a granel), `po` (Produtos em pó) ou `embalados` (Produtos embalados) |
| `order` | posição na lista |
| `featured` | `true` = aparece na home e no rodapé |
| `image` | caminho da foto dentro de `static/img/` (ex.: `products/macadamia.jpg`). Vazio = painel ilustrado da marca |
| `gallery` | fotos extras na ficha (lista) |
| `hs` | código HS de 6 dígitos (informativo) |
| `slug` | endereço da ficha em cada idioma (não troque depois que estiver no ar) |
| `name`, `short`, `description`, `specs`, `origin`, `packaging`, `container`, `availability` | textos, sempre nos 4 idiomas |

`specs` é uma lista de linhas da tabela; cada linha tem `k` (rótulo) e `v` (valor), cada um nos 4 idiomas. Para tirar um produto do ar, apague o arquivo (ou mova para fora da pasta).

#### A terceira família: Produtos embalados

A categoria **Produtos embalados** já está montada no site inteiro — endereço próprio nos
4 idiomas (`/pt/produtos/embalados/`, `/en/products/packaged/`, `/es/productos/envasados/`,
`/ru/products/packaged/`), menu, rodapé, home, página de Produtos e página de Serviços —
mas **fica invisível enquanto não houver nenhum produto nela**. Isso é de propósito: uma
categoria vazia no ar dá impressão de site inacabado.

Para ativá-la, basta criar o primeiro produto:

1. Copie `content/products/MODELO-embalado.json.exemplo` para `content/products/12-<id>.json`
   (sem o `.exemplo` — o build ignora arquivos que não terminam em `.json`).
2. Preencha os campos nos 4 idiomas, mantendo `"category": "embalados"`.
3. Rode `python3 build.py`.

A partir daí a categoria aparece sozinha em todos os lugares, e o texto de abertura da
página de Produtos troca de "duas famílias" para "três famílias" automaticamente (as duas
versões estão em `content/pages/products.json`, nas chaves `index_lead` e `index_lead_3`).

### Blog

`content/blog/`. **Cada artigo é uma pasta** com quatro arquivos: `pt.md`, `en.md`, `es.md`, `ru.md`. Para um artigo novo, copie uma pasta, renomeie (o número ordena) e escreva. O cabeçalho de cada arquivo:

```
---
title: "Título do artigo"
slug: endereco-do-artigo            (só letras minúsculas, números e hífens; um por idioma)
description: "Resumo de uma ou duas frases — aparece no Google e nos cartões."
date: 2026-10-15
author: Equipe GBC Foods
image: products/ship-sea.jpg        (foto de capa, dentro de static/img/; opcional)
image_alt: "Descrição da foto"
tags: [logística, incoterms]
---
```

Abaixo do cabeçalho, o texto em Markdown: `## Subtítulo`, `**negrito**`, `*itálico*`, listas com `-`, links `[texto](https://...)`. O artigo mais recente (pela `date`) aparece primeiro. Um artigo só entra no ar quando existe nos quatro idiomas — se faltar um, o `--check` avisa e aquele idioma fica sem o artigo.

### Textos de interface (menu, botões, formulário, banner)

`content/ui.json`. Cada chave tem os quatro idiomas lado a lado.

### Políticas

`content/legal/privacy/` e `content/legal/cookies/`, em Markdown, um arquivo por idioma. Ao alterar, mude também a data `updated` no cabeçalho — ela aparece no topo da página.

### Fotos

- Coloque o arquivo em `static/img/products/` (ou `coffee/`) em JPEG, **mínimo 1600 px de largura**, e aponte o campo `image` do produto para ele. O gerador cria os tamanhos menores sozinho.
- Fotos de produto funcionam melhor em horizontal, proporção 4:3 ou 3:2, produto ocupando o quadro, fundo neutro.
- Fotos de banco de imagens: registre em `content/creditos-fotos.md` (é a prova de licença). Os produtos ainda sem foto própria (castanha-do-brasil, óleo de amendoim, leite em pó, amido de milho) usam o painel ilustrado da marca até haver foto.
- Fotos com pessoas (as da cooperativa, por exemplo) precisam de autorização de uso de imagem assinada.

### Endereços (URLs)

`content/routes.json` e os `slug` dos produtos e artigos. **Depois que o site estiver no ar, evite mudar**: o Google perde a página antiga e quem tinha o link recebe erro 404. Se precisar mesmo, mude e avise para configurar um redirecionamento na Cloudflare.

---

## 4. Como publicar

A pasta `dist/` é o site inteiro. Três jeitos, do mais simples ao mais automático:

**A. Cloudflare Drop (sem instalar nada).** Abra https://cloudflare.com/drop, arraste a pasta `dist` inteira, teste o link temporário e clique em *Claim* para fixar o site na conta da empresa. Cada nova versão: arrastar de novo e reivindicar para o mesmo Worker.

**B. Wrangler (com Node.js).** Na pasta do site, uma vez `npx wrangler login`; depois, a cada versão, `npx wrangler deploy`. O `wrangler.jsonc` já aponta para `dist/`.

**C. Script Python (`cf-deploy.py`).** Com um token de API da Cloudflare (permissão *Workers Scripts: Edit*) e o ID da conta:

```
CF_API_TOKEN=... CF_ACCOUNT_ID=... python3 cf-deploy.py --name gbc-foods-site --dir dist
```

Domínio, DNS, e-mail (MX) e Search Console: o roteiro está em `COMO-PUBLICAR.md`, entregue junto com a primeira versão do site. O que não muda: **conferir os registros MX antes de trocar os nameservers**, senão o e-mail para de chegar.

Depois de publicar com o domínio final, cadastre na função `site-lead` do Supabase o segredo `LEAD_ALLOWED_ORIGINS = https://gbc-foods.com,https://www.gbc-foods.com` — assim só o site consegue gravar cotações no ERP.

---

## 5. O que o site já faz sozinho

- **Quatro idiomas** em endereços próprios (`/pt/`, `/en/`, `/es/`, `/ru/`). A raiz `/` detecta o idioma do navegador e redireciona; a escolha no seletor fica guardada por 12 meses (cookie `gbc_lang`).
- **Cotação → WhatsApp.** O formulário monta a mensagem no idioma do visitante e abre o WhatsApp do número configurado. Em paralelo, grava uma cópia no ERP (coleção `leadsSite`) pela função `site-lead` — sem chave nenhuma no site. Se o Supabase estiver fora do ar, o WhatsApp funciona do mesmo jeito.
- **Google Analytics 4 com Consent Mode v2.** Nada do Google carrega antes de o visitante clicar em *Aceitar todos*. Quem clica em *Só os essenciais* navega sem cookie de estatística. O link *Gerenciar cookies* no rodapé reabre o banner.
- **SEO:** título e descrição por página e idioma, `hreflang` entre as versões (com `x-default`), `canonical`, `sitemap.xml` com as alternativas de idioma, `robots.txt`, dados estruturados schema.org (Organization, WebSite, BreadcrumbList, Product em cada ficha, BlogPosting em cada artigo), Open Graph e Twitter Card para compartilhamento, imagens em WebP com largura e altura declaradas, fontes com `display=swap`, cabeçalhos de segurança (`_headers`).
- **Acessibilidade:** navegação por teclado, foco visível, contraste AA, `aria` nos menus, `prefers-reduced-motion`.

### Google Search Console — os três passos que fazem o site aparecer

1. Adicione a propriedade `gbc-foods.com` (verificação por DNS, na Cloudflare, é a mais simples).
2. Envie o sitemap: `https://gbc-foods.com/sitemap.xml`.
3. Em *Configurações → Segmentação internacional*, nada a fazer: o `hreflang` já cuida. Em duas a quatro semanas as quatro versões aparecem nos relatórios.

Bing: repita em bing.com/webmasters (aceita importar do Search Console). Yandex, para o público russo: webmaster.yandex.com, mesmo sitemap.

---

## 6. O que fica fora do site

- Preços, margens, preço máximo de compra, volume total originado, dados de contratos: **nunca** no site.
- O ERP: é outro arquivo e não pode ser publicado por este caminho enquanto o login e o RLS não estiverem ligados.
- Selos Fairtrade / Rainforest / C.A.F.E. Practices como imagem: só texto, atribuído à cooperativa ("origem certificada mediante solicitação"), até haver certificado próprio ou autorização de uso da marca.

---

## 7. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `python3 build.py` para com erro apontando um `.json` | vírgula a mais/a menos ou aspas erradas | abra o arquivo num editor com validação de JSON; a linha do erro está na mensagem |
| Um produto/artigo não aparece num idioma | falta a versão naquele idioma | `python3 build.py --check` lista o que falta |
| A foto não aparece | caminho errado em `image` ou arquivo fora de `static/img/` | confira o nome exato, com extensão `.jpg` |
| O WhatsApp abre com número errado | `whatsapp_numero` em `config.json` | corrija e gere de novo |
| O Analytics não registra | ID ainda com `X`, ou visitante recusou cookies | confira `ga4_measurement_id`; teste aceitando o banner |
| Mudei um texto e o site no ar não mudou | esqueceu de gerar ou de publicar `dist/` | `python3 build.py` e publique de novo; limpe o cache no navegador (Ctrl+F5) |
