/**
 * Раскрытие карточек услуг по клику.
 * CTA-ссылки в project-card: capture-phase делегирование — переход до логики карусели/карточки.
 */
(function () {
  function init() {
    var cards = document.querySelectorAll('.js-expandable-card, .project-card');
    cards.forEach(function (card) {
      card.addEventListener('click', function (e) {
        // Не раскрывать, если клик по кнопке или ссылке
        if (e.target.closest('.book-now, .btn, a, .carousel-nav, .carousel-prev-inner, .carousel-next-inner, .wake-checklist__more-btn, .wake-checklist__checkbox, .card-media-carousel__indicator')) return;
        card.classList.toggle('is-expanded');
      });
    });

    // Capture-phase: клик по ссылке в project-card — сразу переход, без вмешательства карусели/карточки
    document.addEventListener('click', function (e) {
      var link = e.target.closest('.project-card .project-card__actions a, .project-card .project-card-expanded__cta a, .project-card__actions--links a');
      if (!link) return;
      var href = link.getAttribute('href');
      if (href && href !== '#' && !href.startsWith('javascript:')) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.location.href = href;
      }
    }, true);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
