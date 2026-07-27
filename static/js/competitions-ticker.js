/**
 * Бегущая строка соревнований:
 * - source of truth: viewport.scrollLeft;
 * - mobile: native horizontal scroll + browser inertia;
 * - desktop: mouse drag + custom momentum;
 * - autoplay: requestAnimationFrame + fractional scrollCarry (Chromium);
 * - loop: cycleWidth normalization on duplicated content;
 * - wide desktop: keep cloning until track overflows (иначе maxScroll=0 и строка стоит).
 */
(function () {
  var AUTO_SPEED_PX_PER_SEC = 18;
  var RESUME_DELAY_MS = 1200;
  var MOUSE_DRAG_THRESHOLD_PX = 5;
  var MOMENTUM_FRICTION = 0.94;
  var MOMENTUM_MIN_VELOCITY = 0.02;
  var MOMENTUM_MAX_VELOCITY = 3.2;
  var MIN_CLONE_SETS = 2;
  var MAX_CLONE_SETS = 8;

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
    var cloneSets = 0;

    function appendCloneSet() {
      children.forEach(function (node) {
        var dup = node.cloneNode(true);
        dup.setAttribute("aria-hidden", "true");
        track.appendChild(dup);
      });
      cloneSets += 1;
    }

    function ensureOverflow() {
      var guard = 0;
      while (
        track.scrollWidth <= viewport.clientWidth * 2 &&
        cloneSets < MAX_CLONE_SETS &&
        guard < MAX_CLONE_SETS
      ) {
        appendCloneSet();
        guard += 1;
      }
      while (cloneSets < MIN_CLONE_SETS) {
        appendCloneSet();
      }
    }

    ensureOverflow();

    track.dataset.tickerReady = "1";
    viewport.classList.add("is-native-scroll", "is-autoplay");

    if (prefersReducedMotion()) {
      viewport.classList.remove("is-autoplay");
      viewport.classList.add("is-manual-only");
      return;
    }

    var cycleWidth = 0;
    var autoplayPaused = false;
    var autoplayFrame = null;
    var lastFrameTime = 0;
    var scrollCarry = 0;
    var resumeTimer = null;
    var dragState = null;
    var momentumFrame = null;

    function measureCycleWidth() {
      var sets = cloneSets + 1;
      cycleWidth = sets > 0 ? track.scrollWidth / sets : 0;
      return cycleWidth;
    }

    function normalizeScroll() {
      var maxScroll = viewport.scrollWidth - viewport.clientWidth;
      if (!cycleWidth || maxScroll <= 0) {
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
        // Accumulate fractional px: Chromium often truncates subpixel scrollLeft.
        scrollCarry += (AUTO_SPEED_PX_PER_SEC * dt) / 1000;
        var delta = scrollCarry | 0;
        if (delta) {
          scrollCarry -= delta;
          viewport.scrollLeft += delta;
          normalizeScroll();
        }
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

    // Do not pause on plain hover — desktop users often keep the cursor over the strip.
    root.addEventListener("focusin", pauseAutoplay);
    root.addEventListener("focusout", function () {
      if (!dragState && !momentumFrame) {
        scheduleResume(250);
      }
    });

    function bootAutoplay() {
      ensureOverflow();
      measureCycleWidth();
      if (cycleWidth > 0 && viewport.scrollWidth > viewport.clientWidth) {
        viewport.scrollLeft = cycleWidth;
      }
      normalizeScroll();
      startAutoplay();
    }

    bootAutoplay();

    // Remeasure after fonts/layout — иначе cycleWidth на десктопе может быть занижен.
    window.requestAnimationFrame(function () {
      bootAutoplay();
    });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        bootAutoplay();
      }).catch(function () { /* ignore */ });
    }

    window.addEventListener("resize", function () {
      ensureOverflow();
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
