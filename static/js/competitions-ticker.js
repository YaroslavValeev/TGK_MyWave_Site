/**
 * Бегущая строка соревнований:
 * - autoplay via CSS transform (desktop + mobile, ~840s loop);
 * - pause on hover, focus, touch;
 * - pointer drag / swipe on mobile and desktop (pauses autoplay, then resumes);
 * - prefers-reduced-motion: native horizontal scroll only.
 */
(function () {
  var BASE_DURATION_SEC = 840;
  var DRAG_THRESHOLD_PX = 8;

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function getTranslateX(el) {
    var style = window.getComputedStyle(el);
    var transform = style.transform;
    if (!transform || transform === "none") {
      return 0;
    }
    if (typeof DOMMatrix !== "undefined") {
      return new DOMMatrix(transform).m41;
    }
    var match = transform.match(/matrix\(([^)]+)\)/);
    if (match) {
      var parts = match[1].split(",");
      return parseFloat(parts[4]) || 0;
    }
    return 0;
  }

  function setManualTranslate(track, x) {
    track.style.animation = "none";
    track.style.transform = "translateX(" + x + "px)";
  }

  function syncAnimationFromTranslate(track, durationSec) {
    var half = track.scrollWidth / 2;
    if (!half) {
      track.style.animation = "";
      track.style.transform = "";
      track.style.animationDelay = "";
      return;
    }
    var x = getTranslateX(track);
    var progress = (Math.abs(x) % half) / half;
    var delay = -progress * durationSec;
    track.style.animation = "";
    track.style.transform = "";
    track.style.animationDelay = delay + "s";
    void track.offsetWidth;
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
    var dragState = null;

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
      if (!dragState) {
        scheduleResume(250);
      }
    });
    root.addEventListener("focusin", pauseAutoplay);
    root.addEventListener("focusout", function () {
      if (!dragState) {
        scheduleResume(250);
      }
    });

    function clearDragState(resumeDelay) {
      if (!dragState) {
        return;
      }
      viewport.classList.remove("is-dragging", "is-user-holding");
      try {
        viewport.releasePointerCapture(dragState.pointerId);
      } catch (err) {
        /* ignore */
      }
      dragState = null;
      if (typeof resumeDelay === "number") {
        scheduleResume(resumeDelay);
      }
    }

    function onPointerDown(e) {
      if (e.pointerType === "mouse" && e.button !== 0) {
        return;
      }
      dragState = {
        pointerId: e.pointerId,
        startClientX: e.clientX,
        startClientY: e.clientY,
        startTranslate: getTranslateX(track),
        moved: false,
        target: e.target,
      };
      viewport.classList.add("is-user-holding");
      pauseAutoplay();
      if (viewport.setPointerCapture) {
        viewport.setPointerCapture(e.pointerId);
      }
    }

    function onPointerMove(e) {
      if (!dragState || dragState.pointerId !== e.pointerId) {
        return;
      }
      var dx = e.clientX - dragState.startClientX;
      var dy = e.clientY - dragState.startClientY;

      if (!dragState.moved) {
        if (Math.abs(dy) > DRAG_THRESHOLD_PX && Math.abs(dy) > Math.abs(dx)) {
          clearDragState(250);
          return;
        }
        if (Math.abs(dx) <= DRAG_THRESHOLD_PX) {
          return;
        }
        dragState.moved = true;
      }

      if (e.cancelable) {
        e.preventDefault();
      }
      viewport.classList.add("is-dragging");
      setManualTranslate(track, dragState.startTranslate + dx);
    }

    function onPointerUp(e) {
      if (!dragState || dragState.pointerId !== e.pointerId) {
        return;
      }

      if (dragState.moved) {
        syncAnimationFromTranslate(track, BASE_DURATION_SEC);
        var link = dragState.target.closest && dragState.target.closest("a");
        if (link) {
          link.addEventListener(
            "click",
            function (ev) {
              ev.preventDefault();
            },
            { once: true, capture: true }
          );
        }
        clearDragState(700);
      } else {
        clearDragState(250);
      }
    }

    viewport.addEventListener("pointerdown", onPointerDown);
    viewport.addEventListener("pointermove", onPointerMove);
    viewport.addEventListener("pointerup", onPointerUp);
    viewport.addEventListener("pointercancel", onPointerUp);
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
