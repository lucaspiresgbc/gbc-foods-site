"""check_links.py e check_contract.py: os dois guardiões do CI, testados como scripts."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script, *args, cwd=ROOT):
    """Roda o script a partir de `cwd` — os scripts se orientam pela própria pasta, então a cópia em tmp é a que vale."""
    return subprocess.run(
        [sys.executable, str(Path(cwd) / script), *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_check_links_passa_no_site_gerado(dist):
    out = run("check_links.py")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "0 links internos quebrados" in out.stdout


def test_check_links_detecta_link_quebrado(dist, tmp_path):
    fake = tmp_path / "dist"
    shutil.copytree(dist / "pt", fake / "pt")
    (fake / "pt" / "index.html").write_text('<a href="/pt/pagina-que-nao-existe/">x</a>', encoding="utf-8")
    out = run("check_links.py", "--dist", str(fake))
    assert out.returncode == 1
    assert "pagina-que-nao-existe" in out.stdout


def test_check_links_sem_dist(tmp_path):
    out = run("check_links.py", "--dist", str(tmp_path / "nada"))
    assert out.returncode == 1


def test_check_contract_passa_no_repositorio():
    out = run("check_contract.py")
    assert out.returncode == 0, out.stdout + out.stderr


def test_check_contract_detecta_slug_renomeado(tmp_path):
    """Copia o repositório (só o necessário) e renomeia um slug: o contrato de URL estável tem de falhar."""
    for item in ("content", "templates", "static/js", "routes.lock.json", ".gitignore", "check_contract.py"):
        src = ROOT / item
        dst = tmp_path / item
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("img"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    routes = json.loads((tmp_path / "content" / "routes.json").read_text(encoding="utf-8"))
    routes["powders"]["en"] = "products/powder"
    (tmp_path / "content" / "routes.json").write_text(json.dumps(routes, ensure_ascii=False), encoding="utf-8")
    out = run("check_contract.py", cwd=tmp_path)
    # fora de um repositório git, git ls-files devolve vazio — os outros contratos seguem valendo
    assert out.returncode == 1
    assert "URL estável: routes.powders.en mudou" in out.stdout


def test_check_contract_detecta_segredo(tmp_path):
    for item in ("content", "templates", "static/js", "routes.lock.json", ".gitignore", "check_contract.py"):
        src = ROOT / item
        dst = tmp_path / item
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("img"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    # montado em partes para o próprio check_contract.py não acusar este arquivo de teste
    falso = "CF_API_" + "TOKEN=" + "abcdefghijklmnopqrstuvwxyz0123456789"
    (tmp_path / "segredo.md").write_text(falso + "\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    out = run("check_contract.py", cwd=tmp_path)
    assert out.returncode == 1
    assert "segredo versionado" in out.stdout
