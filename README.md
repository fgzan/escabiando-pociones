# Escabiando Pociones — sitio web

Sitio estático (HTML/CSS/JS puro) con panel de carga hecho con
**Sveltia CMS**. Cada review y cada noticia vive en su propio archivo
(así el slug de la URL se arma solo, a partir del título) y un
**GitHub Action** —un robotcito que ya vive gratis dentro de GitHub,
no es ningún servicio nuevo— los junta automáticamente en un índice
que la web lee rápido.

## 1. Publicarlo en GitHub Pages

1. Creá un repo público en GitHub llamado `escabiando-pociones`.
2. Subí todos estos archivos (¡importante! asegurate de que se suban
   también las carpetas ocultas `.github/` y `content/reviews/` y
   `content/noticias/` — a veces el navegador no las arrastra si están
   vacías; si eso pasa, mirá la nota al final de este documento).
3. Settings → Pages → Branch: `main`, carpeta `/ (root)` → Save.
4. **Paso extra, una sola vez:** Settings → Actions → General → bajá
   hasta "Workflow permissions" → elegí **"Read and write
   permissions"** → Save. Sin esto, el robotcito no tiene permiso para
   guardar el índice actualizado.
5. En 1-2 minutos el sitio está en `https://TU_USUARIO.github.io/escabiando-pociones/`.

## 2. Activar el panel de carga (`/admin/`)

1. Si tu usuario de GitHub o el nombre del repo no son `fgzan` /
   `escabiando-pociones`, abrí `admin/config.yml` y corregí la línea
   `repo:`.
2. Generá tu token personal en
   **github.com/settings/personal-access-tokens/new** — "Only select
   repositories" → tu repo → permiso "Contents" en "Read and write".
3. Entrá a `tusitio.github.io/escabiando-pociones/admin/` → "Sign in
   with token" → pegá el token.

### Cómo se arma el slug ahora

Ya no hay que tipearlo: cada vez que creás una review o noticia nueva,
Sveltia le pone de nombre de archivo una versión "limpia" del título
(todo minúscula, sin tildes, espacios cambiados por guiones). Ese
nombre de archivo ES la URL de esa nota. Si más adelante cambiás el
título, el nombre del archivo no cambia solo — así que la URL queda
estable aunque retoques el texto después.

### El robotcito (GitHub Action)

Cada vez que se guarda una review o noticia desde el panel, GitHub
corre solo un script chiquito que junta todos los archivos de
`content/reviews/` y `content/noticias/` en `content/reviews.json` y
`content/noticias.json` — que son los que la web realmente muestra.
Tarda entre 10 y 30 segundos después de guardar. Lo podés ver
funcionando en la pestaña **"Actions"** del repositorio si tenés
curiosidad.

### Para que tus compañeros también carguen contenido

Cada uno necesita ser **colaborador** del repositorio (Settings del
repo → Collaborators → Add people) y generar su propio token siguiendo
el paso 2 de arriba, con su propia cuenta.

## 3. Probarlo desde tu PC antes de subir nada

1. Terminal en la carpeta del sitio → `python3 -m http.server 8000`
2. Abrí `http://localhost:8000`

El panel de `/admin/` sí necesita el repositorio ya creado en GitHub
para poder loguearte y guardar.

## 4. Nota sobre carpetas vacías al subir por primera vez

Git no sube carpetas vacías. Si al arrastrar los archivos a GitHub
notás que `content/reviews/`, `content/noticias/` o `.github/` no
aparecieron, es por eso — dentro de esas carpetas dejé un archivo
`.gitkeep` invisible que resuelve el problema, pero si tu explorador
de archivos oculta los archivos que empiezan con punto, puede que no
lo veas y no lo arrastres sin querer. Si te pasa, avisame y lo
solucionamos.

## 5. Estructura

```
index.html          → home (episodio + noticias + reviews)
episodios.html       → todos los capítulos
reviews.html         → listado de reviews (lee content/reviews.json)
review.html          → detalle de una review
noticias.html        → listado de noticias (lee content/noticias.json)
noticia.html         → detalle de una noticia
sobre.html           → sobre el podcast
prensa.html          → contacto para devs y editoras
style.css            → todo el diseño
script.js            → menú mobile
assets/              → logo, arte, e imágenes subidas desde el panel
admin/
  index.html          → carga Sveltia CMS
  config.yml          → define los formularios del panel
content/
  reviews/             → un archivo .json por review (lo escribe el panel)
  noticias/             → un archivo .json por noticia (lo escribe el panel)
  reviews.json          → índice combinado (lo arma solo el robotcito)
  noticias.json          → índice combinado (lo arma solo el robotcito)
.github/workflows/
  build-index.yml     → el robotcito
scripts/
  build_content_index.py → lo que corre el robotcito
```
