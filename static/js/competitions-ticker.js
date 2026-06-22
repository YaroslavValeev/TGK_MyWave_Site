/**
 * Бегущая строка соревнований:
 * - desktop + mobile auto-scroll (~840s full loop, same speed);
 * - pause on hover, focus, touch;
 * - prefers-reduced-motion: manual only.
 */
(function () {
  var BASE_DURATION_SEC = 840;
  var MOBILE_AUTO_SCROLL = true;
  var MOBILE_MAX_WIDTH_PX = 768;
  var MIN_PX_PER_FRAME = 0.4;

  function isMobileViewport() {
    return (
      window.matchMedia &&
      window.matchMedia("(max-width: " + MOBILE_MAX_WIDTH_PX + "px)").matches
    );
  }

  function shouldAutoScroll(prefersReduced) {
    if (prefersReduced) {
      return false;
    }
    if (!MOBILE_AUTO_SCROLL && isMobileViewport()) {
      return false;
    }
    return true;
  }

  function initTicker(root) {
    var viewport = root.querySelector(".home-competitions-ticker__viewport");
    var track = root.querySelector("[data-ticker-track]");
    if (!track || !viewport || track.dataset.tickerReady === "1") {
      return;
    }

    var prefersReduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!prefersReduced) {
      var children = Array.from(track.children);
      children.forEach(function (node) {
        var dup = node.cloneNode(true);
        dup.setAttribute("aria-hidden", "true");
        track.appendChild(dup);
      });
    }

    track.dataset.tickerReady = "1";
    viewport.classList.add("is-scrollable");

    if (prefersReduced) {
      viewport.classList.add("is-manual-only");
      return;
    }

    if (!shouldAutoScroll(false)) {
      viewport.classList.add("is-manual-only");
      return;
    }

    var paused = false;
    var userInteracting = false;
    var resumeTimer = null;
    var wheelTimer = null;
    var rafId = null;
    var scrollAccumulator = 0;

    function getDurationSec() {
      return BASE_DURATION_SEC;
    }

    function loopWidth() {
      return track.scrollWidth / 2;
    }

    function normalizeScroll() {
      var lw = loopWidth();
      if (lw <= 0) {
        return;
      }
      while (viewport.scrollLeft >= lw) {
        viewport.scrollLeft -= lw;
      }
      while (viewport.scrollLeft < 0) {
        viewport.scrollLeft += lw;
      }
    }

    function tick() {
      if (!paused && !userInteracting && shouldAutoScroll(false)) {
        var lw = loopWidth();
        if (lw > 0) {
          var pxPerFrame = Math.max(lw / (getDurationSec() * 60), MIN_PX_PER_FRAME);
          scrollAccumulator += pxPerFrame;
          if (scrollAccumulator >= 1) {
            var step = Math.floor(scrollAccumulator);
            viewport.scrollLeft += step;
            scrollAccumulator -= step;
          }
          if (viewport.scrollLeft >= lw) {
            viewport.scrollLeft -= lw;
          }
        }
      }
      rafId = window.requestAnimationFrame(tick);
    }

    function pause() {
      paused = true;
    }

    function scheduleResume(delay) {
      if (resumeTimer) {
        clearTimeout(resumeTimer);
      }
      resumeTimer = setTimeout(function () {
        if (!userInteracting) {
          paused = false;
        }
      }, delay || 600);
    }

    function onInteractStart() {
      userInteracting = true;
      pause();
      viewport.classList.add("is-dragging");
    }

    function onInteractEnd() {
      userInteracting = false;
      viewport.classList.remove("is-dragging");
      normalizeScroll();
      scheduleResume(800);
    }

    root.addEventListener("mouseenter", pause);
    root.addEventListener("mouseleave", function () {
      if (!userInteracting) {
        scheduleResume(200);
      }
    });
    root.addEventListener("focusin", pause);
    root.addEventListener("focusout", function () {
      if (!userInteracting) {
        scheduleResume(200);
      }
    });

    viewport.addEventListener("touchstart", onInteractStart, { passive: true });
    viewport.addEventListener("touchend", onInteractEnd, { passive: true });
    viewport.addEventListener("touchcancel", onInteractEnd, { passive: true });
    viewport.addEventListener("mousedown", function (e) {
      if (e.button !== 0) {
        return;
      }
      onInteractStart();
    });
    viewport.addEventListener("mouseup", onInteractEnd);
    viewport.addEventListener("mouseleave", onInteractEnd);
    viewport.addEventListener("scroll", function () {
      if (userInteracting) {
        normalizeScroll();
      }
    }, { passive: true });
    viewport.addEventListener("wheel", function () {
      onInteractStart();
      if (wheelTimer) {
        clearTimeout(wheelTimer);
      }
      wheelTimer = setTimeout(onInteractEnd, 400);
    }, { passive: true });

    rafId = window.requestAnimationFrame(tick);

    root.addEventListener("destroy", function () {
      if (rafId) {
        window.cancelAnimationFrame(rafId);
      }
    });
  }

  function initAll() {
    document.querySelectorAll(".home-competitions-ticker").forEach(initTicker);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
