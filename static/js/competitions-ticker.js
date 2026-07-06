/**
 * Бегущая строка соревнований:
 * - source of truth: viewport.scrollLeft;
 * - mobile: native horizontal scroll + browser inertia;
 * - desktop: mouse drag + custom momentum;
 * - autoplay: requestAnimationFrame;
 * - loop: cycleWidth normalization on duplicated content.
 */
(function () {
  var AUTO_SPEED_PX_PER_SEC = 18;
  var RESUME_DELAY_MS = 1200;
  var MOUSE_DRAG_THRESHOLD_PX = 5;
  var MOMENTUM_FRICTION = 0.94;
  var MOMENTUM_MIN_VELOCITY = 0.02;
  var MOMENTUM_MAX_VELOCITY = 3.2;
  var CLONE_SETS = 2;

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

    var originalCount = track.children.length;
    if (!originalCount) {
      return;
    }

    var children = Array.from(track.children);
    for (var cloneIndex = 0; cloneIndex < CLONE_SETS; cloneIndex += 1) {
      children.forEach(function (node) {
        var dup = node.cloneNode(true);
        dup.setAttribute("aria-hidden", "true");
        track.appendChild(dup);
      });
    }

    track.dataset.tickerReady = "1";
    viewport.classList.add("is-native-scroll");

    if (prefersReducedMotion()) {
      viewport.classList.add("is-manual-only");
      return;
    }

    var cycleWidth = 0;
    var autoplayPaused = false;
    var autoplayFrame = null;
    var lastFrameTime = 0;
    var resumeTimer = null;
    var dragState = null;
    var momentumFrame = null;

    function measureCycleWidth() {
      cycleWidth = track.scrollWidth / (CLONE_SETS + 1);
      return cycleWidth;
    }

    function normalizeScroll() {
      if (!cycleWidth) {
        return;
      }
      while (viewport.scrollLeft >= cycleWidth * 2) {
        viewport.scrollLeft -= cycleWidth;
      }
      while (viewport.scrollLeft <= 0) {
        viewport.scrollLeft += cycleWidth;
      }
    }

    function pauseAutoplay() {
      autoplayPaused = true;
      if (autoplayFrame) {
        window.cancelAnimationFrame(autoplayFrame);
        autoplayFrame = null;
      }
    }

    function scheduleResume(delay) {
      if (resumeTimer) {
        clearTimeout(resumeTimer);
      }
      resumeTimer = setTimeout(function () {
        if (!dragState && !momentumFrame) {
          autoplayPaused = false;
          lastFrameTime = 0;
          startAutoplay();
        }
      }, delay || RESUME_DELAY_MS);
    }

    function startAutoplay() {
      if (autoplayFrame || autoplayPaused) {
        return;
      }

      function step(now) {
        if (autoplayPaused) {
          autoplayFrame = null;
          return;
        }
        if (!lastFrameTime) {
          lastFrameTime = now;
        }
        var dt = now - lastFrameTime;
        lastFrameTime = now;
        viewport.scrollLeft += AUTO_SPEED_PX_PER_SEC * dt / 1000;
        normalizeScroll();
        autoplayFrame = window.requestAnimationFrame(step);
      }

      autoplayFrame = window.requestAnimationFrame(step);
    }

    function onTouchStart() {
      pauseAutoplay();
    }

    function onTouchEnd() {
      normalizeScroll();
      scheduleResume(RESUME_DELAY_MS);
    }

    viewport.addEventListener("touchstart", onTouchStart, { passive: true });
    viewport.addEventListener("touchend", onTouchEnd, { passive: true });
    viewport.addEventListener("touchcancel", onTouchEnd, { passive: true });
    viewport.addEventListener("scroll", normalizeScroll, { passive: true });

    function clearDragState() {
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
    }

    function startMomentum(state) {
      var velocity = -state.velocityX * 16;

      function step() {
        if (Math.abs(velocity) <= MOMENTUM_MIN_VELOCITY) {
          momentumFrame = null;
          normalizeScroll();
          scheduleResume(RESUME_DELAY_MS);
          return;
        }
        viewport.scrollLeft += velocity;
        velocity *= MOMENTUM_FRICTION;
        normalizeScroll();
        momentumFrame = window.requestAnimationFrame(step);
      }

      if (momentumFrame) {
        window.cancelAnimationFrame(momentumFrame);
      }
      momentumFrame = window.requestAnimationFrame(step);
    }

    function onPointerDown(e) {
      if (e.pointerType !== "mouse" || e.button !== 0) {
        return;
      }
      if (momentumFrame) {
        window.cancelAnimationFrame(momentumFrame);
        momentumFrame = null;
      }
      pauseAutoplay();
      dragState = {
        pointerId: e.pointerId,
        startClientX: e.clientX,
        startScrollLeft: viewport.scrollLeft,
        lastClientX: e.clientX,
        lastTime: performance.now(),
        velocityX: 0,
        moved: false,
        target: e.target,
      };
      viewport.classList.add("is-user-holding");
      if (viewport.setPointerCapture) {
        viewport.setPointerCapture(e.pointerId);
      }
    }

    function onPointerMove(e) {
      if (!dragState || dragState.pointerId !== e.pointerId || e.pointerType !== "mouse") {
        return;
      }

      var dx = e.clientX - dragState.startClientX;
      if (!dragState.moved) {
        if (Math.abs(dx) < MOUSE_DRAG_THRESHOLD_PX) {
          return;
        }
        dragState.moved = true;
      }

      if (e.cancelable) {
        e.preventDefault();
      }
      viewport.classList.add("is-dragging");

      var now = performance.now();
      var frameDx = e.clientX - dragState.lastClientX;
      var dt = Math.max(16, now - dragState.lastTime);
      dragState.velocityX = Math.max(
        -MOMENTUM_MAX_VELOCITY,
        Math.min(MOMENTUM_MAX_VELOCITY, frameDx / dt)
      );
      dragState.lastClientX = e.clientX;
      dragState.lastTime = now;

      viewport.scrollLeft = dragState.startScrollLeft - (e.clientX - dragState.startClientX);
      normalizeScroll();
    }

    function onPointerUp(e) {
      if (!dragState || dragState.pointerId !== e.pointerId) {
        return;
      }

      if (dragState.moved) {
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
        startMomentum(dragState);
      } else {
        scheduleResume(250);
      }
      clearDragState();
    }

    viewport.addEventListener("pointerdown", onPointerDown);
    viewport.addEventListener("pointermove", onPointerMove);
    viewport.addEventListener("pointerup", onPointerUp);
    viewport.addEventListener("pointercancel", onPointerUp);

    root.addEventListener("mouseenter", pauseAutoplay);
    root.addEventListener("mouseleave", function () {
      if (!dragState && !momentumFrame) {
        scheduleResume(250);
      }
    });
    root.addEventListener("focusin", pauseAutoplay);
    root.addEventListener("focusout", function () {
      if (!dragState && !momentumFrame) {
        scheduleResume(250);
      }
    });

    measureCycleWidth();
    viewport.scrollLeft = cycleWidth;
    normalizeScroll();
    startAutoplay();

    window.addEventListener("resize", function () {
      measureCycleWidth();
      normalizeScroll();
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
