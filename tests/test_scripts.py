"""check_links.py e check_contract.py: os dois guardiões do CI, testados como scripts."""

import json
import re
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


# --------------------------------------------------- paleta e contraste (Issue #32)

_CSS = Path(__file__).resolve().parents[1] / "static" / "site.css"


def _tokens():
    raiz = _CSS.read_text(encoding="utf-8").split(":root{", 1)[1].split("}", 1)[0]
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", raiz))


def _lum(hexa):
    h = hexa.lstrip("#")
    canais = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    canais = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def _contraste(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_fundo_e_branco_puro():
    assert _tokens()["paper"].upper() == "#FFFFFF"


def test_toda_cor_de_texto_passa_em_contraste_sobre_o_fundo():
    """O vermelho antigo dava 4,32 e reprovava. A paleta escura existe para isso."""
    t = _tokens()
    fundo = t["paper"]
    reprovados = {
        nome: round(_contraste(t[nome], fundo), 2)
        for nome in ("navy", "navy-soft", "red", "blue", "ink", "text", "grey")
        if _contraste(t[nome], fundo) < 4.5
    }
    assert not reprovados, reprovados


def test_nenhuma_cor_da_paleta_antiga_sobrou_no_repositorio():
    raiz = _CSS.parents[1]
    antigas = ("#26375E", "#1B2842", "#3E4F76", "#EC2337", "#F0453A", "#1D7AC1", "#169AD2", "#FBFBF9")
    achados = []
    for alvo in ("static", "templates"):
        for f in (raiz / alvo).rglob("*"):
            if f.suffix.lower() not in (".css", ".html", ".svg", ".js"):
                continue
            texto = f.read_text(encoding="utf-8", errors="ignore").upper()
            achados += [(str(f.relative_to(raiz)), c) for c in antigas if c in texto]
    assert not achados, achados
