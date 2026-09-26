// Menú mobile: abrir/cerrar
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');

  if (toggle && links) {
    toggle.addEventListener('click', () => {
      const isOpen = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => links.classList.remove('open'));
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
