/**
 * Подгонка фото в карточках: альбомные — cover (без серых полей), портрет — contain.
 */
(function () {
  var LANDSCAPE_RATIO = 1.05;

  function applyFit(img) {
    if (!img || img.tagName !== 'IMG') return;
    var w = img.naturalWidth;
    var h = img.naturalHeight;
    if (!w || !h) return;
    var ratio = w / h;
    img.classList.remove('card-media--cover', 'card-media--contain');
    if (ratio >= LANDSCAPE_RATIO) {
      img.classList.add('card-media--cover');
    } else {
      img.classList.add('card-media--contain');
    }
  }

  function bind(img) {
    if (!img || img.dataset.mediaFitBound === '1') return;
    img.dataset.mediaFitBound = '1';
    var run = function () {
      applyFit(img);
    };
    if (img.complete && img.naturalWidth > 0) {
      run();
    } else {
      img.addEventListener('load', run, { once: true });
    }
  }

  function scan(root) {
    var scope = root || document;
    var sel =
      '[data-card-media-fit], ' +
      '.services-carousel .service-image, .products-carousel .service-image, ' +
      '.projects-carousel .project-card .service-image, ' +
      '.blog-index-grid .service-image, .blog-home-grid .service-image';
    scope.querySelectorAll(sel).forEach(bind);
  }

  window.CardMediaFit = { apply: applyFit, bind: bind, scan: scan };

  function init() {
    scan(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
