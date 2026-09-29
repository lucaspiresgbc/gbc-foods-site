# Como colocar o site no ar

Sem instalar nada. Quatro etapas, na ordem. A primeira leva cinco minutos e já deixa o site acessível por um link; as outras três fazem dele o site oficial da empresa.

O pacote `gbc-foods-site.zip` tem uma pasta `dist/` com tudo o que vai para o servidor: o site, favicon, imagem de compartilhamento, `robots.txt`, `sitemap.xml` e cabeçalhos de segurança, nos quatro idiomas.

---

## Etapa 1 — Publicar (5 minutos)

1. Descompacte o zip. Abra **https://cloudflare.com/drop**.
2. Arraste a pasta **`dist`** (a pasta inteira, não o zip) para a área de upload.
3. O Cloudflare gera um endereço temporário, tipo `https://xxxx.workers.dev`, válido por uma hora. Abra, navegue, teste o formulário.
4. Clique em **Claim** e entre na conta Cloudflare que já está conectada a este projeto. O site passa a ser permanente, num endereço `gbc-foods-site.<sua-conta>.workers.dev`, com HTTPS, sem custo.

Pronto: o site está no ar. O que vem depois é dar a ele o domínio da empresa.

---

## Etapa 2 — Domínio

O e-mail comercial já é `commercial@gbc-foods.com`, então o domínio **gbc-foods.com** é da empresa e é o endereço natural do site. O site já foi gerado apontando para ele (canonical, Open Graph, sitemap).

1. No painel Cloudflare: **Add a domain** → `gbc-foods.com` → plano Free.
2. O Cloudflare lê os registros DNS atuais e mostra os nameservers novos. **Antes de trocar, confira que os registros MX (e-mail) aparecem na lista importada.** Se não aparecerem, adicione à mão os MX do provedor de e-mail. Este é o único passo que pode derrubar algo: sem os MX, `commercial@gbc-foods.com` para de receber.
3. No registrador do domínio, troque os nameservers pelos dois que o Cloudflare indicou. Propaga em minutos a algumas horas.
4. No Cloudflare: **Workers & Pages → gbc-foods-site → Settings → Domains & Routes → Add → Custom domain** → `gbc-foods.com`. Repita para `www.gbc-foods.com`.

Se preferir manter o DNS onde está, dá para usar só um subdomínio (`foods.gbcgroup.com.br`, por exemplo) — mas o domínio inteiro na Cloudflare é o caminho limpo, e o site já foi preparado para `gbc-foods.com`.

---

## Etapa 3 — Fechar a porta do formulário

Com o domínio no ar, tranque a função que recebe os formulários para aceitar só o seu site:

**Supabase → Edge Functions → site-lead → Secrets → Add:**

```
LEAD_ALLOWED_ORIGINS = https://gbc-foods.com,https://www.gbc-foods.com
```

Opcionalmente, para receber um e-mail a cada solicitação, adicione também `LEAD_NOTIFY_TO` e `RESEND_API_KEY` (detalhes em `LEADS-SITE-INTEGRACAO.md`).

Depois, envie uma solicitação de teste pelo site publicado. Me avise — eu confirmo a linha no banco.

---

## Etapa 4 — Ser encontrado

1. **Google Search Console** (search.google.com/search-console): adicione `gbc-foods.com`, verifique pelo DNS (o Cloudflare facilita) e envie o sitemap `https://gbc-foods.com/sitemap.xml`. As quatro línguas entram pelo mesmo sitemap.
2. **Google Analytics 4**: crie a propriedade, copie o ID `G-…` para `content/config.json` e gere o site de novo. O banner de consentimento já está pronto; sem aceite, nada do Google carrega.

---

## Atualizar o site depois — pelo GitHub

O site vive num repositório no GitHub e **cada merge em `main` publica sozinho** na
Cloudflare. Ninguém arrasta pasta nem roda comando de deploy: a alteração entra por
Pull Request ligado a uma Issue (o padrão está em `AGENTS.md`), o CI gera e confere o
site, e o merge dispara `.github/workflows/deploy.yml`.

Para isso funcionar, cadastre uma vez os dois segredos no repositório
(**Settings → Secrets and variables → Actions → New repository secret**):

| Secret | O que é | Onde pegar |
|---|---|---|
| `CF_ACCOUNT_ID` | ID da conta Cloudflare | Painel Cloudflare → Workers & Pages → lado direito, "Account ID" |
| `CF_API_TOKEN` | Token de API só para publicar Workers | Painel → My Profile → API Tokens → Create Token → modelo **"Edit Cloudflare Workers"** (ou permissão *Account · Workers Scripts · Edit*) |

Enquanto os segredos não existirem, o workflow não falha: ele gera o site e deixa a pasta
`dist/` anexada como artefato da execução (**Actions → Deploy → site-dist-…**) para
publicar à mão pelo Cloudflare Drop, como na Etapa 1.

Se um deploy falhar, o site anterior continua no ar. Abre-se uma Issue de `Correção` e
resolve-se pelo fluxo normal.

Fotos próprias: coloque em `static/img/products/`, aponte o campo `image` do produto e gere de novo (ver README.md).

---

## O que NÃO publicar assim

O ERP. Ele é um arquivo estático também, e subiria pelo mesmo caminho em um minuto — mas hoje ele carrega a chave do Supabase com acesso total e o login está desligado. Publicá-lo agora é deixar os contratos abertos para quem souber o endereço. O roteiro do outro chat já tem a ordem certa: religar a autenticação, apertar o RLS, e só então publicar — de preferência atrás do Cloudflare Access, que exige login antes mesmo de a página carregar.

---

## Checklist final

- [ ] Site no ar pelo Drop e reivindicado na conta
- [ ] `gbc-foods.com` na Cloudflare, **MX conferidos**, nameservers trocados
- [ ] Domínio ligado ao Worker (raiz e www)
- [ ] `LEAD_ALLOWED_ORIGINS` cadastrado na função `site-lead`
- [ ] Solicitação de teste enviada e confirmada no banco
- [ ] Search Console com sitemap enviado
- [ ] Google Analytics 4 ativo (ID em config.json)
- [ ] Número de WhatsApp e ID do Analytics em `content/config.json`
- [ ] Fotos próprias em `static/img/` quando existirem
- [ ] `CF_ACCOUNT_ID` e `CF_API_TOKEN` cadastrados como Secrets no GitHub (deploy automático)
