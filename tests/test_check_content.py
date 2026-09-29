"""build.py --check (check_content) e os dois scripts de verificação importados como módulos."""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_content_passa_com_o_conteudo_atual(build_mod, capsys):
    assert build_mod.check_content() == []
    assert "ok — conteúdo completo nos 4 idiomas" in capsys.readouterr().out


def test_check_content_detecta_idioma_faltando_em_pagina(build_mod, monkeypatch, capsys):
    pages = {
        k: {lang: (dict(v) if isinstance(v, dict) else v) for lang, v in page.items()}
        for k, page in build_mod.PAGES.items()
    }
    del pages["company"]["ru"]["title"]
    monkeypatch.setattr(build_mod, "PAGES", pages)
    problems = build_mod.check_content()
    assert any("pages/company.json" in p and "ru" in p for p in problems), problems
    assert "Conteúdo incompleto" in capsys.readouterr().out


def test_check_content_detecta_texto_vazio_na_interface(build_mod, monkeypatch):
    ui = {k: (dict(v) if isinstance(v, dict) else v) for k, v in build_mod.UI.items()}
    ui["nav"] = dict(ui["nav"])
    ui["nav"]["home"] = dict(ui["nav"]["home"], es="")
    monkeypatch.setattr(build_mod, "UI", ui)
    problems = build_mod.check_content()
    assert any("ui.json.nav.home" in p and "es" in p for p in problems), problems


def test_check_content_detecta_rota_sem_idioma(build_mod, monkeypatch):
    routes = {k: dict(v) if isinstance(v, dict) else v for k, v in build_mod.ROUTES.items()}
    routes["blog"] = {"pt": "blog", "en": "blog", "es": "blog"}  # sem ru
    monkeypatch.setattr(build_mod, "ROUTES", routes)
    problems = build_mod.check_content()
    assert any("routes.json.blog" in p and "ru" in p for p in problems), problems


def test_check_content_detecta_imagem_inexistente(build_mod, monkeypatch):
    products = [dict(p) for p in build_mod.PRODUCTS]
    products[0]["image"] = "products/nao-existe.jpg"
    monkeypatch.setattr(build_mod, "PRODUCTS", products)
    problems = build_mod.check_content()
    assert any("imagem não encontrada" in p for p in problems), problems


def test_check_links_como_modulo(dist, monkeypatch, capsys):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    mod = importlib.import_module("check_links")
    monkeypatch.setattr(sys, "argv", ["check_links.py", "--dist", str(dist)])
    mod.main()
    assert "0 links internos quebrados" in capsys.readouterr().out


def test_check_contract_como_modulo(capsys, monkeypatch):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    mod = importlib.import_module("check_contract")
    monkeypatch.setattr(sys, "argv", ["check_contract.py"])
    assert mod.main() == 0
    assert "contratos de arquitetura respeitados" in capsys.readouterr().out
    slugs = mod.current_slugs()
    assert set(slugs) == {"routes", "products", "posts"}
    assert "packaged" in slugs["routes"] and "coffee-arabica" in slugs["products"]
