"""
Nivel 2 del SEO: genera una página HTML de verdad por cada review y
cada noticia (con el contenido ya adentro, no traído después con
JavaScript), rellena las listas de reviews.html/noticias.html/index.html
con el mismo contenido ya armado (para que un buscador lo vea sin
ejecutar nada), y arma el feed RSS.

Se corre después de build_content_index.py, disparado por el mismo
GitHub Action. No hace falta correrlo a mano.
"""
import html
import json
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote

import markdown as md

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://www.escabiandopociones.com.ar"
OG_IMAGE = f"{SITE_URL}/assets/banner-podcast.png"

YOUTUBE_RE = re.compile(
    r'<p>\s*<a[^>]*href="https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)'
    r'([a-zA-Z0-9_-]{11})[^"]*"[^>]*>[^<]*</a>\s*</p>'
)
TWEET_RE = re.compile(
    r'<p>\s*<a[^>]*href="(https?://(?:www\.)?(?:twitter\.com|x\.com)/[A-Za-z0-9_]+/status/\d+)'
    r'[^"]*"[^>]*>[^<]*</a>\s*</p>'
)
LINK_RE = re.compile(r'<a (?![^>]*target=)')
BARE_URL_RE = re.compile(r'(?<![(<\[])\bhttps?://[^\s<>()\[\]]+')


def autolink_bare_urls(text):
    """Python-Markdown, a diferencia de marked.js (el que usa el sitio
    en el navegador), no convierte automáticamente un link 'pelado' en
    un link de verdad — hay que envolverlo en <> para que lo entienda.
    Sin esto, el truco de 'pegá el link de YouTube solo en su línea'
    no funcionaría nunca del lado del servidor."""
    def wrap(m):
        url = m.group(0)
        trail = ''
        while url and url[-1] in '.,;:!?':
            trail = url[-1] + trail
            url = url[:-1]
        return f'<{url}>{trail}'
    return BARE_URL_RE.sub(wrap, text)


def render_body(body_md, asset_prefix=""):
    """Convierte el markdown guardado a HTML, con los mismos criterios
    que ya usa el sitio en vivo: YouTube y X se incrustan solos si van
    en su propia línea, y todos los links abren en pestaña nueva."""
    body_md = (body_md or "").replace("](/assets/", "](assets/")
    if asset_prefix:
        body_md = re.sub(
            r"!\[([^\]]*)\]\((?!https?://)assets/",
            rf"![\1]({asset_prefix}assets/",
            body_md,
        )
    html_body = md.markdown(autolink_bare_urls(body_md))
    html_body = YOUTUBE_RE.sub(
        lambda m: (
            f'<div class="embed-wrap" style="margin:20px 0;">'
            f'<iframe width="100%" height="400" src="https://www.youtube.com/embed/{m.group(1)}" '
            f'title="Video de YouTube" frameborder="0" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            f'allowfullscreen loading="lazy"></iframe></div>'
        ),
        html_body,
    )
    html_body = TWEET_RE.sub(
        lambda m: f'<blockquote class="twitter-tweet"><a href="{m.group(1)}"></a></blockquote>',
        html_body,
    )
    html_body = LINK_RE.sub('<a target="_blank" rel="noopener" ', html_body)
    return html_body


MESES_ES = {
    "January": "enero", "February": "febrero", "March": "marzo", "April": "abril",
    "May": "mayo", "June": "junio", "July": "julio", "August": "agosto",
    "September": "septiembre", "October": "octubre", "November": "noviembre", "December": "diciembre",
}


