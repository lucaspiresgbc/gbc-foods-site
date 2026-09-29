#!/usr/bin/env python3
"""Publica a pasta public/ como um Worker com static assets, direto pela API da Cloudflare.

Uso:
  CF_API_TOKEN=... CF_ACCOUNT_ID=... python3 cf-deploy.py [--name gbc-foods-site] [--dir public] [--dry-run]

Fluxo (documentação "Direct Upload" da Cloudflare):
  1. manifesto  → POST /accounts/{acct}/workers/scripts/{name}/assets-upload-session
  2. arquivos   → POST /accounts/{acct}/workers/assets/upload?base64=true  (por bucket)
  3. versão     → PUT  /accounts/{acct}/workers/scripts/{name}  (multipart: metadata + módulo)
  4. domínio    → POST /accounts/{acct}/workers/scripts/{name}/subdomain  (workers.dev)
"""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

API = "https://api.cloudflare.com/client/v4"

MAIN_JS = """export default {
  async fetch(request, env) { return env.ASSETS.fetch(request); }
};
"""


def req(method, url, headers=None, data=None, ctype=None):
    h = dict(headers or {})
    if ctype:
        h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            body = resp.read()
            return resp.status, json.loads(body or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body or b"{}")
        except Exception:
            return e.code, {"raw": body[:500].decode("utf-8", "replace")}


def multipart(parts):
    """parts: list of (name, filename|None, content_bytes, content_type). Returns (body, content_type)."""
    b = "----gbc" + uuid.uuid4().hex
    out = bytearray()
    for name, filename, content, ctype in parts:
        out += f"--{b}\r\n".encode()
        disp = f'Content-Disposition: form-data; name="{name}"'
        if filename:
            disp += f'; filename="{filename}"'
        out += (disp + "\r\n").encode()
        out += f"Content-Type: {ctype}\r\n\r\n".encode()
        out += content + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def manifesto(dirpath):
    m, files = {}, {}
    for root, _, names in os.walk(dirpath):
        for n in names:
            full = os.path.join(root, n)
            rel = "/" + os.path.relpath(full, dirpath).replace(os.sep, "/")
            if os.path.basename(rel) in ("LEIA-ME.txt", ".keep", ".DS_Store"):
                continue
            with open(full, "rb") as fh:
                data = fh.read()
            # hash de 32 hex: sha256 do conteúdo + extensão, como o wrangler faz
            ext = os.path.splitext(n)[1]
            h = hashlib.sha256(data + ext.encode()).hexdigest()[:32]
            m[rel] = {"hash": h, "size": len(data)}
            files[h] = (rel, data)
    return m, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="gbc-foods-site")
    ap.add_argument("--dir", default="public")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tok, acct = os.environ.get("CF_API_TOKEN"), os.environ.get("CF_ACCOUNT_ID")
    m, files = manifesto(a.dir)
    print(f"{len(m)} arquivos no manifesto ({sum(v['size'] for v in m.values()) / 1024:.0f} KB)")
    for k in sorted(m):
        print("  ", k, m[k]["size"])
    if a.dry_run:
        return
    if not tok or not acct:
        sys.exit("defina CF_API_TOKEN e CF_ACCOUNT_ID")
    H = {"Authorization": f"Bearer {tok}"}

    # 0. token ok?
    st, j = req("GET", f"{API}/user/tokens/verify", H)
    print("token:", st, j.get("result", {}).get("status"))
    if st != 200:
        sys.exit(json.dumps(j)[:400])

    # 1. sessão de upload
    st, j = req(
        "POST",
        f"{API}/accounts/{acct}/workers/scripts/{a.name}/assets-upload-session",
        H,
        json.dumps({"manifest": m}).encode(),
        "application/json",
    )
    if st != 200 or not j.get("success"):
        sys.exit("manifesto: " + json.dumps(j)[:600])
    jwt, buckets = j["result"]["jwt"], j["result"].get("buckets") or []
    print(f"sessão ok — {len(buckets)} lote(s) para enviar")

    # 2. arquivos
    completion = jwt
    for i, bucket in enumerate(buckets, 1):
        parts = []
        for h in bucket:
            rel, data = files[h]
            ctype = mimetypes.guess_type(rel)[0] or (
                "text/plain" if rel.endswith(("_headers", "_redirects", ".txt")) else "application/octet-stream"
            )
            parts.append((h, h, base64.b64encode(data), ctype))
        body, ct = multipart(parts)
        st, j = req(
            "POST",
            f"{API}/accounts/{acct}/workers/assets/upload?base64=true",
            {"Authorization": f"Bearer {jwt}"},
            body,
            ct,
        )
        if st not in (200, 201) or not j.get("success"):
            sys.exit(f"upload lote {i}: " + json.dumps(j)[:600])
        if j["result"].get("jwt"):
            completion = j["result"]["jwt"]
        print(f"lote {i}/{len(buckets)} enviado ({len(bucket)} arquivo(s))")

    # 3. versão do Worker
    cfg = {"html_handling": "auto-trailing-slash", "not_found_handling": "404-page"}
    hp = os.path.join(a.dir, "_headers")
    if os.path.exists(hp):
        with open(hp, encoding="utf-8") as fh:
            cfg["_headers"] = fh.read()
    rp = os.path.join(a.dir, "_redirects")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            cfg["_redirects"] = fh.read()
    meta = {
        "main_module": "main.js",
        "compatibility_date": "2026-09-01",
        "assets": {"jwt": completion, "config": cfg},
        "bindings": [{"type": "assets", "name": "ASSETS"}],
        "observability": {"enabled": True},
    }
    body, ct = multipart(
        [
            ("metadata", None, json.dumps(meta).encode(), "application/json"),
            ("main.js", "main.js", MAIN_JS.encode(), "application/javascript+module"),
        ]
    )
    st, j = req("PUT", f"{API}/accounts/{acct}/workers/scripts/{a.name}", H, body, ct)
    if st != 200 or not j.get("success"):
        # alguns planos rejeitam _headers/_redirects no config: tenta sem
        if "_headers" in cfg or "_redirects" in cfg:
            cfg.pop("_headers", None)
            cfg.pop("_redirects", None)
            body, ct = multipart(
                [
                    ("metadata", None, json.dumps(meta).encode(), "application/json"),
                    ("main.js", "main.js", MAIN_JS.encode(), "application/javascript+module"),
                ]
            )
            st, j = req("PUT", f"{API}/accounts/{acct}/workers/scripts/{a.name}", H, body, ct)
            print("aviso: _headers não aceito pela API; publicado sem os cabeçalhos extras")
        if st != 200 or not j.get("success"):
            sys.exit("versão: " + json.dumps(j)[:800])
    print("worker publicado:", j["result"].get("id"))

    # 4. domínio gratuito workers.dev
    st, j = req(
        "POST",
        f"{API}/accounts/{acct}/workers/scripts/{a.name}/subdomain",
        H,
        json.dumps({"enabled": True, "previews_enabled": False}).encode(),
        "application/json",
    )
    print("subdomínio:", st, j.get("success"))
    st, j = req("GET", f"{API}/accounts/{acct}/workers/subdomain", H)
    sub = j.get("result", {}).get("subdomain")
    if sub:
        print(f"\nNO AR: https://{a.name}.{sub}.workers.dev\n")
    else:
        print("não consegui ler o subdomínio da conta:", json.dumps(j)[:300])


if __name__ == "__main__":
    main()
