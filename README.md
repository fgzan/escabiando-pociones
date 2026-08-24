# Escabiando Pociones — sitio web

Sitio estático (HTML/CSS/JS puro) con panel de carga hecho con
**Sveltia CMS** (sucesor open source de Netlify/Decap CMS). Sin
Netlify, sin Cloudflare, sin OAuth Apps — solo GitHub, que es lo mismo
que ya usás para el hosting.

## 1. Publicarlo en GitHub Pages

1. Creá un repo público en GitHub llamado `escabiando-pociones`.
2. Subí todos estos archivos.
3. Settings → Pages → Branch: `main`, carpeta `/ (root)` → Save.
4. En 1-2 minutos el sitio está en `https://TU_USUARIO.github.io/escabiando-pociones/`.

## 2. Activar el panel de carga (`/admin/`)

1. Si tu usuario de GitHub o el nombre del repo no son `fgzan` /
   `escabiando-pociones`, abrí `admin/config.yml` y corregí la línea
   `repo:` con los datos correctos.
2. Generá tu token personal: andá a
   **github.com/settings/personal-access-tokens/new**, en "Repository
   access" elegí **"Only select repositories"** → tu repo, y en
   "Repository permissions" → **"Contents"** → **"Read and write"**.
   Generalo y copialo (solo se muestra una vez).
3. Entrá a `tusitio.github.io/escabiando-pociones/admin/`.
4. En la pantalla de login, hacé clic en **"Sign in with token"** (no
   hace falta usar el botón grande de "Login with GitHub", que sí
   pediría un paso extra) y pegá el token.
5. Listo, ya estás dentro del panel.

### Lo que trae Sveltia CMS de fábrica

- Editor con vista previa en vivo mientras escribís.
- Manejo de imágenes real: subís portada y fotos dentro del texto
  desde el propio editor, sin límites artificiales de tamaño (más allá
  de lo razonable).
- Casillero de **"Borrador"** en cada review o noticia: mientras esté
  tildado, no aparece en la web pública — lo destildás cuando esté
  lista para publicar.
- Es un proyecto open source mantenido activamente, con mejoras y
  arreglos constantes — no depende de que nosotros lo sostengamos.

### Para que tus compañeros también puedan cargar contenido

Cada uno necesita ser **colaborador** del repositorio:

1. En GitHub: Settings del repo → Collaborators → Add people → su
   usuario o mail.
2. Cada persona genera su propio token siguiendo el paso 2 de arriba
   (con su propia cuenta) y lo usa para entrar a `/admin/` desde su
   navegador con "Sign in with token".

Así cada quien firma sus propios cambios (queda registrado en el
historial de GitHub quién publicó qué) sin compartir contraseñas ni
tokens entre todos.

## 3. Probarlo desde tu PC antes de subir nada

Para ver las páginas del sitio (no el panel, que sí necesita un repo
real en GitHub) sin subir todavía nada:

1. Abrí una terminal en la carpeta del sitio.
2. Corré `python3 -m http.server 8000` (Python ya viene instalado en
   Mac y Linux; en Windows hay que instalarlo, o usar la extensión
   "Live Server" de VS Code como alternativa).
3. Abrí `http://localhost:8000` en el navegador.

El panel de `/admin/` en cambio sí necesita el repositorio ya creado
en GitHub para poder loguearte y guardar — no se puede probar sin eso,
porque su trabajo es justamente escribir ahí.

## 4. Sobre el video de YouTube en Episodios

Si al abrir el sitio localmente (doble clic al HTML) un video de
YouTube tira error, es normal: YouTube bloquea los embeds abiertos
desde un archivo local (`file://`). Con el sitio corriendo con
`python3 -m http.server` (paso anterior) o ya publicado en GitHub
Pages, cualquier embed de YouTube anda bien.

## 5. Estructura

```
index.html         → home (episodio + noticias + reviews)
episodios.html      → todos los capítulos
reviews.html        → listado de reviews (lee content/reviews.json)
review.html         → detalle de una review
noticias.html       → listado de noticias (lee content/noticias.json)
noticia.html        → detalle de una noticia
sobre.html          → sobre el podcast
prensa.html         → contacto para devs y editoras
style.css           → todo el diseño
script.js           → menú mobile
assets/             → logo, arte, e imágenes subidas desde el panel
admin/
  index.html         → carga Sveltia CMS
  config.yml         → define los formularios del panel
content/
  reviews.json       → datos de las reviews (los edita el panel)
  noticias.json       → datos de las noticias (los edita el panel)
```
