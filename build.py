#!/usr/bin/env python3
"""
Gerador do site GBC Foods.

    python3 build.py            → gera a pasta dist/ (o site pronto para publicar)
    python3 build.py --serve    → gera e abre um servidor local em http://localhost:8080

Tudo o que aparece no site vem da pasta content/ (textos, produtos, blog, políticas)
e das imagens em static/img/. Este arquivo só monta as páginas; não há texto aqui.
Requisitos: Python 3.9+ e  pip install jinja2 markdown pyyaml pillow
"""

import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"

try:
    import markdown as md_lib
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    sys.exit("Faltam pacotes. Rode:  pip install jinja2 markdown pyyaml pillow")
try:
    import yaml
except ImportError:
    yaml = None
try:
    from PIL import Image
except ImportError:
    Image = None

# ----------------------------------------------------------------------------- utilidades


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def parse_front_matter(text):
    """Separa o cabeçalho (--- ... ---) do corpo de um .md."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        return {}, text
    head, body = m.group(1), m.group(2)
    if yaml:
        meta = yaml.safe_load(head) or {}
    else:  # parser mínimo, caso o PyYAML não esteja instalado
        meta = {}
        for line in head.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
            else:
                v = v.strip("\"'")
            meta[k.strip()] = v
    if isinstance(meta.get("date"), (datetime.date, datetime.datetime)):
        meta["date"] = meta["date"].isoformat()[:10]
    if isinstance(meta.get("updated"), (datetime.date, datetime.datetime)):
        meta["updated"] = meta["updated"].isoformat()[:10]
    return meta, body


def md_to_html(text):
    return md_lib.markdown(text, extensions=["tables", "sane_lists", "smarty"], output_format="html5")


def reading_minutes(text):
    words = len(re.findall(r"\w+", text))
    return max(1, round(words / 200))


MONTHS = {
    "pt": [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ],
    "es": [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "ru": [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ],
}


def fmt_date(iso, lang):
    y, m, d = [int(x) for x in iso.split("-")]
    name = MONTHS[lang][m - 1]
    if lang == "en":
        return f"{d} {name} {y}"
    if lang == "ru":
        return f"{d} {name} {y} г."
    return f"{d} de {name} de {y}"


def slugify(s):
    s = s.lower()
    s = re.sub(r"[àáâãä]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôõö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = s.replace("ç", "c").replace("ñ", "n")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# ----------------------------------------------------------------------------- carga do conteúdo

CFG = load_json(CONTENT / "config.json")
UI = load_json(CONTENT / "ui.json")
ROUTES = load_json(CONTENT / "routes.json")
STEPS = load_json(CONTENT / "steps.json")
PAGES = {p.stem: load_json(p) for p in sorted((CONTENT / "pages").glob("*.json"))}
LANGS = CFG["idiomas"]
DOMAIN = CFG["dominio"].rstrip("/")
WA = re.sub(r"\D", "", CFG.get("whatsapp_numero", ""))
WA_OK = bool(WA) and "X" not in CFG.get("whatsapp_numero", "").upper()
GA = CFG.get("ga4_measurement_id", "")
GA_OK = bool(GA) and "X" not in GA.upper()
SENTRY_DSN = CFG.get("sentry_dsn", "").strip()
SENTRY_OK = bool(re.match(r"^https://[a-f0-9]{16,}@", SENTRY_DSN, re.I))
SENTRY_RATE = CFG.get("sentry_traces_sample_rate", 0.2)


def release_id() -> str:
    """Identificador da versão publicada (SHA curto): o CI passa GITHUB_SHA; localmente vem do git."""
    env = os.environ.get("SITE_RELEASE") or os.environ.get("GITHUB_SHA", "")
    if env:
        return env[:7]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except OSError:
        return ""


RELEASE = release_id()

PRODUCTS = []
for p in sorted((CONTENT / "products").glob("*.json")):
    d = load_json(p)
    d.setdefault("gallery", [])
    d.setdefault("featured", False)
    PRODUCTS.append(d)
PRODUCTS.sort(key=lambda x: x.get("order", 99))

POSTS = {l: [] for l in LANGS}
for folder in sorted((CONTENT / "blog").iterdir()):
    if not folder.is_dir():
        continue
    for lang in LANGS:
        f = folder / f"{lang}.md"
        if not f.exists():
            continue
        meta, body = parse_front_matter(f.read_text(encoding="utf-8"))
        meta["id"] = folder.name
        meta["lang"] = lang
        meta["body_html"] = md_to_html(body)
        meta["minutes"] = reading_minutes(body)
        meta.setdefault("slug", slugify(meta.get("title", folder.name)))
        meta.setdefault("date", "2026-01-01")
        meta.setdefault("tags", [])
        meta["date_fmt"] = fmt_date(meta["date"], lang)
        POSTS[lang].append(meta)
for lang in LANGS:
    POSTS[lang].sort(key=lambda m: m["date"], reverse=True)

LEGAL = {}
for kind in ("privacy", "cookies"):
    LEGAL[kind] = {}
    for lang in LANGS:
        f = CONTENT / "legal" / kind / f"{lang}.md"
        meta, body = parse_front_matter(f.read_text(encoding="utf-8"))
        LEGAL[kind][lang] = {"meta": meta, "body": body}

# ----------------------------------------------------------------------------- URLs


def url(page, lang):
    slug = ROUTES[page][lang]
    return f"/{lang}/" + (slug + "/" if slug else "")


def product_url(prod, lang):
    return f"/{lang}/{ROUTES['products'][lang]}/{prod['slug'][lang]}/"


def post_url(post_id, lang):
    for m in POSTS[lang]:
        if m["id"] == post_id:
            return f"/{lang}/{ROUTES['blog'][lang]}/{m['slug']}/"
    return None


def t(key_path, lang):
    """t('nav.home', 'pt') → texto da interface."""
    node = UI
    for k in key_path.split("."):
        node = node[k]
    return node[lang]


def L(obj, lang):
    """Pega o idioma de um campo {pt,en,es,ru}; se não for dicionário, devolve como está."""
    if isinstance(obj, dict) and lang in obj:
        return obj[lang]
    return obj


# ----------------------------------------------------------------------------- imagens

IMG_WIDTHS = (640, 1100, 1600)
IMG_CACHE = {}


def process_images():
    """Converte cada foto de static/img em .webp em três larguras + jpg de fallback."""
    src_root = STATIC / "img"
    out_root = DIST / "img"
    for src in sorted(src_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        dst = out_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() not in (".jpg", ".jpeg", ".png") or Image is None or "brand" in rel.parts:
            shutil.copy2(src, dst)
            continue
        im = Image.open(src)
        im = im.convert("RGB") if im.mode not in ("RGB",) else im
        w, h = im.size
        IMG_CACHE[str(rel).replace(os.sep, "/")] = (w, h)
        base = dst.with_suffix("")
        for tw in IMG_WIDTHS:
            if tw >= w and tw != IMG_WIDTHS[0]:
                # não amplia: gera só até a largura original
                pass
            tw_eff = min(tw, w)
            r = im.resize((tw_eff, round(h * tw_eff / w)), Image.LANCZOS) if tw_eff != w else im
            r.save(f"{base}-{tw}.webp", "WEBP", quality=80, method=4)
        fb = im if w <= 1600 else im.resize((1600, round(h * 1600 / w)), Image.LANCZOS)
        fb.save(dst.with_suffix(".jpg"), "JPEG", quality=82, optimize=True, progressive=True)


def picture(rel, alt="", cls="", sizes="(max-width: 700px) 100vw, 50vw", loading="lazy", fetchpriority=None):
    """Gera <picture> com srcset webp. rel é relativo a img/ (ex.: coffee/coffee-green.jpg)."""
    if not rel:
        return ""
    rel = rel.replace("\\", "/")
    base = "/img/" + re.sub(r"\.(jpe?g|png)$", "", rel, flags=re.I)
    dims = IMG_CACHE.get(rel)
    wh = f' width="{dims[0]}" height="{dims[1]}"' if dims else ""
    srcset = ", ".join(f"{base}-{w}.webp {w}w" for w in IMG_WIDTHS)
    fp = f' fetchpriority="{fetchpriority}"' if fetchpriority else ""
    return (
        f'<picture class="{cls}"><source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
        f'<img src="{base}.jpg" alt="{html.escape(alt)}" loading="{loading}" decoding="async"{wh}{fp}></picture>'
    )


def screen_svg(cls="screen"):
    """A peneira de classificação — elemento gráfico da marca (grade de furos)."""
    cols, rows, r, gap = 14, 10, 7, 23
    w = cols * gap + 26
    h = rows * gap + 26
    out = [
        f'<svg viewBox="0 0 {w} {h}" class="{cls}" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{w}" height="{h}" rx="12" fill="var(--navy)"/>',
    ]
    for i in range(cols):
        for j in range(rows):
            out.append(f'<circle cx="{24 + i * gap}" cy="{24 + j * gap}" r="{r}" fill="var(--paper)"/>')
    # três grãos (elipses) presos na peneira
    for cx, cy, rot in (
        (24 + 4 * gap, 24 + 3 * gap, -28),
        (24 + 9 * gap, 24 + 6 * gap, 15),
        (24 + 6 * gap, 24 + 8 * gap, -60),
    ):
        out.append(
            f'<g transform="translate({cx} {cy}) rotate({rot})"><ellipse rx="9.5" ry="6.5" fill="var(--bean)"/>'
            f'<path d="M-6.5 0 Q0 2.8 6.5 0" fill="none" stroke="var(--bean-line)" stroke-width="1.4" stroke-linecap="round"/></g>'
        )
    out.append("</svg>")
    return "".join(out)


def placeholder_svg(label):
    """Painel de marca para produto ainda sem foto própria."""
    cols, rows, gap = 9, 6, 26
    w, h = 480, 320
    out = [
        f'<svg viewBox="0 0 {w} {h}" class="ph" role="img" aria-label="{html.escape(label)}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{w}" height="{h}" fill="#F4F4F4"/>',
    ]
    for i in range(cols):
        for j in range(rows):
            out.append(f'<circle cx="{40 + i * gap}" cy="{40 + j * gap}" r="6" fill="#E7E9DC"/>')
    out.append(
        '<g transform="translate(380 230) rotate(-28)"><ellipse rx="46" ry="30" fill="#A9AF88"/><path d="M-30 0 Q0 12 30 0" fill="none" stroke="#7E855F" stroke-width="5" stroke-linecap="round"/></g>'
    )
    out.append(
        f'<text x="40" y="{h - 36}" font-family="Outfit, sans-serif" font-size="22" font-weight="600" fill="#26375E">{html.escape(label)}</text>'
    )
    out.append("</svg>")
    return "".join(out)


# ----------------------------------------------------------------------------- JSON-LD


def org_jsonld():
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": DOMAIN + "/#org",
        "name": "GBC Foods",
        "alternateName": "GBC Group",
        "url": DOMAIN + "/",
        "logo": DOMAIN + "/img/brand/logo-color.png",
        "email": CFG["email_comercial"],
        "telephone": CFG["telefone_link"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": CFG["endereco"]["cidade"],
            "addressRegion": CFG["endereco"]["estado"],
            "addressCountry": "BR",
        },
        "contactPoint": [
            {
                "@type": "ContactPoint",
                "contactType": "sales",
                "email": CFG["email_comercial"],
                "telephone": CFG["telefone_link"],
                "availableLanguage": ["en", "pt", "es"],
            }
        ],
    }


def breadcrumb_jsonld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(items)
        ],
    }


# ----------------------------------------------------------------------------- render

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["tojson_ld"] = lambda o: json.dumps(o, ensure_ascii=False)
env.globals.update(picture=picture, screen_svg=screen_svg, placeholder_svg=placeholder_svg)

WRITTEN = []


def write(path, content):
    p = DIST / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    WRITTEN.append(path)


SITEMAP = []  # (loc, alternates dict, lastmod, priority)


def render(
    template,
    path,
    lang,
    *,
    title,
    description,
    alternates,
    breadcrumbs=None,
    jsonld=None,
    og_image=None,
    priority="0.7",
    lastmod=None,
    noindex=False,
    **ctx,
):
    tpl = env.get_template(template)
    canonical = DOMAIN + path
    ld = [org_jsonld()]
    if breadcrumbs:
        ld.append(breadcrumb_jsonld(breadcrumbs))
    if jsonld:
        ld.extend(jsonld if isinstance(jsonld, list) else [jsonld])
    base_ctx = {
        "lang": lang,
        "langs": LANGS,
        "path": path,
        "canonical": canonical,
        "domain": DOMAIN,
        "cfg": CFG,
        "title": title,
        "description": description,
        "alternates": alternates,
        "breadcrumbs": breadcrumbs or [],
        "jsonld": ld,
        "og_image": DOMAIN + (og_image or "/og-image.png"),
        "noindex": noindex,
        "ui": lambda k: t(k, lang),
        "L": lambda o: L(o, lang),
        "url": lambda p, l=None: url(p, l or lang),
        "product_url": lambda pr, l=None: product_url(pr, l or lang),
        "post_url": lambda pid, l=None: post_url(pid, l or lang),
        "lang_names": {l: UI["lang_name"][l] for l in LANGS},
        "products": PRODUCTS,
        "posts": POSTS[lang],
        "steps": STEPS[lang],
        # A terceira família só aparece no menu depois que houver produtos nela.
        "has_packaged": any(p["category"] == "embalados" for p in PRODUCTS),
        "wa": WA,
        "wa_ok": WA_OK,
        "precisa_consentimento": GA_OK or SENTRY_OK,
        "ga": GA if GA_OK else "",
        "sentry_dsn": SENTRY_DSN if SENTRY_OK else "",
        "sentry_rate": SENTRY_RATE,
        "release": RELEASE,
        "lead_endpoint": CFG.get("lead_endpoint", ""),
        "year": datetime.date.today().year,
    }
    base_ctx.update(ctx)
    write(path, tpl.render(**base_ctx))
    if not noindex:
        SITEMAP.append((canonical, {l: DOMAIN + u for l, u in alternates.items()}, lastmod, priority))


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    # estáticos
    for name in ("favicon.svg", "apple-touch-icon.png", "favicon-512.png", "og-image.png"):
        shutil.copy2(STATIC / name, DIST / name)
    (DIST / "css").mkdir()
    # folha base + motion (static/motion.css) num único arquivo: uma requisição a menos
    css = (STATIC / "site.css").read_text(encoding="utf-8") + "\n" + (STATIC / "motion.css").read_text(encoding="utf-8")
    (DIST / "css" / "site.css").write_text(css, encoding="utf-8")
    shutil.copytree(STATIC / "js", DIST / "js")  # módulos ES: site.js importa os demais
    process_images()

    for lang in LANGS:
        H = PAGES["home"][lang]
        C = PAGES["company"][lang]
        S = PAGES["services"][lang]
        F = PAGES["foods"][lang]
        G = PAGES["logistics"][lang]
        P = PAGES["products"][lang]
        Q = PAGES["quote_contact_blog"][lang]

        def alt(page):
            return {l: url(page, l) for l in LANGS}

        crumb_home = (t("nav.home", lang), url("home", lang))

        # Home
        render(
            "home.html",
            url("home", lang),
            lang,
            title=H["meta_title"],
            description=H["meta_description"],
            alternates=alt("home"),
            page=H,
            priority="1.0",
            jsonld={
                "@context": "https://schema.org",
                "@type": "WebSite",
                "url": DOMAIN + "/",
                "name": "GBC Foods",
                "inLanguage": lang,
                "publisher": {"@id": DOMAIN + "/#org"},
            },
            featured=[p for p in PRODUCTS if p.get("featured")][:6],
            latest=POSTS[lang][:3],
        )

        # Empresa
        render(
            "company.html",
            url("company", lang),
            lang,
            title=C["meta_title"],
            description=C["meta_description"],
            alternates=alt("company"),
            page=C,
            breadcrumbs=[crumb_home, (t("nav.company", lang), url("company", lang))],
            priority="0.8",
            og_image="/img/products/port-santos.jpg",
        )

        # Serviços
        render(
            "services.html",
            url("services", lang),
            lang,
            title=S["meta_title"],
            description=S["meta_description"],
            alternates=alt("services"),
            page=S,
            breadcrumbs=[crumb_home, (t("nav.services", lang), url("services", lang))],
            priority="0.8",
        )
        render(
            "foods.html",
            url("foods", lang),
            lang,
            title=F["meta_title"],
            description=F["meta_description"],
            alternates=alt("foods"),
            page=F,
            priority="0.9",
            breadcrumbs=[
                crumb_home,
                (t("nav.services", lang), url("services", lang)),
                (t("nav.foods", lang), url("foods", lang)),
            ],
        )
        render(
            "logistics.html",
            url("logistics", lang),
            lang,
            title=G["meta_title"],
            description=G["meta_description"],
            alternates=alt("logistics"),
            page=G,
            priority="0.9",
            og_image="/img/products/ship-sea.jpg",
            breadcrumbs=[
                crumb_home,
                (t("nav.services", lang), url("services", lang)),
                (t("nav.logistics", lang), url("logistics", lang)),
            ],
        )

        # Produtos
        bulk = [p for p in PRODUCTS if p["category"] == "granel"]
        powders = [p for p in PRODUCTS if p["category"] == "po"]
        packaged = [p for p in PRODUCTS if p["category"] == "embalados"]
        crumb_prod = (t("nav.products", lang), url("products", lang))
        # O texto de abertura fala em duas ou em três famílias conforme a
        # categoria "embalados" tenha produtos cadastrados.
        index_lead = P["index_lead_3"] if packaged else P["index_lead"]
        render(
            "products_index.html",
            url("products", lang),
            lang,
            title=P["index_meta_title"],
            description=P["index_meta_description"],
            alternates=alt("products"),
            page=P,
            bulk=bulk,
            powders=powders,
            packaged=packaged,
            index_lead=index_lead,
            priority="0.9",
            breadcrumbs=[crumb_home, crumb_prod],
        )
        render(
            "products_category.html",
            url("bulk", lang),
            lang,
            title=P["bulk_meta_title"],
            description=P["bulk_meta_description"],
            alternates=alt("bulk"),
            page=P,
            items=bulk,
            cat_title=P["bulk_title"],
            cat_lead=P["bulk_lead"],
            priority="0.9",
            breadcrumbs=[crumb_home, crumb_prod, (t("nav.bulk", lang), url("bulk", lang))],
        )
        render(
            "products_category.html",
            url("powders", lang),
            lang,
            title=P["powders_meta_title"],
            description=P["powders_meta_description"],
            alternates=alt("powders"),
            page=P,
            items=powders,
            cat_title=P["powders_title"],
            cat_lead=P["powders_lead"],
            priority="0.9",
            breadcrumbs=[crumb_home, crumb_prod, (t("nav.powders", lang), url("powders", lang))],
        )
        if packaged:
            render(
                "products_category.html",
                url("packaged", lang),
                lang,
                title=P["packaged_meta_title"],
                description=P["packaged_meta_description"],
                alternates=alt("packaged"),
                page=P,
                items=packaged,
                cat_title=P["packaged_title"],
                cat_lead=P["packaged_lead"],
                priority="0.9",
                breadcrumbs=[crumb_home, crumb_prod, (t("nav.packaged", lang), url("packaged", lang))],
            )
        for prod in PRODUCTS:
            cat_key = {"granel": "bulk", "po": "powders", "embalados": "packaged"}[prod["category"]]
            name = prod["name"][lang]
            pu = product_url(prod, lang)
            ld = {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": name,
                "description": prod["short"][lang],
                "brand": {"@type": "Brand", "name": "GBC Foods"},
                "manufacturer": {"@id": DOMAIN + "/#org"},
                "url": DOMAIN + pu,
                "category": t("nav." + cat_key, lang),
                "countryOfOrigin": L(prod.get("origin", ""), lang),
                "additionalProperty": [
                    {"@type": "PropertyValue", "name": s["k"][lang], "value": s["v"][lang]}
                    for s in prod.get("specs", [])
                ],
                "offers": {
                    "@type": "Offer",
                    "availability": "https://schema.org/InStock",
                    "priceCurrency": "USD",
                    "businessFunction": "http://purl.org/goodrelations/v1#Sell",
                    "seller": {"@id": DOMAIN + "/#org"},
                    "url": DOMAIN + url("quote", lang) + "?produto=" + prod["id"],
                    "priceSpecification": {
                        "@type": "PriceSpecification",
                        "priceCurrency": "USD",
                        "valueAddedTaxIncluded": False,
                    },
                },
            }
            if prod.get("image"):
                ld["image"] = DOMAIN + "/img/" + re.sub(r"\.(jpe?g|png)$", ".jpg", prod["image"])
            if prod.get("hs"):
                ld["additionalProperty"].append({"@type": "PropertyValue", "name": "HS", "value": prod["hs"]})
            others = [p for p in PRODUCTS if p["id"] != prod["id"] and p["category"] == prod["category"]][:3]
            if len(others) < 3:
                others += [p for p in PRODUCTS if p["id"] != prod["id"] and p not in others][: 3 - len(others)]
            render(
                "product.html",
                pu,
                lang,
                title=f"{name} — GBC Foods",
                description=prod["short"][lang],
                alternates={l: product_url(prod, l) for l in LANGS},
                page=P,
                product=prod,
                cat_key=cat_key,
                others=others,
                jsonld=ld,
                priority="0.8",
                og_image=("/img/" + re.sub(r"\.(jpe?g|png)$", ".jpg", prod["image"])) if prod.get("image") else None,
                breadcrumbs=[crumb_home, crumb_prod, (t("nav." + cat_key, lang), url(cat_key, lang)), (name, pu)],
            )

        # Blog
        render(
            "blog_index.html",
            url("blog", lang),
            lang,
            title=Q["blog_meta_title"],
            description=Q["blog_meta_description"],
            alternates=alt("blog"),
            page=Q,
            priority="0.7",
            breadcrumbs=[crumb_home, (t("nav.blog", lang), url("blog", lang))],
        )
        for post in POSTS[lang]:
            pu = post_url(post["id"], lang)
            alts = {l: post_url(post["id"], l) for l in LANGS if post_url(post["id"], l)}
            ld = {
                "@context": "https://schema.org",
                "@type": "BlogPosting",
                "headline": post["title"],
                "description": post.get("description", ""),
                "datePublished": post["date"],
                "dateModified": post["date"],
                "inLanguage": lang,
                "author": {"@type": "Organization", "name": "GBC Foods", "@id": DOMAIN + "/#org"},
                "publisher": {"@id": DOMAIN + "/#org"},
                "mainEntityOfPage": DOMAIN + pu,
                "url": DOMAIN + pu,
            }
            if post.get("image"):
                ld["image"] = DOMAIN + "/img/" + re.sub(r"\.(jpe?g|png)$", ".jpg", post["image"])
            related = [p for p in POSTS[lang] if p["id"] != post["id"]][:2]
            render(
                "post.html",
                pu,
                lang,
                title=f"{post['title']} — GBC Foods",
                description=post.get("description", ""),
                alternates=alts,
                post=post,
                related=related,
                jsonld=ld,
                priority="0.6",
                lastmod=post["date"],
                og_image=("/img/" + re.sub(r"\.(jpe?g|png)$", ".jpg", post["image"])) if post.get("image") else None,
                breadcrumbs=[crumb_home, (t("nav.blog", lang), url("blog", lang)), (post["title"], pu)],
            )

        # Cotação e contato
        render(
            "quote.html",
            url("quote", lang),
            lang,
            title=Q["quote_meta_title"],
            description=Q["quote_meta_description"],
            alternates=alt("quote"),
            page=Q,
            priority="0.9",
            breadcrumbs=[crumb_home, (t("nav.quote", lang), url("quote", lang))],
        )
        render(
            "contact.html",
            url("contact", lang),
            lang,
            title=Q["contact_meta_title"],
            description=Q["contact_meta_description"],
            alternates=alt("contact"),
            page=Q,
            priority="0.8",
            breadcrumbs=[crumb_home, (t("nav.contact", lang), url("contact", lang))],
        )

        # Legal
        for kind, route in (("privacy", "privacy"), ("cookies", "cookies")):
            meta = LEGAL[kind][lang]["meta"]
            body = LEGAL[kind][lang]["body"]
            body = body.replace("{cookies_url}", url("cookies", lang)).replace("{privacy_url}", url("privacy", lang))
            render(
                "legal.html",
                url(route, lang),
                lang,
                title=f"{meta['title']} — GBC Foods",
                description=meta.get("description", ""),
                alternates=alt(route),
                doc_title=meta["title"],
                updated=fmt_date(str(meta.get("updated", "2026-01-01")), lang),
                body_html=md_to_html(body),
                priority="0.3",
                breadcrumbs=[crumb_home, (meta["title"], url(route, lang))],
            )

    # Raiz: detecção de idioma. 404. Arquivos de servidor.
    write(
        "/",
        env.get_template("root.html").render(
            langs=LANGS,
            lang_names=UI["lang_name"],
            default=CFG["idioma_padrao"],
            domain=DOMAIN,
            ui=UI,
            url=url,
            year=datetime.date.today().year,
        ),
    )
    write(
        "/404.html",
        env.get_template("404.html").render(langs=LANGS, lang_names=UI["lang_name"], ui=UI, url=url, domain=DOMAIN),
    )
    write_sitemap()
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")
    print(f"ok — {len(WRITTEN)} páginas em dist/")
    if not WA_OK:
        print(
            "AVISO: whatsapp_numero em content/config.json ainda está com o valor de exemplo. O botão de cotação abrirá o WhatsApp com esse número."
        )
    if not GA_OK:
        print("AVISO: ga4_measurement_id não configurado — o Google Analytics não foi incluído.")
    if not SENTRY_OK:
        print("info: sentry_dsn vazio — monitoramento de erros (Sentry) não incluído. Release:", RELEASE or "(sem git)")
    if not (GA_OK or SENTRY_OK):
        print(
            "info: nenhum rastreamento ativo — o banner de cookies não foi gerado. "
            "Ele volta sozinho assim que ga4_measurement_id ou sentry_dsn for preenchido."
        )


def write_sitemap():
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    today = datetime.date.today().isoformat()
    for loc, alts, lastmod, prio in SITEMAP:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        for l, u in alts.items():
            lines.append(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{u}"/>')
        if len(alts) == len(LANGS):
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{DOMAIN}/"/>')
        lines.append(f"    <lastmod>{lastmod or today}</lastmod>")
        lines.append(f"    <priority>{prio}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


HEADERS = """/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Cache-Control: public, max-age=0, must-revalidate
/img/*
  Cache-Control: public, max-age=2592000, immutable
/css/*
  Cache-Control: public, max-age=604800
/js/*
  Cache-Control: public, max-age=604800
/og-image.png
  Cache-Control: public, max-age=604800
"""


def check_content():
    """Confere se todo texto existe nos quatro idiomas. Uso: python3 build.py --check"""
    problems = []

    def walk(obj, path):
        if isinstance(obj, dict):
            keys = set(obj.keys())
            if keys & set(LANGS):
                missing = [l for l in LANGS if l not in obj or obj[l] in ("", None, [])]
                if missing:
                    problems.append(f"{path}: falta {', '.join(missing)}")
            else:
                for k, v in obj.items():
                    if not k.startswith("_"):
                        walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(UI, "ui.json")
    for k, v in ROUTES.items():
        if not k.startswith("_"):
            miss = [l for l in LANGS if l not in v]
            if miss:
                problems.append(f"routes.json.{k}: falta {', '.join(miss)}")
    for name, page in PAGES.items():
        for l in LANGS:
            if l not in page:
                problems.append(f"pages/{name}.json: falta o bloco '{l}'")
        blocks = [page[l] for l in LANGS if l in page]
        if blocks:
            keys0 = set(blocks[0].keys())
            for l, b in zip([l for l in LANGS if l in page], blocks, strict=True):
                diff = keys0 ^ set(b.keys())
                if diff:
                    problems.append(f"pages/{name}.json [{l}]: chaves diferentes: {', '.join(sorted(diff))}")
    for prod in PRODUCTS:
        walk(
            {
                k: v
                for k, v in prod.items()
                if k not in ("id", "category", "order", "featured", "image", "gallery", "hs")
            },
            f"products/{prod['id']}",
        )
        if prod["image"] and not (STATIC / "img" / prod["image"]).exists():
            problems.append(f"products/{prod['id']}: imagem não encontrada: static/img/{prod['image']}")
    for folder in sorted((CONTENT / "blog").iterdir()):
        if folder.is_dir():
            for l in LANGS:
                if not (folder / f"{l}.md").exists():
                    problems.append(f"blog/{folder.name}: falta {l}.md")
    for kind in ("privacy", "cookies"):
        for l in LANGS:
            if not (CONTENT / "legal" / kind / f"{l}.md").exists():
                problems.append(f"legal/{kind}: falta {l}.md")
    if problems:
        print("Conteúdo incompleto:")
        for p in problems:
            print("  -", p)
    else:
        print("ok — conteúdo completo nos", len(LANGS), "idiomas")
    return problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(1 if check_content() else 0)
    check_content()
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("Servindo em http://localhost:8080  (Ctrl+C para parar)")
        http.server.ThreadingHTTPServer(("", 8080), handler).serve_forever()