def fmt_date_es(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%-d de %B de %Y")
    except Exception:
        return iso or ""
    for en, es in MESES_ES.items():
        d = d.replace(en, es)
    return d


def esc(s):
    return html.escape(s or "", quote=True)


def estimate_reading_minutes(body_md):
    """Cálculo simple: cuenta palabras del markdown crudo (sin renderizar)
    y asume ~200 palabras por minuto, que es un promedio razonable de
    lectura en español. No pretende ser exacto, solo dar una referencia."""
    words = len(re.findall(r"\w+", body_md or ""))
    return max(1, round(words / 200))


def fmt_pct(score):
    pct = max(0, min(100, (score or 0) * 10))
    return int(pct) if float(pct).is_integer() else pct


def tag_slugify(s):
    """Mismo algoritmo que el slugify() del panel (admin/index.html),
    para que un tag armado en el panel y su página generada acá
    apunten siempre a la misma URL."""
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def effective_tags(kind, item):
    """Los tags 'de verdad' de una nota: para una review, el campo
    Juego cuenta como tag número uno aunque el campo 'tags' esté
    vacío; para una noticia, son los que se cargaron en el panel.
    Deduplica sin importar mayúsculas/acentos, conservando la primera
    forma en la que apareció escrito cada uno."""
    tags = list(item.get("tags") or [])
    if kind == "review" and item.get("game"):
        tags = [item["game"]] + tags
    seen = set()
    result = []
    for t in tags:
        t = (t or "").strip()
        if not t:
            continue
        key = tag_slugify(t)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(t)
    return result


def build_tag_index(reviews, noticias):
    """slug de tag -> {'label': nombre a mostrar, 'items': [(kind, item), ...]}"""
    index = {}
    for kind, items in (("review", reviews), ("noticia", noticias)):
        for item in items:
            for tag in effective_tags(kind, item):
                slug = tag_slugify(tag)
                entry = index.setdefault(slug, {"label": tag, "items": []})
                entry["items"].append((kind, item))
    for entry in index.values():
        entry["items"].sort(key=lambda x: x[1].get("date", ""), reverse=True)
    return index


def find_related(kind, item, tag_index, limit=3):
    """Otras notas que comparten al menos un tag con esta, ordenadas
    primero por cuántos tags comparten y después por fecha (más
    nuevas primero). No se pisa a sí misma."""
    my_tags = {tag_slugify(t) for t in effective_tags(kind, item)}
    if not my_tags:
        return []
    scored = {}
    for slug in my_tags:
        for k, it in tag_index.get(slug, {}).get("items", []):
            if k == kind and it.get("slug") == item.get("slug"):
                continue
            key = (k, it.get("slug"))
            if key not in scored:
                scored[key] = [0, k, it]
            scored[key][0] += 1
    ranked = sorted(scored.values(), key=lambda x: (x[0], x[2].get("date", "")), reverse=True)
    return [(k, it) for _, k, it in ranked[:limit]]


PAGE_SHELL = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Escabiando Pociones</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="Escabiando Pociones" href="{site}/rss.xml">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Escabiando Pociones">
<meta property="og:locale" content="es_AR">
<meta property="og:title" content="{title} | Escabiando Pociones">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{image}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} | Escabiando Pociones">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{image}">
<script type="application/ld+json">{schema}</script>
<link rel="icon" href="../assets/logo-full.png">
<link rel="stylesheet" href="../style.css">
<script data-goatcounter="https://escabiandopociones.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="../index.html" class="nav-brand">
      <img src="../assets/logo-full.png" alt="Escabiando Pociones">
      ESCABIANDO POCIONES
    </a>
    <button class="nav-toggle" aria-label="Abrir menú" aria-expanded="false">☰</button>
    <ul class="nav-links">
      <li><a href="../index.html">Inicio</a></li>
      <li><a href="../episodios.html">Episodios</a></li>
      <li><a href="../noticias.html">Noticias</a></li>
      <li><a href="../reviews.html">Reviews</a></li>
      <li><a href="../sobre.html">Sobre nosotros</a></li>
      <li><a href="../prensa.html">Prensa</a></li>
      <li><a href="../search.html">Buscar</a></li>
    </ul>
  </div>
</nav>

<header class="page-header">
  <div class="container">
    <a href="{back_href}" class="eyebrow" style="display:inline-block; margin-bottom:18px;">← Volver a {back_label}</a>
    {header_extra}
    <h1>{title_esc}</h1>
    <p style="font-family: var(--f-mono); font-size:0.85rem; color: var(--ink-dim);">
      {byline}
    </p>
    {tags_html}
  </div>
</header>

<section class="section" data-pagefind-body>
  <div class="container" id="{body_id}" style="max-width: 760px;">
    {body}
  </div>
</section>

