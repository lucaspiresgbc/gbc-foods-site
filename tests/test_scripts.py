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


# ---------------------------------------- links e anel de foco (Issue #36)

_CSS = ROOT / "static" / "site.css"


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


def _regra(seletor):
    css = _CSS.read_text(encoding="utf-8")
    i = css.index(seletor)
    return css[i : css.index("}", i) + 1]


def test_link_de_texto_usa_sublinhado_e_nao_borda():
    for sel in (".more{", ".head-links a{"):
        r = _regra(sel)
        assert "border-bottom" not in r, sel
        assert "text-decoration-thickness" in r and "text-underline-offset" in r, sel
        # neutro em repouso: o vermelho só entra no hover
        assert "text-decoration-color:var(--line)" in r, sel


def test_existe_um_terceiro_nivel_de_acao():
    r = _regra(".btn.quiet{")
    assert "border-radius:999px" in r and "background:transparent" in r


def test_anel_de_foco_do_botao_principal_tem_contraste():
    """O anel padrão é vermelho; sobre o botão vermelho ele dá 1,16:1 e reprova.

    A saída é anel duplo: branco por dentro, que contrasta com o botão, e navy por
    fora, que contrasta com a página. Cada um precisa dos seus 3:1 contra o que
    está atrás dele.
    """
    t = _tokens()
    for classe, grad in (
        (".btn.solid:focus-visible", ("red-warm", "red")),
        (".btn.solid.blue:focus-visible", ("blue-light", "blue")),
    ):
        regra = _regra(classe)
        assert "outline-color:var(--navy)" in regra, classe
        assert "inset 0 0 0 2.5px #fff" in regra, classe
        for ponta in grad:
            r = _contraste("#FFFFFF", t[ponta])
            assert r >= 3.0, (classe, ponta, t[ponta], round(r, 2))
    assert _contraste(t["navy"], t["paper"]) >= 3.0
    # e o anel vermelho continua servindo onde o fundo é claro
    assert _contraste(t["red"], t["paper"]) >= 3.0


def test_a_sombra_do_botao_e_token_para_o_foco_nao_a_repetir():
    assert "--sh-solid:" in _CSS.read_text(encoding="utf-8")
    assert "box-shadow:var(--sh-solid)" in _regra(".btn.solid{")
