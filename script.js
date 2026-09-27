// Menú de secciones y buscador embebido: abrir/cerrar, y que al abrir
// uno se cierre el otro (no tiene sentido tener los dos desplegados a
// la vez).
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  const searchToggle = document.querySelector('.nav-search-toggle');
  const searchBox = document.querySelector('.nav-search-box');
  const searchInput = searchBox ? searchBox.querySelector('input') : null;

  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const isOpen = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      if (isOpen && searchBox) {
        searchBox.hidden = true;
        if (searchToggle) searchToggle.setAttribute('aria-expanded', 'false');
      }
    });
    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => links.classList.remove('open'));
    });
  }

  if (searchToggle && searchBox) {
    searchToggle.addEventListener('click', () => {
      const willOpen = searchBox.hidden;
      searchBox.hidden = !willOpen;
      searchToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (willOpen) {
        if (links) links.classList.remove('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
        if (searchInput) searchInput.focus();
      }
    });
  }
});

// Botón "Copiar link" en las notas: copia la URL de la nota al
// portapapeles y avisa con un cambio de texto de 1.5 segundos.
document.addEventListener('click', (event) => {
  const button = event.target.closest('.js-copy-link');
  if (!button) return;

  const url = button.dataset.url || window.location.href;
  const original = button.textContent;

  navigator.clipboard.writeText(url).then(() => {
    button.textContent = '¡Copiado!';
    setTimeout(() => { button.textContent = original; }, 1500);
  }).catch(() => {
    // Si el navegador no deja copiar (por permisos, por ejemplo),
    // no rompemos nada: el link ya está en la barra de direcciones.
  });
});
