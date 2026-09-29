#!/usr/bin/env python3
"""Confere os links internos do site gerado em dist/.

Uso:  python3 check_links.py [--dist dist]
Sai com código 1 se houver link interno apontando para página ou arquivo inexistente.
Roda depois de `python3 build.py`; o CI executa este script em todo PR.
"""

import argparse
import re
import sys
from pathlib import Path

HREF = re.compile(r'(?:href|src|content)="(/[^"#?]*)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    a = ap.parse_args()
    dist = Path(a.dist)
    if not dist.is_dir():
        sys.exit(f"pasta {dist} não existe — rode python3 build.py antes")

    pages = set()
    for f in dist.rglob("*.html"):
        rel = "/" + f.relative_to(dist).as_posix()
        pages.add(rel)
        if f.name == "index.html":
            pages.add(rel[: -len("index.html")])

    bad, checked = [], 0
    for f in dist.rglob("*.html"):
        html = f.read_text(encoding="utf-8", errors="ignore")
        for href in HREF.findall(html):
            if href.startswith("//"):
                continue  # protocolo-relativo = externo
            checked += 1
            cand = href if (href.endswith("/") or href.endswith(".html")) else href + "/"
            if cand in pages or (cand + "index.html") in pages:
                continue
            if (dist / href.lstrip("/")).is_file():
                continue  # imagem, css, js, sitemap, etc.
            bad.append((f.relative_to(dist).as_posix(), href))

    print(f"{checked} links internos conferidos em {len(pages) // 2 or len(pages)} páginas")
    if bad:
        print(f"ERRO — {len(bad)} link(s) interno(s) quebrado(s):")
        for page, href in bad:
            print(f"  {page}  →  {href}")
        sys.exit(1)
    print("ok — 0 links internos quebrados")


if __name__ == "__main__":
    main()
