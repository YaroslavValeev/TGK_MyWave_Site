/**
 * Стрелки карусели: прокрутка .carousel-track по клику на .carousel-prev / .carousel-next.
 * Работает для Services, Products, Projects — единый компонент.
 */
(function () {
  function init() {
    document.querySelectorAll('.services-carousel, .products-carousel, .projects-carousel, .blog-carousel').forEach(function (wrapper) {
      var prev = wrapper.querySelector('.carousel-prev');
      var next = wrapper.querySelector('.carousel-next');
      var track = wrapper.querySelector('.carousel-track') || wrapper.querySelector('.projects-carousel-track');
      if (!prev || !next || !track) return;

      var scrollStep = 320;
      function scrollBy(delta) {
        track.scrollBy({ left: delta * scrollStep, behavior: 'smooth' });
      }
      prev.addEventListener('click', function () { scrollBy(-1); });
      next.addEventListener('click', function () { scrollBy(1); });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
