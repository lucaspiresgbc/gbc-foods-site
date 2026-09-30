"""Integração: o site gerado em dist/ — o que o navegador, o Google e o visitante recebem."""

import json
import re
import xml.etree.ElementTree as ET

import pytest

PAGES_PER_LANG = (
    28  # 14 rotas fixas + 11 fichas + (…) — conferido abaixo por igualdade entre idiomas, não por número mágico
)


def read(dist, rel):
    return (dist / rel).read_text(encoding="utf-8")


def test_gera_114_paginas_com_a_categoria_de_embalados_vazia(build_mod, dist):
    assert len(build_mod.WRITTEN) == 114
    assert not (dist / "pt" / "produtos" / "embalados").exists()


def test_cada_idioma_tem_o_mesmo_numero_de_paginas(dist, langs):
    counts = {lang: len(list((dist / lang).rglob("index.html"))) for lang in langs}
    assert len(set(counts.values())) == 1, counts


def test_raiz_redireciona_por_idioma_e_tem_hreflang(dist, langs):
    root = read(dist, "index.html")
    assert "gbc_lang" in root and "navigator.languages" in root
    for lang in langs:
        assert f'hreflang="{lang}{"-BR" if lang == "pt" else ""}"' in root
    assert 'hreflang="x-default"' in root
    assert "<noscript>" in root


@pytest.mark.parametrize(
    "rel", ["pt/index.html", "en/products/index.html", "es/cotizacion/index.html", "ru/company/index.html"]
)
def test_hreflang_reciproco_e_canonical(dist, rel, langs):
    html = read(dist, rel)
    lang = rel.split("/")[0]
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
    assert canonical.startswith("https://gbc-foods.com/" + lang + "/")
    alts = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', html))
    assert "x-default" in alts
    for other in langs:
        key = other + ("-BR" if other == "pt" else "")
        assert key in alts, f"{rel} sem hreflang {key}"
        # a alternativa aponta para uma página que existe
        target = alts[key].replace("https://gbc-foods.com", "").strip("/")
        assert (dist / target / "index.html").exists(), alts[key]


def test_jsonld_valido_em_toda_pagina(dist):
    bad = []
    for f in dist.rglob("index.html"):
        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', f.read_text(encoding="utf-8"), re.S
        ):
            try:
                d = json.loads(block)
                assert "@type" in d
            except (ValueError, AssertionError):
                bad.append(str(f.relative_to(dist)))
    assert not bad, bad


def test_ficha_de_produto_tem_jsonld_product_e_link_de_cotacao(dist, build_mod):
    prod = next(p for p in build_mod.PRODUCTS if p["id"] == "coffee-arabica")
    html = read(dist, build_mod.product_url(prod, "en").strip("/") + "/index.html")
    blocks = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    product = next(b for b in blocks if b.get("@type") == "Product")
    assert product["name"] == prod["name"]["en"]
    assert product["offers"]["url"].endswith("?produto=coffee-arabica")
    assert 'href="/en/quote/?produto=coffee-arabica"' in html


