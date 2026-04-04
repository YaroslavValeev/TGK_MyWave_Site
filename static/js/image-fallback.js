/**
 * Fallback для изображений при ошибке загрузки.
 * Заменяет inline onerror — используется data-fallback на img.
 */
(function () {
  function init() {
    document.querySelectorAll('img[data-fallback]').forEach(function (img) {
      if (img.dataset.fallbackHandled) return;
      img.dataset.fallbackHandled = '1';
      img.addEventListener('error', function () {
        var fallback = img.dataset.fallback;
        if (fallback) {
          img.onerror = null;
          img.src = fallback;
        }
      });
    });
  }
  function handleNewNodes(mutations) {
    mutations.forEach(function (m) {
      m.addedNodes.forEach(function (n) {
        if (n.nodeType === 1) {
          if (n.tagName === 'IMG' && n.dataset && n.dataset.fallback) init();
          n.querySelectorAll && n.querySelectorAll('img[data-fallback]').length && init();
        }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  if (typeof MutationObserver !== 'undefined') {
    var obs = new MutationObserver(handleNewNodes);
    obs.observe(document.body, { childList: true, subtree: true });
  }
})();
