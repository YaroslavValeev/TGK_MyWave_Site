/**
 * Галерея изображений внутри карточки (2+ файлов).
 * Переключение по стрелкам prev/next.
 * Предпочитает data-image-urls (полные URL от сервера), иначе собирает baseUrl + path из data-images.
 */
(function () {
  function init() {
    document.querySelectorAll('.card-media-carousel').forEach(function (carousel) {
      var urlsStr = carousel.dataset.imageUrls || '';
      var imagesStr = carousel.dataset.images || '';
      var urls = urlsStr ? urlsStr.split(',').map(function (s) { return s.trim(); }).filter(Boolean) : [];
      var paths = imagesStr ? imagesStr.split(',').map(function (s) { return s.trim(); }).filter(Boolean) : [];
      var images = urls.length >= 2 ? urls : paths;
      if (images.length < 2) return;

      var img = carousel.querySelector('.service-image');
      if (!img) return;

      var prevBtn = carousel.querySelector('.carousel-prev-inner');
      var nextBtn = carousel.querySelector('.carousel-next-inner');
      var idx = 0;
      var baseUrl = window.location.origin + '/static/';
      var useFullUrls = urls.length >= 2;

      function showImage(i) {
        idx = ((i % images.length) + images.length) % images.length;
        var src = useFullUrls ? images[idx] : baseUrl + images[idx];
        img.src = src;
      }

      if (prevBtn) {
        prevBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          showImage(idx - 1);
        });
      }
      if (nextBtn) {
        nextBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          showImage(idx + 1);
        });
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