def test_sitemap_lista_so_paginas_existentes_com_alternates(dist, langs):
    tree = ET.parse(dist / "sitemap.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    urls = tree.getroot().findall("s:url", ns)
    assert len(urls) >= 100
    for u in urls:
        loc = u.find("s:loc", ns).text
        rel = loc.replace("https://gbc-foods.com/", "").strip("/")
        assert (dist / rel / "index.html").exists(), loc
        alts = u.findall("x:link", ns)
        assert len(alts) >= len(langs), loc
    assert (dist / "robots.txt").read_text().strip().endswith("Sitemap: https://gbc-foods.com/sitemap.xml")


def test_headers_de_seguranca_e_cache(dist):
    h = read(dist, "_headers")
    for k in ("X-Content-Type-Options: nosniff", "X-Frame-Options: SAMEORIGIN", "Strict-Transport-Security"):
        assert k in h
    assert "/img/*" in h and "immutable" in h


def test_css_inclui_motion_e_reduced_motion(dist):
    css = read(dist, "css/site.css")
    assert "@view-transition" in css
    assert "prefers-reduced-motion" in css
    assert "picture.is-loaded" in css


def test_js_e_modulo_es_com_todos_os_arquivos(dist):
    html = read(dist, "pt/index.html")
    assert '<script type="module" src="/js/site.js"></script>' in html
    for name in ("site", "util", "quote-message", "quote-form", "consent", "nav", "motion", "observability"):
        assert (dist / "js" / f"{name}.js").exists(), name
    assert 'document.documentElement.classList.add("js")' in html


def test_window_gbc_tem_release_e_sentry_desligado(dist):
    html = read(dist, "en/index.html")
    assert re.search(r'release: "[0-9a-f]*"', html)
    assert 'sentry: { dsn: "", tracesSampleRate: 0.2 }' in html
    assert "js.sentry-cdn.com" not in html


def test_quatro_idiomas_no_seletor_e_no_rodape(dist, langs):
    html = read(dist, "es/index.html")
    for lang in langs:
        assert f'data-lang="{lang}"' in html


def test_404_multilingue(dist):
    html = read(dist, "404.html")
    assert 'content="noindex"' in html
    for lang in ("pt", "en", "es", "ru"):
        assert f'href="/{lang}/"' in html


def test_nada_vetado_no_site(dist):
    """Regras de conteúdo do AGENTS.md, seção 4: nada de posição de negociação nem contato da cooperativa."""
    vetados = [
        "540 cont",
        "NY+20",
        "99172-7003",
        "contato@coopernovarum",
        "não compramos em mercado aberto",
        "o que não fazemos",
    ]
    hits = []
    for f in dist.rglob("index.html"):
        txt = f.read_text(encoding="utf-8")
        hits += [(str(f.relative_to(dist)), v) for v in vetados if v.lower() in txt.lower()]
    assert not hits, hits


def test_categoria_embalados_aparece_quando_ha_produto(build_mod, dist):
    """O mesmo teste feito à mão no PR #14: com um produto embalado, sobem 8 páginas e a categoria entra em tudo."""
    base = next(p for p in build_mod.PRODUCTS if p["id"] == "milk-powder")
    fake = json.loads(json.dumps(base))
    fake.update({"id": "teste-embalado", "category": "embalados", "order": 99, "featured": False, "image": ""})
    for lang in build_mod.LANGS:
        fake["slug"][lang] = "teste-embalado"
        fake["name"][lang] = "Teste embalado"
    build_mod.PRODUCTS.append(fake)
    try:
        build_mod.WRITTEN.clear()
        build_mod.SITEMAP.clear()
        build_mod.build()
        assert len(build_mod.WRITTEN) == 122
        cat = read(dist, "pt/produtos/embalados/index.html")
        assert "Teste embalado" in cat
        assert 'hreflang="es" href="https://gbc-foods.com/es/productos/envasados/"' in cat
        home = read(dist, "pt/index.html")
        assert "Produtos embalados" in home
        assert "Três famílias" in read(dist, "pt/produtos/index.html")
    finally:
        build_mod.PRODUCTS.remove(fake)
        build_mod.WRITTEN.clear()
        build_mod.SITEMAP.clear()
        build_mod.build()  # deixa dist/ como estava para os outros testes


# ------------------------------------------------ seta no botão do hero (Issue #38)


def test_a_seta_esta_so_no_botao_principal_do_hero(dist, langs):
    for lang in langs:
        home = read(dist, f"{lang}/index.html")
        assert home.count("btn-seta") == 1, (lang, home.count("btn-seta"))
        # e ela está dentro do sólido, não do de contorno
        cta = home[home.index('<div class="cta">') : home.index("</div>", home.index('<div class="cta">'))]
        solido = cta[cta.index('class="btn solid"') : cta.index("</a>", cta.index('class="btn solid"'))]
        assert "btn-seta" in solido, lang
    # nenhuma outra página ganhou seta, mesmo tendo botão sólido
    outras = [f for f in dist.rglob("index.html") if f.parent.name != f.parts[-2] or True]
    com_seta = [str(f.relative_to(dist)) for f in outras if "btn-seta" in f.read_text(encoding="utf-8")]
    assert sorted(com_seta) == sorted(f"{lang}/index.html" for lang in langs), com_seta


def test_a_seta_nao_e_anunciada_por_leitor_de_tela(dist):
    home = read(dist, "pt/index.html")
    svg = home[home.index('<svg class="btn-seta"') : home.index("</svg>", home.index('<svg class="btn-seta"'))]
    assert 'aria-hidden="true"' in svg and 'focusable="false"' in svg


def test_o_avanco_da_seta_respeita_movimento_reduzido(dist):
    """AGENTS.md: toda animação nova entra também no bloco de prefers-reduced-motion."""
    css = read(dist, "css/site.css")
    assert ".btn:hover .btn-seta{transform:translateX(3px)}" in css
    reduzido = css[css.index("@media (prefers-reduced-motion:reduce){") :]
    assert ".btn-seta" in reduzido and "transform:none" in reduzido
