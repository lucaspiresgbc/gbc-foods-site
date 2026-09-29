"""Fixtures compartilhadas: o módulo build importado uma vez e o site gerado uma vez por sessão."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def build_mod():
    """O módulo build.py (importar não gera nada: o build só roda em build())."""
    return importlib.import_module("build")


@pytest.fixture(scope="session")
def dist(build_mod):
    """Gera o site inteiro uma vez e devolve a pasta dist/. Os testes de integração leem daqui."""
    build_mod.WRITTEN.clear()
    build_mod.SITEMAP.clear()
    build_mod.build()
    return build_mod.DIST


@pytest.fixture(scope="session")
def langs(build_mod):
    return list(build_mod.LANGS)