<footer class="footer">
  <div class="container footer-inner">
    <div class="footer-brand">
      <small>© 2026 Escabiando Pociones</small>
      <div class="social-icons">
        <a href="https://www.instagram.com/escabiandopociones?igsi=MWNld2g0ZjA0cXg2bA==" target="_blank" rel="noopener" aria-label="Instagram">
          <svg viewBox="0 0 24 24"><path d="M12 2c2.717 0 3.056.01 4.122.06 1.065.05 1.79.217 2.428.465.66.256 1.216.598 1.772 1.153a4.908 4.908 0 0 1 1.153 1.772c.247.637.415 1.363.465 2.428.05 1.066.06 1.405.06 4.122 0 2.717-.01 3.056-.06 4.122-.05 1.065-.218 1.79-.465 2.428a4.883 4.883 0 0 1-1.153 1.772 4.915 4.915 0 0 1-1.772 1.153c-.637.247-1.363.415-2.428.465-1.066.05-1.405.06-4.122.06-2.717 0-3.056-.01-4.122-.06-1.065-.05-1.79-.218-2.428-.465a4.89 4.89 0 0 1-1.772-1.153 4.904 4.904 0 0 1-1.153-1.772c-.248-.637-.415-1.363-.465-2.428C2.013 15.056 2 14.717 2 12c0-2.717.01-3.056.06-4.122.05-1.066.217-1.79.465-2.428a4.88 4.88 0 0 1 1.153-1.772A4.897 4.897 0 0 1 5.45 2.525c.637-.248 1.363-.415 2.428-.465C8.944 2.013 9.283 2 12 2zm0 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.25a3.25 3.25 0 1 1 0-6.5 3.25 3.25 0 0 1 0 6.5zM17.4 5.15a1.17 1.17 0 1 0 0 2.34 1.17 1.17 0 0 0 0-2.34z"/></svg>
        </a>
        <a href="https://www.facebook.com/share/1GMazu41dF/" target="_blank" rel="noopener" aria-label="Facebook">
          <svg viewBox="0 0 24 24"><path d="M13.5 21v-7.6h2.55l.38-2.96h-2.93V8.53c0-.86.24-1.44 1.47-1.44h1.57V4.46A21 21 0 0 0 14.2 4.3c-2.24 0-3.77 1.37-3.77 3.88v2.16H7.87v2.96h2.56V21h3.07z"/></svg>
        </a>
        <a href="https://www.tiktok.com/@escabiandopociones" target="_blank" rel="noopener" aria-label="TikTok">
          <svg viewBox="0 0 24 24"><path d="M16.6 2h-3.1v13.3c0 1.5-1.2 2.7-2.7 2.7a2.7 2.7 0 0 1-2.7-2.7 2.7 2.7 0 0 1 2.7-2.7c.3 0 .6.05.87.13V9.6a5.9 5.9 0 0 0-.87-.07A5.9 5.9 0 0 0 4.9 15.4a5.9 5.9 0 0 0 5.9 5.9 5.9 5.9 0 0 0 5.9-5.9V8.35a7.6 7.6 0 0 0 4.4 1.4V6.65a4.5 4.5 0 0 1-4.5-4.5V2z"/></svg>
        </a>
      </div>
    </div>
    <div class="social-links">
      <a href="https://open.spotify.com/show/587CqZd5K8oaRWqiVCQWSP" target="_blank" rel="noopener">Spotify</a>
      <a href="https://www.youtube.com/@EscabiandoPociones/videos" target="_blank" rel="noopener">YouTube</a>
      <a href="../prensa.html">Prensa</a>
    </div>
  </div>
</footer>

