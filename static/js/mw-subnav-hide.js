/**
 * Скрывает subnav при скролле вниз, показывает при скролле вверх.
 * Используется на странице WakeSurf Safari.
 */
(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    const subnav = document.getElementById("mw-subnav");
    if (!subnav) return;

    const threshold = 80;
    let lastScrollY = window.pageYOffset;
    let ticking = false;

    function update() {
      const scrollY = window.pageYOffset;
      if (scrollY < threshold) {
        subnav.classList.remove("is-hidden");
      } else if (scrollY > lastScrollY) {
        subnav.classList.add("is-hidden");
      } else {
        subnav.classList.remove("is-hidden");
      }
      lastScrollY = scrollY;
      ticking = false;
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(update);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
  });
})();
