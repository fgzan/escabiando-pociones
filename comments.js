/* Comentarios de Escabiando Pociones.
   Se carga en cada review/noticia. Lee los comentarios aprobados desde
   Supabase y manda los nuevos a la función "submit-comment".
   La clave "anon" es pública por diseño (la protege la seguridad de la tabla). */
(function () {
  var SUPABASE_URL = "https://mmhzgamixbnawbjhmagt.supabase.co";
  var SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1taHpnYW1peGJuYXdiamhtYWd0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc3ODMyOTUsImV4cCI6MjEwMzM1OTI5NX0.sSxZWLnwAG3yzGrsQUJgOgWPbruVoTyslxSXVij89EY";
  var MAX_BODY = 1000;

  var root = document.getElementById("comments");
  if (!root) return;
  var kind = root.getAttribute("data-kind");
  var slug = root.getAttribute("data-slug");
  var listEl = document.getElementById("comments-list");
  var countEl = document.getElementById("comments-count");
  var form = document.getElementById("comment-form");
  var nameEl = document.getElementById("comment-name");
  var bodyEl = document.getElementById("comment-body");
  var counterEl = document.getElementById("comment-counter");
  var msgEl = document.getElementById("comment-msg");
  var btn = document.getElementById("comment-submit");

  function authHeaders() {
    return { apikey: SUPABASE_ANON_KEY, Authorization: "Bearer " + SUPABASE_ANON_KEY };
  }

  function fmtDate(iso) {
    try {
      return new Date(iso).toLocaleDateString("es-AR", { day: "numeric", month: "long", year: "numeric" });
    } catch (e) { return ""; }
  }

  function renderComments(items) {
    listEl.innerHTML = "";
    countEl.textContent = items.length ? "(" + items.length + ")" : "";
    if (!items.length) {
      var empty = document.createElement("p");
      empty.className = "comments-empty";
      empty.textContent = "Todavía no hay comentarios. ¡Sé el primero!";
      listEl.appendChild(empty);
      return;
    }
    items.forEach(function (c) {
      var box = document.createElement("div");
      box.className = "comment";
      var head = document.createElement("div");
      head.className = "comment-head";
      var who = document.createElement("strong");
      who.textContent = c.name;
      var when = document.createElement("span");
      when.textContent = fmtDate(c.created_at);
      head.appendChild(who);
      head.appendChild(when);
      var text = document.createElement("p");
      text.className = "comment-body";
      text.textContent = c.body;
      box.appendChild(head);
      box.appendChild(text);
      listEl.appendChild(box);
    });
  }

  function loadComments() {
    var url = SUPABASE_URL + "/rest/v1/comments?select=id,name,body,created_at" +
      "&kind=eq." + encodeURIComponent(kind) +
      "&slug=eq." + encodeURIComponent(slug) +
      "&order=created_at.asc";
    fetch(url, { headers: authHeaders() })
      .then(function (r) { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .then(renderComments)
      .catch(function () {
        listEl.innerHTML = "";
        var p = document.createElement("p");
        p.className = "comments-empty";
        p.textContent = "No pudimos cargar los comentarios en este momento.";
        listEl.appendChild(p);
      });
  }

  function showMsg(text, ok) {
    msgEl.textContent = text;
    msgEl.className = "comment-msg " + (ok ? "comment-msg-ok" : "comment-msg-err");
  }

  bodyEl.addEventListener("input", function () {
    counterEl.textContent = bodyEl.value.length + " / " + MAX_BODY;
  });

  try {
    var saved = localStorage.getItem("ep_comment_name");
    if (saved) nameEl.value = saved;
  } catch (e) {}

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var name = nameEl.value.trim();
    var body = bodyEl.value.trim();
    if (!name) { showMsg("Escribí tu nombre.", false); return; }
    if (body.length < 2) { showMsg("Escribí tu comentario.", false); return; }

    btn.disabled = true;
    btn.textContent = "Enviando…";
    var headers = authHeaders();
    headers["Content-Type"] = "application/json";

    fetch(SUPABASE_URL + "/functions/v1/submit-comment", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        kind: kind,
        slug: slug,
        name: name,
        body: body,
        website: document.getElementById("comment-website").value
      })
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok || data.error) throw new Error(data.error || "No pudimos enviar tu comentario.");
          return data;
        });
      })
      .then(function () {
        try { localStorage.setItem("ep_comment_name", name); } catch (e) {}
        bodyEl.value = "";
        counterEl.textContent = "0 / " + MAX_BODY;
        showMsg("¡Gracias! Tu comentario quedó pendiente de aprobación y va a aparecer apenas lo revisemos.", true);
      })
      .catch(function (err) {
        showMsg(err.message || "No pudimos enviar tu comentario.", false);
      })
      .then(function () {
        btn.disabled = false;
        btn.textContent = "Enviar comentario";
      });
  });

  loadComments();
})();
