"""
Trae el ranking de "más leídas" desde GoatCounter (el analytics que ya
usa el sitio) y arma content/mas_leidas.json con las reviews/noticias
más visitadas de los últimos 7 días.

Corre una vez por día (ver .github/workflows/mas-leidas.yml). Necesita
dos secretos configurados en el repo (Settings -> Secrets and
variables -> Actions):
  - GOATCOUNTER_CODE: el "código" de tu sitio en GoatCounter -- la
    parte antes de ".goatcounter.com" en la URL donde ves tus
    estadísticas (ej. si entrás a "escabiando.goatcounter.com", el
    código es "escabiando").
  - GOATCOUNTER_API_TOKEN: un token nuevo generado en GoatCounter
    (arriba a la derecha, tu usuario -> API -> "New API key"). Alcanza
    con darle permiso de solo lectura de estadísticas, no hace falta
    nada más.

Si algo falla (token vencido, GoatCounter caído, sin datos todavía,
etc.), esto corta SIN tocar el archivo ya commiteado -- el home sigue
mostrando el último ranking bueno que se pudo traer, en vez de mostrar
la sección vacía de golpe. Solo se sale con error (que deja el
workflow en rojo y dispara el mail automático de GitHub) cuando el
problema es de verdad un error de la API -- no cuando simplemente no
hubo visitas esta semana.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_N = 6
DAYS_WINDOW = 7

# Coincide con las rutas reales que arma render_articles.py para cada
# tipo de contenido: /reviews/<slug>.html y /noticias/<slug>.html.
PATH_RE = re.compile(r"^/(reviews|noticias)/([^/]+)\.html$")


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch_hits(code, token):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS_WINDOW)
    url = (
        f"https://{code}.goatcounter.com/api/v0/stats/hits"
        f"?start={start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&end={end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&limit=100"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    code = os.environ.get("GOATCOUNTER_CODE", "").strip()
    token = os.environ.get("GOATCOUNTER_API_TOKEN", "").strip()
    if not code or not token:
        fail("Faltan las variables de entorno GOATCOUNTER_CODE y/o GOATCOUNTER_API_TOKEN.")

    try:
        data = fetch_hits(code, token)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        fail(f"GoatCounter respondió {e.code}: {body}")
    except Exception as e:
        fail(f"No se pudo consultar la API de GoatCounter: {e}")

    reviews = json.loads((ROOT / "content" / "reviews.json").read_text(encoding="utf-8"))
    noticias = json.loads((ROOT / "content" / "noticias.json").read_text(encoding="utf-8"))
    valid_slugs = {
        "review": {r["slug"] for r in reviews if not r.get("draft")},
        "noticia": {n["slug"] for n in noticias if not n.get("draft")},
    }

    ranking = []
    for hit in data.get("hits", []):
        m = PATH_RE.match(hit.get("path", ""))
        if not m:
            continue  # es /admin/, /search.html, la home, etc. -- no nos interesa
        kind_folder, slug = m.groups()
        kind = "review" if kind_folder == "reviews" else "noticia"
        if slug not in valid_slugs[kind]:
            continue  # se borró, o quedó como borrador, desde que se generó esta visita
        ranking.append({"kind": kind, "slug": slug, "count": hit.get("count", 0)})
        if len(ranking) >= TOP_N:
            break

    if not ranking:
        # Puede ser una semana floja de verdad, no necesariamente un
        # error -- no hace falta prender ninguna alarma por esto, solo
        # dejamos el ranking anterior como estaba.
        print("No hubo reviews/noticias con visitas en los últimos "
              f"{DAYS_WINDOW} días. Se deja el ranking anterior sin cambios.")
        sys.exit(0)

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": DAYS_WINDOW,
        "items": ranking,
    }
    (ROOT / "content" / "mas_leidas.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"content/mas_leidas.json: {len(ranking)} nota(s) en el ranking.")


if __name__ == "__main__":
    main()
