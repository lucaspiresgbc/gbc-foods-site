"""Unitários de build.py: as funções puras que montam URLs, textos e HTML."""

import html
import re

import pytest


def test_url_home_e_pagina(build_mod, langs):
    for lang in langs:
        assert build_mod.url("home", lang) == f"/{lang}/"
    assert build_mod.url("company", "pt") == "/pt/empresa/"
    assert build_mod.url("packaged", "es") == "/es/productos/envasados/"


def test_product_url_usa_slug_do_idioma(build_mod):
    prod = next(p for p in build_mod.PRODUCTS if p["id"] == "coffee-arabica")
    for lang in build_mod.LANGS:
        u = build_mod.product_url(prod, lang)
        assert u.startswith(f"/{lang}/{build_mod.ROUTES['products'][lang]}/")
        assert u.endswith(prod["slug"][lang] + "/")


def test_post_url_inexistente_devolve_none(build_mod):
    assert build_mod.post_url("nao-existe", "pt") is None
    first = build_mod.POSTS["pt"][0]
    assert build_mod.post_url(first["id"], "pt") == f"/pt/blog/{first['slug']}/"


def test_t_le_texto_da_interface(build_mod):
    assert build_mod.t("nav.home", "pt") == "Home"
    assert build_mod.t("nav.home", "ru") == "Главная"
    with pytest.raises(KeyError):
        build_mod.t("nav.nao-existe", "pt")


def test_L_pega_idioma_ou_devolve_como_esta(build_mod):
    assert build_mod.L({"pt": "a", "en": "b"}, "en") == "b"
    assert build_mod.L("texto", "en") == "texto"
    assert build_mod.L({"pt": "a"}, "ru") == {"pt": "a"}


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Café Verde Arábica", "cafe-verde-arabica"),
        ("Açúcar cristal ICUMSA 45", "acucar-cristal-icumsa-45"),
        ("  --Amêndoas de Portugal--  ", "amendoas-de-portugal"),
        ("Leite em pó (25 kg)", "leite-em-po-25-kg"),
    ],
)
def test_slugify(build_mod, texto, esperado):
    assert build_mod.slugify(texto) == esperado


def test_fmt_date_por_idioma(build_mod):
    assert build_mod.fmt_date("2026-09-29", "en") == "29 September 2026"
    assert build_mod.fmt_date("2026-09-29", "pt") == "29 de setembro de 2026"
    assert build_mod.fmt_date("2026-09-29", "ru").endswith(" г.")


def test_parse_front_matter(build_mod):
    meta, body = build_mod.parse_front_matter("---\ntitle: Olá\ntags: [a, b]\n---\nCorpo\n")
    assert meta == {"title": "Olá", "tags": ["a", "b"]}
    assert body == "Corpo\n"
    meta2, body2 = build_mod.parse_front_matter("sem cabeçalho")
    assert meta2 == {} and body2 == "sem cabeçalho"


def test_reading_minutes_nunca_zero(build_mod):
    assert build_mod.reading_minutes("uma palavra") >= 1
    assert build_mod.reading_minutes(" ".join(["palavra"] * 1000)) >= 4


def test_picture_gera_srcset_lazy_e_alt_escapado(build_mod):
    build_mod.IMG_CACHE["coffee/coffee-green.jpg"] = (1600, 1067)
    out = build_mod.picture("coffee/coffee-green.jpg", alt='Grão "verde" & cru')
    assert '<source type="image/webp" srcset="/img/coffee/coffee-green-640.webp 640w' in out
    assert 'loading="lazy"' in out and 'decoding="async"' in out
    assert 'width="1600" height="1067"' in out
    assert html.escape('Grão "verde" & cru') in out
    assert "fetchpriority" not in out


def test_picture_eager_com_prioridade(build_mod):
    out = build_mod.picture("products/ship-sea.jpg", loading="eager", fetchpriority="high")
    assert 'loading="eager"' in out and 'fetchpriority="high"' in out


def test_picture_vazio(build_mod):
    assert build_mod.picture("") == ""


def test_placeholder_svg_e_screen_svg_sao_svg_validos(build_mod):
    ph = build_mod.placeholder_svg("Leite em pó")
    assert ph.startswith("<svg") and ph.endswith("</svg>")
    assert 'aria-hidden="true"' in build_mod.screen_svg()


def test_org_jsonld_tem_identidade_e_idiomas(build_mod):
    ld = build_mod.org_jsonld()
    assert ld["@type"] == "Organization"
    assert ld["@id"] == build_mod.DOMAIN + "/#org"
    assert "GBC" in ld["name"]


def test_breadcrumb_jsonld_posicoes(build_mod):
    ld = build_mod.breadcrumb_jsonld([("Home", "/pt/"), ("Produtos", "/pt/produtos/")])
    assert ld["@type"] == "BreadcrumbList"
    assert [i["position"] for i in ld["itemListElement"]] == [1, 2]
    assert ld["itemListElement"][1]["item"] == build_mod.DOMAIN + "/pt/produtos/"


def test_release_id_e_sha_curto(build_mod, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "abcdef1234567890")
    assert build_mod.release_id() == "abcdef1"
    monkeypatch.delenv("GITHUB_SHA")
    monkeypatch.setenv("SITE_RELEASE", "v2.1.0-teste")
    assert build_mod.release_id() == "v2.1.0-"
    monkeypatch.delenv("SITE_RELEASE")
    assert re.fullmatch(r"[0-9a-f]{7,}|", build_mod.release_id())


def test_sentry_so_com_dsn_valido(build_mod):
    assert build_mod.SENTRY_OK is False  # config.json entregue com sentry_dsn vazio
    assert re.match(r"^https://[a-f0-9]{16,}@", "https://0123456789abcdef0123456789abcdef@o1.ingest.sentry.io/1", re.I)


def test_whatsapp_e_ga_ainda_sao_exemplos(build_mod):
    """Enquanto as Issues #4 e #5 estiverem abertas, o site é gerado com os avisos, não com valores falsos."""
    assert build_mod.WA_OK is False
    assert build_mod.GA_OK is False
