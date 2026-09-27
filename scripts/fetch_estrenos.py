"""
Busca en la API de RAWG (rawg.io) los juegos que salen en la semana
actual (lunes a domingo, huso horario Argentina) y guarda el
resultado en content/estrenos/<lunes-de-la-semana>.json, con el
mismo formato que ya usan content/reviews/ y content/noticias/ (un
archivo por elemento, que después junta build_content_index.py).

Se corre solo, todos los lunes, disparado por
.github/workflows/estrenos-semanales.yml. También se puede disparar
a mano desde la pestaña Actions (workflow_dispatch) para probarlo o
para forzar una actualización de la semana en curso.

Necesita la variable de entorno RAWG_API_KEY (se pasa como secreto
del repo desde el workflow). Para conseguir una clave gratis:
https://rawg.io/apidocs (alcanza con crear una cuenta).

Términos de uso de RAWG: es gratis para uso personal siempre que se
cite a RAWG como fuente y se linkee — por eso cada juego guarda su
`rawg_url`, y la plantilla (render_articles.py) tiene que mostrar esa
atribución en la página.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import date, timedelta, timezone, datetime

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent

API_KEY = os.environ.get("RAWG_API_KEY", "").strip()
API_URL = "https://api.rawg.io/api/games"

# Cuántos juegos como máximo mostramos por semana. RAWG devuelve de
# todo (desde AAA hasta shovelware de mobile), así que primero
# filtramos por popularidad (campo "added") y de ahí nos quedamos con
# los más relevantes.
MAX_JUEGOS = 15

# Huso horario de Argentina. Uso un offset fijo en vez de
# zoneinfo("America/Argentina/Buenos_Aires") para no depender de que
# el runner tenga la base de datos de husos horarios instalada.
# Argentina no tiene horario de verano desde 2009, así que -3 fijo es
# correcto siempre.
ART = timezone(timedelta(hours=-3))


def semana_actual():
    """Devuelve (lunes, domingo) de la semana actual, en fecha Argentina."""
    hoy = datetime.now(ART).date()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)
    return lunes, domingo


def pedir_con_reintentos(url, intentos=3):
    ultimo_error = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 — queremos capturar cualquier falla de red/API
            ultimo_error = e
            if i < intentos - 1:
                time.sleep(5 * (i + 1))
    raise RuntimeError(f"No se pudo consultar la API de RAWG tras {intentos} intentos: {ultimo_error}")


def buscar_juegos(lunes, domingo):
    params = {
        "key": API_KEY,
        "dates": f"{lunes.isoformat()},{domingo.isoformat()}",
        "ordering": "-added",
        "page_size": 40,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    data = pedir_con_reintentos(url)
    resultados = data.get("results", [])

    juegos = []
    for g in resultados:
        if g.get("tba"):
            continue
        released = g.get("released")
        if not released:
            continue
        # Filtro extra de seguridad: a veces la API devuelve juegos
        # con fecha cercana pero fuera del rango pedido.
        try:
            fecha_release = date.fromisoformat(released)
        except ValueError:
            continue
        if not (lunes <= fecha_release <= domingo):
            continue

        plataformas = []
        for p in (g.get("platforms") or []):
            nombre = (p.get("platform") or {}).get("name")
            if nombre:
                plataformas.append(nombre)
        if not plataformas:
            continue

        juegos.append({
            "name": g.get("name") or "Sin nombre",
            "released": released,
            "platforms": plataformas,
            "cover": g.get("background_image"),
            "rawg_url": f"https://rawg.io/games/{g.get('slug')}" if g.get("slug") else "https://rawg.io",
            "added": g.get("added", 0),
        })

    # Nos quedamos con los más populares...
    juegos.sort(key=lambda j: j["added"], reverse=True)
    juegos = juegos[:MAX_JUEGOS]
    # ...pero se muestran ordenados por fecha de salida.
    juegos.sort(key=lambda j: j["released"])
    for j in juegos:
        j.pop("added", None)
    return juegos


def main():
    if not API_KEY:
        print("Falta la variable de entorno RAWG_API_KEY (secreto del repo). No se puede consultar RAWG.", file=sys.stderr)
        sys.exit(1)

    lunes, domingo = semana_actual()
    slug = lunes.isoformat()

    try:
        juegos = buscar_juegos(lunes, domingo)
        error = None
    except Exception as e:  # noqa: BLE001
        juegos = []
        error = str(e)
        print(f"⚠️  Falló la búsqueda en RAWG: {error}", file=sys.stderr)

    item = {
        "slug": slug,
        "date": lunes.isoformat(),
        "week_start": lunes.isoformat(),
        "week_end": domingo.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "RAWG (rawg.io)",
        "games": juegos,
        "fetch_error": error,
    }

    out_dir = ROOT / "content" / "estrenos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(item, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"{out_path}: {len(juegos)} juego(s) para la semana del {lunes} al {domingo}.")
    if error:
        # No hacemos que falle el Action entero (así igual queda
        # commiteado un archivo de esa semana, aunque sea vacío) pero
        # sí devolvemos código de error para que se vea en rojo en la
        # pestaña Actions y quede claro que hay que revisar.
        sys.exit(1)


if __name__ == "__main__":
    main()