<script src="../script.js"></script>
<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</body>
</html>
"""


def build_schema(kind, item, url):
    schema = {
        "@context": "https://schema.org",
        "@type": "ReviewNewsArticle" if kind == "review" else "NewsArticle",
        "headline": item.get("title", ""),
        "description": item.get("excerpt", ""),
        "datePublished": item.get("date", ""),
        "dateModified": item.get("date", ""),
        "author": {"@type": "Person", "name": item.get("author") or "Escabiando Pociones"},
        "publisher": {
            "@type": "Organization",
            "name": "Escabiando Pociones",
            "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/assets/logo-full.png"},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    if item.get("cover"):
        schema["image"] = [f"{SITE_URL}/{item['cover'].lstrip('/')}"]
    if kind == "review" and item.get("score") is not None:
        schema["reviewRating"] = {
            "@type": "Rating", "ratingValue": item["score"], "bestRating": 10, "worstRating": 0,
        }
        video_game = {"@type": "VideoGame", "name": item.get("game") or item.get("title")}
        if item.get("cover"):
            video_game["image"] = f"{SITE_URL}/{item['cover'].lstrip('/')}"
        schema["itemReviewed"] = video_game
    return json.dumps(schema, ensure_ascii=False)


def build_share_buttons(title, url):
    """Botones de compartir: son solo links armados a mano (wa.me para
    WhatsApp, el intent de tweet para X, y un botón que copia el link
    con JS). No necesitan ninguna cuenta conectada ni API de terceros."""
    wa_text = quote(f"{title} {url}")
    tw_text = quote(title)
    tw_url = quote(url)
    return f'''<div class="btn-row" style="margin-top:40px; padding-top:24px; border-top:1px solid var(--line);">
      <span class="eyebrow" style="margin:0 4px 0 0; align-self:center;">Compartir</span>
      <a class="btn btn-ghost" href="https://wa.me/?text={wa_text}" target="_blank" rel="noopener" aria-label="Compartir por WhatsApp">WhatsApp</a>
      <a class="btn btn-ghost" href="https://twitter.com/intent/tweet?text={tw_text}&url={tw_url}" target="_blank" rel="noopener" aria-label="Compartir en X">X</a>
      <button type="button" class="btn btn-ghost js-copy-link" data-url="{esc(url)}" aria-label="Copiar el link de esta nota">Copiar link</button>
    </div>'''


def build_tag_chips(kind, item, path_prefix="../"):
    tags = effective_tags(kind, item)
    if not tags:
        return ""
    chips = "".join(
        f'<a class="tag-chip" href="{path_prefix}tags/{tag_slugify(t)}.html">{esc(t)}</a>'
        for t in tags
    )
    return f'<div class="tag-list">{chips}</div>'


def build_related_section(kind, item, tag_index):
    related = find_related(kind, item, tag_index)
    if not related:
        return ""
    cards = "".join(render_card(k, it, path_prefix="../") for k, it in related)
    return f'''<div style="margin-top:48px; padding-top:32px; border-top:1px solid var(--line);">
      <span class="eyebrow-lg" style="display:block; margin-bottom:20px;">También te puede interesar</span>
      <div class="grid grid-3">{cards}</div>
    </div>'''


def render_article_page(kind, item, tag_index):
    slug = item["slug"]
    folder = "reviews" if kind == "review" else "noticias"
    url = f"{SITE_URL}/{folder}/{slug}.html"
    cover_url = f"{SITE_URL}/{item['cover'].lstrip('/')}" if item.get("cover") else OG_IMAGE
    description = (item.get("excerpt") or "").strip()[:160] or "Escabiando Pociones."

    cover_html = ""
    if item.get("cover"):
        cover_alt = esc(item.get("game") or item.get("title", ""))
        cover_html = f'<img src="../{item["cover"].lstrip("/")}" alt="{cover_alt}" style="width:100%; border-radius:6px; margin-bottom:20px;">'

    title_block_extra = ""
    if kind == "review":
        pct = fmt_pct(item.get("score"))
        score_txt = f"{item['score']} / 10" if item.get("score") is not None else ""
        header_extra = f'{cover_html}\n    <span class="eyebrow">{esc(item.get("game", ""))}</span>'
        title_block_extra = (
            f'<div class="vial-score" style="margin-bottom:8px;">'
            f'<div class="vial"><div class="vial-fill" style="height:{pct}%;"></div></div>'
            f'{score_txt}</div>'
        )
    else:
        header_extra = cover_html

    byline_parts = []
    if item.get("author"):
        byline_parts.append(esc(item["author"]))
    if item.get("date"):
        byline_parts.append(fmt_date_es(item["date"]))
    reading_minutes = estimate_reading_minutes(item.get("body", ""))
    byline_parts.append(f"{reading_minutes} min de lectura")
    byline = " · ".join(byline_parts)

    body_html = render_body(item.get("body", ""), asset_prefix="../")
    share_html = build_share_buttons(item.get("title", ""), url)
    related_html = build_related_section(kind, item, tag_index)
    body_full = title_block_extra + "\n    " + body_html + "\n    " + share_html + "\n    " + related_html

    html_out = PAGE_SHELL.format(
        title=esc(item.get("title", "")),
        description=esc(description),
        url=url,
        site=SITE_URL,
        image=cover_url,
        schema=build_schema(kind, item, url),
        back_href="../reviews.html" if kind == "review" else "../noticias.html",
        back_label="Reviews" if kind == "review" else "Noticias",
        header_extra=header_extra,
        title_esc=esc(item.get("title", "")),
        byline=byline,
        tags_html=build_tag_chips(kind, item),
        body_id="review-body" if kind == "review" else "news-body",
        body=body_full,
    )

    out_dir = ROOT / folder
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html_out)
    return out_path


def render_card(kind, item, path_prefix=""):
    """path_prefix: '' si la tarjeta se muestra en una página de la
    raíz (reviews.html, noticias.html, index.html), '../' si se
    muestra desde una página que vive una carpeta adentro (dentro de
    una nota, o en tags/<slug>.html)."""
    slug = item["slug"]
    folder = "reviews" if kind == "review" else "noticias"
    cover_src = f'{path_prefix}{item["cover"]}' if item.get("cover") else ""
    cover = (
        f'<img src="{cover_src}" alt="{esc(item.get("game") or item.get("title", ""))}" style="width:100%; border-radius:4px; margin-bottom:14px;">'
        if item.get("cover") else ""
    )
    href = f"{path_prefix}{folder}/{slug}.html"
    if kind == "review":
        pct = fmt_pct(item.get("score"))
        score_txt = f'{item["score"]} / 10' if item.get("score") is not None else ""
        return f'''<a class="card" href="{href}" style="display:block; margin-bottom:20px;">
      {cover}
      <span class="eyebrow">{esc(item.get("game", ""))}</span>
      <h3>{esc(item.get("title", ""))}</h3>
      <p>{esc(item.get("excerpt", ""))}</p>
      <div class="vial-score">
        <div class="vial"><div class="vial-fill" style="height:{pct}%;"></div></div>
        {score_txt}
      </div>
    </a>'''
    else:
        date_txt = fmt_date_es(item["date"]) if item.get("date") else ""
        return f'''<a class="card" href="{href}" style="display:block; margin-bottom:20px;">
      {cover}
      <span class="eyebrow">{date_txt}</span>
      <h3>{esc(item.get("title", ""))}</h3>
      <p>{esc(item.get("excerpt", ""))}</p>
    </a>'''


def nav_html(prefix):
    """prefix: '' para páginas en la raíz, '../' para páginas que
    viven una carpeta adentro (como tags/<slug>.html)."""
    return f'''<nav class="nav">
  <div class="nav-inner">
    <a href="{prefix}index.html" class="nav-brand">
      <img src="{prefix}assets/logo-full.png" alt="Escabiando Pociones">
      ESCABIANDO POCIONES
    </a>
    <button class="nav-toggle" aria-label="Abrir menú" aria-expanded="false">☰</button>
    <ul class="nav-links">
      <li><a href="{prefix}index.html">Inicio</a></li>
      <li><a href="{prefix}episodios.html">Episodios</a></li>
      <li><a href="{prefix}noticias.html">Noticias</a></li>
      <li><a href="{prefix}reviews.html">Reviews</a></li>
      <li><a href="{prefix}sobre.html">Sobre nosotros</a></li>
      <li><a href="{prefix}prensa.html">Prensa</a></li>
      <li><a href="{prefix}search.html">Buscar</a></li>
    </ul>
  </div>
</nav>'''


def footer_html(prefix):
    return f'''<footer class="footer">
  <div class="container footer-inner">
    <div class="footer-brand">
      <small>© 2026 Escabiando Pociones</small>
      <div class="social-icons">
        <a href="https://www.instagram.com/escabiandopociones?igsi=MWNld2g0ZjA0cXg2bA==" target="_blank" rel="noopener" aria-label="Instagram">
          <svg viewBox="0 0 24 24"><path d="M12 2c2.717 0 3.056.01 4.122.06 1.065.05 1.79.217 2.428.465.66.256 1.216.598 1.772 1.153a4.908 4.908 0 0 1 1.153 1.772c.247.637.415 1.363.465 2.428.05 1.066.06 1.405.06 4.122 0 2.717-.01 3.056-.06 4.122-.05 1.065-.218 1.79-.465 2.428a4.883 4.883 0 0 1-1.153 1.772 4.915 4.915 0 0 1-1.772 1.153c-.637.247-1.363.415-2.428.465-1.066.05-1.405.06-4.122.06-2.717 0-3.056-.01-4.122-.06-1.065-.05-1.79-.218-2.428-.465a4.89 4.89 0 0 1-1.772-1.153 4.904 4.904 0 0 1-1.153-1.772c-.248-.637-.415-1.363-.465-2.428C2.013 15.056 2 14.717 2 12c0-2.717.01-3.056.06-4.122.05-1.066.217-1.79.465-2.428a4.88 4.88 0 0 1 1.153-1.772A4.897 4.897 0 0 1 5.45 2.525c.637-.248 1.363-.415 2.428-.465C8.944 2.013 9.283 2 12 2zm0 5a5 5 0 1 0 0 10 5 5 0 0 0 0-10zm0 8.25a3.25 3.25 0 1 1 0-6.5 3.25 3.25 0 0 1 0 6.5zM17.4 5.15a1.17 1.17 0 1 0 0 2.34 1.17 1.17 0 0 0 0-2.34z"/></svg>
        </a>
        <a href="https://www.facebook.com/share/1GMazu41dF/" target="_blank" rel="noopener" aria-label="Facebook">
          <svg viewBox="0 0 24 24"><path d="M13.5 21v-7.6h2.55l.38-2.96h-2.93V8.53c0-.86.24-1.44 1.47-1.44h1.57V4.46A21 21 0 0 0 14.2 4.3c-2.24 0-3.77 1.37-3.77 3.88v2.16H7.87v2.96h2.56V21h3.07z"/></svg>
        </a>
        <a href="https://www.tiktok.com/@escabiandopociones" target="_blank" rel="noopener" aria-label="TikTok">
          <svg viewBox="0 0 24 24"><path d="M16.6 2h-3.1v13.3c0 1.5-1.2 2.7-2.7 2.7a2.7 2.7 0 0 1-2.7-2.7 2.7 2.7 0 0 1 2.7-2.7c.3 0 .6.05.87.13V9.6a5.9 5.9 0 0 0-.87-.07A5.9 5.9 0 0 0 4.9 15.4a5.9 5.9 0 0 0 5.9 5.9 5.9 5.9 0 0 0 5.9-5.9V8.35a7.6 7.6 0 0 0 4.4 1.4V6.65a4.5 4.5 0 0 1-4.5-4.5V2z"/></svg>
        </a>
      </div>
    </div>
    <div class="social-links">
      <a href="https://open.spotify.com/show/587CqZd5K8oaRWqiVCQWSP" target="_blank" rel="noopener">Spotify</a>
      <a href="https://www.youtube.com/@EscabiandoPociones/videos" target="_blank" rel="noopener">YouTube</a>
      <a href="{prefix}prensa.html">Prensa</a>
    </div>
  </div>
</footer>'''


def render_listing_page(*, title, description, url, back_href, back_label, subtitle, body, prefix):
    """Página genérica de listado (usada para cada tags/<slug>.html y
    para tags.html), con el mismo nav/header/footer que el resto del
    sitio pero sin todo lo específico de un artículo individual."""
    back_link = (
        f'<a href="{back_href}" class="eyebrow" style="display:inline-block; margin-bottom:18px;">← {back_label}</a>'
        if back_href else ""
    )
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} | Escabiando Pociones</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">
<link rel="alternate" type="application/rss+xml" title="Escabiando Pociones" href="{SITE_URL}/rss.xml">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Escabiando Pociones">
<meta property="og:locale" content="es_AR">
<meta property="og:title" content="{esc(title)} | Escabiando Pociones">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:url" content="{url}">
<link rel="icon" href="{prefix}assets/logo-full.png">
<link rel="stylesheet" href="{prefix}style.css">
<script data-goatcounter="https://escabiandopociones.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</head>
<body>

{nav_html(prefix)}

<header class="page-header">
  <div class="container">
    {back_link}
    <h1>{esc(title)}</h1>
    <p style="font-family: var(--f-mono); font-size:0.85rem; color: var(--ink-dim);">{esc(subtitle)}</p>
  </div>
</header>

<section class="section">
  <div class="container">
    {body}
  </div>
</section>

{footer_html(prefix)}

<script src="{prefix}script.js"></script>
</body>
</html>
'''


def render_tag_page(slug, label, items):
    url = f"{SITE_URL}/tags/{slug}.html"
    count = len(items)
    subtitle = f"{count} nota{'s' if count != 1 else ''} publicada{'s' if count != 1 else ''}"
    cards = "".join(render_card(k, it, path_prefix="../") for k, it in items)
    body = f'<div class="grid grid-3">{cards}</div>'
    html_out = render_listing_page(
        title=label,
        description=f"Todo lo publicado sobre {label} en Escabiando Pociones.",
        url=url,
        back_href="../tags.html",
        back_label="Volver a todos los tags",
        subtitle=subtitle,
        body=body,
        prefix="../",
    )
    out_dir = ROOT / "tags"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / f"{slug}.html", "w", encoding="utf-8") as fh:
        fh.write(html_out)


def render_tags_index(tag_index):
    entries = sorted(tag_index.items(), key=lambda kv: kv[1]["label"].lower())
    if entries:
        chips = "".join(
            f'<a class="tag-chip" href="tags/{slug}.html" style="font-size:0.9rem; padding:8px 16px;">'
            f'{esc(entry["label"])} <span style="opacity:0.6;">({len(entry["items"])})</span></a>'
            for slug, entry in entries
        )
        body = f'<div class="tag-list">{chips}</div>'
    else:
        body = '<div class="empty-vial"><p class="mt-0">Todavía no hay tags cargados.</p></div>'
    html_out = render_listing_page(
        title="Todos los tags",
        description="Todos los juegos y franquicias sobre los que se publicó en Escabiando Pociones.",
        url=f"{SITE_URL}/tags.html",
        back_href="index.html",
        back_label="Volver al inicio",
        subtitle=f"{len(entries)} tag{'s' if len(entries) != 1 else ''} en total",
        body=body,
        prefix="",
    )
    with open(ROOT / "tags.html", "w", encoding="utf-8") as fh:
        fh.write(html_out)


def clean_stale_tag_pages(valid_slugs):
    folder = ROOT / "tags"
    if not folder.exists():
        return
    for f in folder.glob("*.html"):
        if f.stem not in valid_slugs:
            f.unlink()
            print(f"Borrado (tag ya sin notas): {f}")


def fill_ssr_marker(file_path, marker_name, inner_html):
    path = ROOT / file_path
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(<!-- SSR:{marker_name}:start -->)(.*?)(<!-- SSR:{marker_name}:end -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        print(f"AVISO: no encontré el marcador SSR:{marker_name} en {file_path}")
        return
    new_text = pattern.sub(lambda m: f"{m.group(1)}\n{inner_html}\n{m.group(3)}", text)
    path.write_text(new_text, encoding="utf-8")


def build_rss(reviews, noticias):
    entries = [("review", r) for r in reviews] + [("noticia", n) for n in noticias]
    entries.sort(key=lambda x: x[1].get("date", ""), reverse=True)
    entries = entries[:30]

    items_xml = []
    for kind, item in entries:
        folder = "reviews" if kind == "review" else "noticias"
        url = f"{SITE_URL}/{folder}/{item['slug']}.html"
        try:
            pub_date = format_datetime(datetime.fromisoformat(item["date"].replace("Z", "+00:00")))
        except Exception:
            pub_date = format_datetime(datetime.now(timezone.utc))
        # Portada: si la nota no tiene una propia, usamos el banner del
        # podcast como respaldo, para que Instagram siempre tenga algo
        # con qué postear (no admite posteos sin imagen).
        cover_url = f"{SITE_URL}/{item['cover'].lstrip('/')}" if item.get("cover") else OG_IMAGE
        cover_ext = cover_url.rsplit(".", 1)[-1].lower()
        cover_mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(cover_ext, "image/jpeg")
        items_xml.append(f"""  <item>
    <title>{esc(item.get('title', ''))}</title>
    <link>{url}</link>
    <guid>{url}</guid>
    <pubDate>{pub_date}</pubDate>
    <category>{'Review' if kind == 'review' else 'Noticia'}</category>
    <description><![CDATA[{item.get('excerpt', '')}]]></description>
    <enclosure url="{cover_url}" type="{cover_mime}" length="0"/>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Escabiando Pociones</title>
  <link>{SITE_URL}/</link>
  <description>Portal de noticias de videojuegos y reviews — Escabiando Pociones</description>
  <language>es-AR</language>
  <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
{chr(10).join(items_xml)}
</channel>
</rss>
"""
    (ROOT / "rss.xml").write_text(rss, encoding="utf-8")
    print(f"rss.xml: {len(entries)} elemento(s)")


def build_sitemap(reviews, noticias, tag_index):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [
        {"loc": f"{SITE_URL}/", "lastmod": today, "priority": "1.0"},
        {"loc": f"{SITE_URL}/episodios.html", "lastmod": today, "priority": "0.7"},
        {"loc": f"{SITE_URL}/reviews.html", "lastmod": today, "priority": "0.8"},
        {"loc": f"{SITE_URL}/noticias.html", "lastmod": today, "priority": "0.9"},
        {"loc": f"{SITE_URL}/sobre.html", "lastmod": today, "priority": "0.5"},
        {"loc": f"{SITE_URL}/prensa.html", "lastmod": today, "priority": "0.5"},
        {"loc": f"{SITE_URL}/tags.html", "lastmod": today, "priority": "0.4"},
    ]
    for r in reviews:
        urls.append({"loc": f"{SITE_URL}/reviews/{r['slug']}.html", "lastmod": (r.get("date") or today)[:10], "priority": "0.8"})
    for n in noticias:
        urls.append({"loc": f"{SITE_URL}/noticias/{n['slug']}.html", "lastmod": (n.get("date") or today)[:10], "priority": "0.9"})
    for slug, entry in tag_index.items():
        newest_date = entry["items"][0][1].get("date", "") if entry["items"] else ""
        urls.append({"loc": f"{SITE_URL}/tags/{slug}.html", "lastmod": (newest_date or today)[:10], "priority": "0.3"})

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines += ["  <url>", f"    <loc>{u['loc']}</loc>", f"    <lastmod>{u['lastmod']}</lastmod>", f"    <priority>{u['priority']}</priority>", "  </url>"]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml: {len(urls)} URL(s)")


def clean_stale_pages(folder_name, valid_slugs):
    folder = ROOT / folder_name
    if not folder.exists():
        return
    for f in folder.glob("*.html"):
        if f.stem not in valid_slugs:
            f.unlink()
            print(f"Borrado (ya no existe o es borrador): {f}")


if __name__ == "__main__":
    reviews = json.loads((ROOT / "content" / "reviews.json").read_text(encoding="utf-8"))
    noticias = json.loads((ROOT / "content" / "noticias.json").read_text(encoding="utf-8"))

    published_reviews = [r for r in reviews if not r.get("draft")]
    published_noticias = [n for n in noticias if not n.get("draft")]

    tag_index = build_tag_index(published_reviews, published_noticias)

    for r in published_reviews:
        render_article_page("review", r, tag_index)
    for n in published_noticias:
        render_article_page("noticia", n, tag_index)

    for slug, entry in tag_index.items():
        render_tag_page(slug, entry["label"], entry["items"])
    render_tags_index(tag_index)

    clean_stale_pages("reviews", {r["slug"] for r in published_reviews})
    clean_stale_pages("noticias", {n["slug"] for n in published_noticias})
    clean_stale_tag_pages(set(tag_index.keys()))

    reviews_cards = "".join(render_card("review", r) for r in published_reviews[:9])
    reviews_html = f'<div class="grid grid-3">{reviews_cards}</div>' if published_reviews else \
        '<div class="empty-vial"><p class="mt-0">Todavía no hay reviews publicadas.</p></div>'
    fill_ssr_marker("reviews.html", "reviews-list", reviews_html)

    noticias_cards = "".join(render_card("noticia", n) for n in published_noticias[:9])
    noticias_html = f'<div class="grid grid-3">{noticias_cards}</div>' if published_noticias else \
        '<div class="empty-vial"><p class="mt-0">Todavía no hay noticias publicadas.</p></div>'
    fill_ssr_marker("noticias.html", "news-list", noticias_html)

    featured = sorted([n for n in published_noticias if n.get("featuredPosition")], key=lambda n: n["featuredPosition"])
    home_source = featured if featured else published_noticias[:3]
    home_cards = "".join(render_card("noticia", n) for n in home_source[:3])
    home_html = f'<div class="grid grid-3">{home_cards}</div>' if home_source else \
        '<div class="empty-vial"><p class="mt-0">Todavía no hay noticias publicadas.</p></div>'
    fill_ssr_marker("index.html", "home-news", home_html)

    build_rss(published_reviews, published_noticias)
    build_sitemap(published_reviews, published_noticias, tag_index)

    print(f"Listo: {len(published_reviews)} review(s), {len(published_noticias)} noticia(s), {len(tag_index)} página(s) de tag generadas.")
