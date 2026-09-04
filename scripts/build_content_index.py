"""
Junta todos los archivos individuales de content/reviews/*.json y
content/noticias/*.json en dos archivos índice (content/reviews.json y
content/noticias.json) que son los que la web realmente lee. De paso,
arma sitemap.xml con todas las URLs del sitio (para Google).

Se corre solo, disparado por el GitHub Action en
.github/workflows/build-index.yml, cada vez que el panel guarda una
review o noticia nueva. No hace falta correrlo a mano.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://www.escabiandopociones.com.ar"


def build(folder_name, index_name):
    folder = ROOT / "content" / folder_name
    items = []

    if folder.exists():
        for file in sorted(folder.glob("*.json")):
            with open(file, encoding="utf-8") as fh:
                data = json.load(fh)
            data["slug"] = file.stem
            items.append(data)

    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    out_path = ROOT / "content" / f"{index_name}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"{out_path}: {len(items)} elemento(s)")
    return items


def build_sitemap(reviews, noticias):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{SITE_URL}/", "lastmod": today, "priority": "1.0"},
        {"loc": f"{SITE_URL}/episodios.html", "lastmod": today, "priority": "0.7"},
        {"loc": f"{SITE_URL}/reviews.html", "lastmod": today, "priority": "0.8"},
        {"loc": f"{SITE_URL}/noticias.html", "lastmod": today, "priority": "0.9"},
        {"loc": f"{SITE_URL}/sobre.html", "lastmod": today, "priority": "0.5"},
        {"loc": f"{SITE_URL}/prensa.html", "lastmod": today, "priority": "0.5"},
    ]

    for r in reviews:
        if r.get("draft"):
            continue
        lastmod = (r.get("date") or today)[:10]
        urls.append({
            "loc": f"{SITE_URL}/review.html?slug={r['slug']}",
            "lastmod": lastmod,
            "priority": "0.8",
        })

    for n in noticias:
        if n.get("draft"):
            continue
        lastmod = (n.get("date") or today)[:10]
        urls.append({
            "loc": f"{SITE_URL}/noticia.html?slug={n['slug']}",
            "lastmod": lastmod,
            "priority": "0.9",
        })

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{u['loc']}</loc>")
        lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        lines.append(f"    <priority>{u['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")

    out_path = ROOT / "sitemap.xml"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"{out_path}: {len(urls)} URL(s)")


if __name__ == "__main__":
    reviews = build("reviews", "reviews")
    noticias = build("noticias", "noticias")
    build_sitemap(reviews, noticias)
