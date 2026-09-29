#!/usr/bin/env python3
"""Contratos de arquitetura do repositório — as regras estruturais que nenhum PR pode quebrar.

Rodar: python3 check_contract.py            (sai com 1 se algum contrato for violado)
       python3 check_contract.py --update   (regrava routes.lock.json com os slugs atuais — só com decisão explícita)

Contratos:
  1. URLs publicadas são estáveis: nenhum slug de routes.json, de produto ou de artigo do blog muda ou some
     depois de registrado em routes.lock.json (o Google indexa a URL; renomear = perder a página).
  2. Toda página, produto e texto de interface existe nos 4 idiomas (delegado a build.py --check; aqui só a
     estrutura dos produtos: id único, order único, categoria válida, slug por idioma único).
  3. Nenhum segredo versionado (tokens, chaves privadas, JWT).
  4. dist/ e node_modules/ fora do git; .gitignore os cobre.
  5. Templates só referenciam rotas que existem em routes.json; nenhum <img> sem alt; nenhum handler inline
     (onclick=...) nem document.write — compatível com uma CSP futura.
  6. JavaScript do site sem dependência externa e sem código gerado dentro de dist/ (dist é sempre regenerada).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
LANGS = ("pt", "en", "es", "ru")
CATEGORIES = {"granel", "po", "embalados"}
LOCK = ROOT / "routes.lock.json"

problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False)
    return out.stdout.split("\n") if out.returncode == 0 else []


# ---------- 1. URLs estáveis
def current_slugs() -> dict:
    routes = {k: v for k, v in load_json(CONTENT / "routes.json").items() if not k.startswith("_")}
    products = {}
    for p in sorted((CONTENT / "products").glob("*.json")):
        d = load_json(p)
        products[d["id"]] = d["slug"]
    posts = {}
    for folder in sorted((CONTENT / "blog").iterdir()):
        if not folder.is_dir():
            continue
        slugs = {}
        for lang in LANGS:
            md = folder / f"{lang}.md"
            if md.exists():
                m = re.search(r"^slug:\s*(.+)$", md.read_text(encoding="utf-8"), re.M)
                if m:
                    slugs[lang] = m.group(1).strip().strip("'\"")
        posts[folder.name] = slugs
    return {"routes": routes, "products": products, "posts": posts}


def check_urls(update: bool) -> None:
    now = current_slugs()
    if update or not LOCK.exists():
        LOCK.write_text(json.dumps(now, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"routes.lock.json {'atualizado' if update else 'criado'} com os slugs atuais")
        return
    locked = load_json(LOCK)
    for group in ("routes", "products", "posts"):
        for key, langs in locked.get(group, {}).items():
            if key not in now[group]:
                fail(
                    f"URL estável: {group}.{key} sumiu (estava em routes.lock.json). Remover uma URL publicada exige decisão registrada e redirect."
                )
                continue
            for lang, slug in langs.items():
                if now[group][key].get(lang) != slug:
                    fail(
                        f"URL estável: {group}.{key}.{lang} mudou de '{slug}' para '{now[group][key].get(lang)}'. "
                        "Slugs publicados não se renomeiam; se for decisão consciente, rode --update e registre o redirect."
                    )


# ---------- 2. estrutura dos produtos
def check_products() -> None:
    ids, orders, slugs = set(), set(), {lang: set() for lang in LANGS}
    for p in sorted((CONTENT / "products").glob("*.json")):
        d = load_json(p)
        if d.get("category") not in CATEGORIES:
            fail(f"{p.name}: category '{d.get('category')}' inválida (use {sorted(CATEGORIES)})")
        if d["id"] in ids:
            fail(f"{p.name}: id '{d['id']}' repetido")
        ids.add(d["id"])
        if d.get("order") in orders:
            fail(f"{p.name}: order {d.get('order')} repetido")
        orders.add(d.get("order"))
        for lang in LANGS:
            s = d.get("slug", {}).get(lang)
            if not s:
                fail(f"{p.name}: falta slug.{lang}")
            elif s in slugs[lang]:
                fail(f"{p.name}: slug.{lang} '{s}' repetido")
            elif not re.fullmatch(r"[a-z0-9-]+", s):
                fail(f"{p.name}: slug.{lang} '{s}' só pode ter a-z, 0-9 e hífen")
            slugs[lang].add(s)
    for f in (CONTENT / "products").iterdir():
        if f.suffix != ".json" and not f.name.endswith(".json.exemplo"):
            fail(f"content/products/{f.name}: só .json (produto) ou .json.exemplo (modelo)")


# ---------- 3. segredos
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "chave privada"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{20,}"), "JWT"),
    (re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"), "chave de API"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "chave AWS"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "token GitHub"),
    (
        re.compile(
            r"(?i)\b(CF_API_TOKEN|SUPABASE_SERVICE_ROLE_KEY|RESEND_API_KEY|CODECOV_TOKEN|SENTRY_AUTH_TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}"
        ),
        "segredo em texto",
    ),
]
TEXT_EXT = {".py", ".js", ".cjs", ".mjs", ".json", ".md", ".html", ".css", ".yml", ".yaml", ".toml", ".txt", ".jsonc"}


def check_secrets(files: list[str]) -> None:
    for rel in files:
        p = ROOT / rel
        if not p.is_file() or p.suffix not in TEXT_EXT or rel == "check_contract.py":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for rx, what in SECRET_PATTERNS:
            if rx.search(text):
                fail(f"segredo versionado ({what}) em {rel}")


# ---------- 4. gerados fora do git
def check_ignored(files: list[str]) -> None:
    for bad in ("dist/", "node_modules/"):
        if any(f.startswith(bad) for f in files):
            fail(f"{bad} está versionada — é gerada/instalada, nunca entra no git")
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    for need in ("dist/", "node_modules/", ".env"):
        if need not in gi:
            fail(f".gitignore precisa conter '{need}'")


# ---------- 5. templates
def check_templates() -> None:
    routes = load_json(CONTENT / "routes.json")
    for t in sorted((ROOT / "templates").glob("*.html")):
        src = t.read_text(encoding="utf-8")
        for key in re.findall(r"url\(\s*['\"]([a-z_]+)['\"]", src):
            if key not in routes:
                fail(f"templates/{t.name}: url('{key}') não existe em routes.json")
        for tag in re.findall(r"<img\b[^>]*>", src):
            if " alt=" not in tag:
                fail(f"templates/{t.name}: <img> sem alt: {tag[:60]}…")
        if re.search(r"\son[a-z]+=", src):
            fail(f"templates/{t.name}: handler inline (onclick= etc.) — use site.js")
        if "document.write" in src:
            fail(f"templates/{t.name}: document.write")


# ---------- 6. javascript do site
def check_js() -> None:
    for js in sorted((ROOT / "static" / "js").glob("*.js")):
        src = js.read_text(encoding="utf-8")
        for spec in re.findall(r"^\s*import\s.*?from\s+['\"]([^'\"]+)['\"]", src, re.M):
            if not spec.startswith("./"):
                fail(f"static/js/{js.name}: import '{spec}' — o site não tem bundler; só imports locais ./x.js")
        if "document.write" in src or "eval(" in src:
            fail(f"static/js/{js.name}: document.write/eval")


def main() -> int:
    update = "--update" in sys.argv
    files = tracked_files()
    check_urls(update)
    check_products()
    check_secrets(files)
    check_ignored(files)
    check_templates()
    check_js()
    if problems:
        print(f"ERRO — {len(problems)} contrato(s) violado(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("ok — contratos de arquitetura respeitados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
