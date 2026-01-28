document.addEventListener('DOMContentLoaded', () => {
  const carousels = Array.from(document.querySelectorAll('.js-service-carousel'));
  if (carousels.length === 0) return;

  function parseImages(raw) {
    return String(raw || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function normalizeIndex(index, length) {
    if (length <= 0) return 0;
    const mod = index % length;
    return mod < 0 ? mod + length : mod;
  }

  carousels.forEach((carousel) => {
    const images = parseImages(carousel.getAttribute('data-images'));
    const img = carousel.querySelector('.service-card-media-img');
    const prev = carousel.querySelector('.service-card-media-btn.prev');
    const next = carousel.querySelector('.service-card-media-btn.next');

    if (!img || images.length === 0) return;

    let currentIndex = 0;

    function render() {
      currentIndex = normalizeIndex(currentIndex, images.length);
      img.src = images[currentIndex];
    }

    function go(delta) {
      currentIndex += delta;
      render();
    }

    if (prev) prev.addEventListener('click', () => go(-1));
    if (next) next.addEventListener('click', () => go(1));

    if (images.length <= 1) {
      if (prev) prev.style.display = 'none';
      if (next) next.style.display = 'none';
    }
  });
});


