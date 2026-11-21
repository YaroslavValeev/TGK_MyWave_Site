/**
 * Раскрытие карточек услуг по клику.
 * CTA-ссылки в project-card: capture-phase делегирование — переход до логики карусели/карточки.
 */
(function () {
  function equalizeProjectCards() {
    var track = document.querySelector('.projects-carousel .carousel-track');
    if (!track) return;
    var cards = track.querySelectorAll('.project-card:not(.is-expanded)');
    if (!cards.length) return;
    cards.forEach(function (card) {
      card.style.minHeight = '';
    });
    var maxH = 0;
    cards.forEach(function (card) {
      maxH = Math.max(maxH, card.offsetHeight);
    });
    if (maxH < 1) return;
    cards.forEach(function (card) {
      card.style.minHeight = maxH + 'px';
    });
  }

  function loadSpotmapIframe(card) {
    var iframe = card.querySelector('iframe[data-spotmap-src]');
    if (!iframe) return;
    var src = iframe.getAttribute('data-spotmap-src');
    if (src && !iframe.getAttribute('src')) {
      iframe.setAttribute('src', src);
    }
  }

  function setCardExpanded(card, expanded) {
    if (expanded) {
      card.classList.add('is-expanded');
      loadSpotmapIframe(card);
    } else {
      card.classList.remove('is-expanded');
    }
    equalizeProjectCards();
  }

  function init() {
    var cards = document.querySelectorAll('.js-expandable-card, .project-card');
    cards.forEach(function (card) {
      card.addEventListener('click', function (e) {
        if (e.target.closest('.js-spotmap-expand')) {
          e.preventDefault();
          e.stopPropagation();
          setCardExpanded(card, true);
          return;
        }
        if (e.target.closest('.js-spotmap-collapse')) {
          e.preventDefault();
          e.stopPropagation();
          setCardExpanded(card, false);
          return;
        }
        // Не раскрывать, если клик по кнопке или ссылке
        if (e.target.closest('.book-now, .btn, a, .carousel-nav, .carousel-prev-inner, .carousel-next-inner, .wake-checklist__more-btn, .wake-checklist__checkbox, .card-media-carousel__indicator, .product-card')) return;
        var willExpand = !card.classList.contains('is-expanded');
        setCardExpanded(card, willExpand);
      });
    });
    equalizeProjectCards();
    window.addEventListener('resize', equalizeProjectCards);
    window.addEventListener('load', equalizeProjectCards);

    // Capture-phase: клик по ссылке в project-card — сразу переход, без вмешательства карусели/карточки
    document.addEventListener('click', function (e) {
      var link = e.target.closest('.project-card .project-card__actions a, .project-card .project-card-expanded__cta a, .project-card__actions--links a');
      if (!link) return;
      // target=_blank (SpotMap «на всю страницу») — не перехватываем
      if (link.getAttribute('target') === '_blank') return;
      var href = link.getAttribute('href');
      if (href && href !== '#' && !href.startsWith('javascript:')) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        window.location.href = href;
      }
    }, true);

    // /projects#spotmap — сразу раскрыть карту
    if (window.location.hash === '#spotmap') {
      var spotmapCard = document.getElementById('spotmap');
      if (spotmapCard) {
        setCardExpanded(spotmapCard, true);
        spotmapCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
