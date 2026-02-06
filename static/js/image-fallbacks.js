document.addEventListener('DOMContentLoaded', function () {
  const imgs = document.querySelectorAll('img[data-fallback]');
  imgs.forEach(img => {
    // If image already broken, browser may not emit error; try a quick check using naturalWidth after load
    const fallback = img.getAttribute('data-fallback');
    function setFallback() {
      try {
        if (!fallback) return;
        if (img.src === fallback) return;
        img.src = fallback;
        img.removeAttribute('srcset');
        img.classList.add('is-fallback');
      } catch (e) {
        // ignore
      }
    }

    img.addEventListener('error', function onError() {
      img.removeEventListener('error', onError);
      setFallback();
    });

    // Defensive: if image loads but with 0 naturalWidth (broken), replace after load
    img.addEventListener('load', function onLoad() {
      if (img.naturalWidth === 0) setFallback();
    });
  });
});
