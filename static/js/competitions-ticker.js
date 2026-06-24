/**
 * Бегущая строка соревнований:
 * - autoplay via CSS transform (desktop + mobile, ~840s loop);
 * - pause on hover, focus, touch;
 * - prefers-reduced-motion: manual scroll only.
 *
 * Note: programmatic scrolling on overflow containers is unreliable on iOS Safari.
 */
(function () {
  var BASE_DURATION_SEC = 840;

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function initTicker(root) {
    var viewport = root.querySelector(".home-competitions-ticker__viewport");
    var track = root.querySelector("[data-ticker-track]");
    if (!track || !viewport || track.dataset.tickerReady === "1") {
      return;
    }

    var reduced = prefersReducedMotion();

    if (!reduced) {
      var children = Array.from(track.children);
      children.forEach(function (node) {
        var dup = node.cloneNode(true);
        dup.setAttribute("aria-hidden", "true");
        track.appendChild(dup);
      });
    }

    track.dataset.tickerReady = "1";
    root.style.setProperty("--ticker-duration", BASE_DURATION_SEC + "s");
    viewport.classList.add("is-scrollable");

    if (reduced) {
      viewport.classList.add("is-manual-only");
      return;
    }

    viewport.classList.add("is-autoplay");

    var resumeTimer = null;

    function pauseAutoplay() {
      viewport.classList.add("is-paused");
    }

    function scheduleResume(delay) {
      if (resumeTimer) {
        clearTimeout(resumeTimer);
      }
      resumeTimer = setTimeout(function () {
        if (!viewport.classList.contains("is-user-holding")) {
          viewport.classList.remove("is-paused");
        }
      }, delay || 500);
    }

    root.addEventListener("mouseenter", pauseAutoplay);
    root.addEventListener("mouseleave", function () {
      scheduleResume(250);
    });
    root.addEventListener("focusin", pauseAutoplay);
    root.addEventListener("focusout", function () {
      scheduleResume(250);
    });

    viewport.addEventListener(
      "touchstart",
      function () {
        viewport.classList.add("is-user-holding");
        pauseAutoplay();
      },
      { passive: true }
    );

    function onTouchEnd() {
      viewport.classList.remove("is-user-holding");
      scheduleResume(700);
    }

    viewport.addEventListener("touchend", onTouchEnd, { passive: true });
    viewport.addEventListener("touchcancel", onTouchEnd, { passive: true });
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
