/**
 * Галерея внутри карточки: фото и видео, переключение стрелками.
 */
(function () {
  function parseCsv(str) {
    return str ? str.split(',').map(function (s) { return s.trim(); }).filter(Boolean) : [];
  }

  function isVideoUrl(url) {
    return /\.(mp4|webm|mov|avi)(\?|$)/i.test(url || '');
  }

  /** Сначала обложка, затем ролики, остальные фото — ролики видны после 1–2 кликов. */
  function buildSlides(carousel) {
    var imageUrls = parseCsv(carousel.dataset.imageUrls || '');
    var videoUrls = parseCsv(carousel.dataset.videoUrls || '');
    var paths = parseCsv(carousel.dataset.images || '');
    var baseUrl = window.location.origin + '/static/';
    var slides = [];

    if (!imageUrls.length && paths.length) {
      imageUrls = paths.map(function (p) { return baseUrl + p; });
    }

    if (imageUrls.length) {
      slides.push({ type: 'image', url: imageUrls[0] });
      videoUrls.forEach(function (u) {
        slides.push({ type: 'video', url: u });
      });
      for (var i = 1; i < imageUrls.length; i++) {
        slides.push({ type: 'image', url: imageUrls[i] });
      }
    } else {
      videoUrls.forEach(function (u) {
        slides.push({ type: 'video', url: u });
      });
    }

    return slides;
  }

  function ensureVideoEl(carousel, img) {
    var video = carousel.querySelector('.service-video');
    if (video) return video;
    video = document.createElement('video');
    video.className = 'service-video';
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.setAttribute('loop', '');
    video.setAttribute('controls', '');
    video.setAttribute('preload', 'metadata');
    video.setAttribute('aria-hidden', 'true');
    img.insertAdjacentElement('afterend', video);
    return video;
  }

  function updateIndicator(carousel, idx, total) {
    var el = carousel.querySelector('.card-media-carousel__indicator');
    if (!el) {
      el = document.createElement('span');
      el.className = 'card-media-carousel__indicator';
      el.setAttribute('aria-live', 'polite');
      carousel.appendChild(el);
    }
    if (total > 1) {
      el.textContent = (idx + 1) + ' / ' + total;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function init() {
    document.querySelectorAll('.card-media-carousel').forEach(function (carousel) {
      var slides = buildSlides(carousel);
      if (slides.length < 2) return;

      var img = carousel.querySelector('.service-image');
      if (!img) return;

      var video = ensureVideoEl(carousel, img);
      var prevBtn = carousel.querySelector('.carousel-prev-inner');
      var nextBtn = carousel.querySelector('.carousel-next-inner');
      var idx = 0;

      function pauseVideo() {
        try {
          video.pause();
        } catch (e) { /* ignore */ }
      }

      function showSlide(i) {
        idx = ((i % slides.length) + slides.length) % slides.length;
        var slide = slides[idx];
        updateIndicator(carousel, idx, slides.length);

        if (slide.type === 'video' || isVideoUrl(slide.url)) {
          carousel.classList.add('is-video-slide');
          img.classList.add('card-media-carousel__img--hidden');
          video.style.display = 'block';
          video.setAttribute('aria-hidden', 'false');
          if (video.getAttribute('src') !== slide.url) {
            pauseVideo();
            video.src = slide.url;
            video.load();
          }
          var playPromise = video.play();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(function () { /* autoplay blocked */ });
          }
          return;
        }

        carousel.classList.remove('is-video-slide');
        pauseVideo();
        video.style.display = 'none';
        video.removeAttribute('src');
        video.setAttribute('aria-hidden', 'true');
        img.classList.remove('card-media-carousel__img--hidden');
        img.src = slide.url;
      }

      showSlide(0);

      if (prevBtn) {
        prevBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          showSlide(idx - 1);
        });
      }
      if (nextBtn) {
        nextBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          showSlide(idx + 1);
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
