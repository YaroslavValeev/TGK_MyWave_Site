document.addEventListener('DOMContentLoaded', () => {
  const carousels = Array.from(document.querySelectorAll('.js-service-carousel'));

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

    if (!img || images.length === 0) return; // skip this card only

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

// Единая логика scroll для Услуги / Товары / Проекты / Блог (не ломает .js-service-carousel)
(function () {
  function initScrollCarousel(root) {
    const track = root.querySelector(".carousel-track");
    const prev = root.querySelector(".carousel-prev");
    const next = root.querySelector(".carousel-next");
    if (!track || !prev || !next) return;

    const stop = function (e) {
      e.preventDefault();
      e.stopPropagation();
    };

    const getStep = function () {
      const first = track.querySelector(":scope > *");
      if (first) {
        const styles = window.getComputedStyle(track);
        const gap =
          parseFloat(styles.columnGap || styles.gap || "0") ||
          0;
        return first.getBoundingClientRect().width + gap;
      }
      return Math.max(240, Math.round(track.clientWidth * 0.9));
    };

    const update = function () {
      const max = track.scrollWidth - track.clientWidth;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft >= max - 2;
    };

    prev.addEventListener("click", function (e) {
      stop(e);
      track.scrollBy({ left: -getStep(), behavior: "smooth" });
      window.setTimeout(update, 200);
    });

    next.addEventListener("click", function (e) {
      stop(e);
      track.scrollBy({ left: getStep(), behavior: "smooth" });
      window.setTimeout(update, 200);
    });

    track.addEventListener(
      "scroll",
      function () { window.requestAnimationFrame(update); },
      { passive: true }
    );

    window.addEventListener("resize", update);
    update();
  }

  function initAll() {
    document
      .querySelectorAll(
        ".services-carousel, .products-carousel, .projects-carousel, .blog-carousel"
      )
      .forEach(initScrollCarousel);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();


