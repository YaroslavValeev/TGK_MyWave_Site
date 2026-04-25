// static/js/loop-carousel.js
(function () {
  const carousels = document.querySelectorAll("[data-loop-carousel]");
  if (!carousels.length) return;

  carousels.forEach((root) => {
    const track = root.querySelector("[data-loop-track]");
    const prevBtn = root.querySelector("[data-loop-prev]");
    const nextBtn = root.querySelector("[data-loop-next]");
    const viewport = root.querySelector(".mw-loop-carousel__viewport");

    if (!track || !prevBtn || !nextBtn || !viewport) return;

    const reduceMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let index = 0;
    let isAnimating = false;

    function getCardWidth() {
      const card = track.querySelector(".mw-item-card");
      if (!card) return 320;
      const rect = card.getBoundingClientRect();
      const style = window.getComputedStyle(track);
      const gap = parseFloat(style.columnGap || style.gap || "0") || 0;
      return rect.width + gap;
    }

    function update() {
      const w = getCardWidth();
      track.style.transform = `translateX(${-(index * w)}px)`;
    }

    function move(dir) {
      if (isAnimating && !reduceMotion) return;

      const items = track.querySelectorAll(".mw-item-card");
      if (!items.length) return;

      isAnimating = true;

      index += dir;
      if (index < 0) index = items.length - 1;
      if (index >= items.length) index = 0;

      update();

      if (reduceMotion) {
        isAnimating = false;
      } else {
        setTimeout(() => {
          isAnimating = false;
        }, 280);
      }
    }

    prevBtn.addEventListener("click", () => move(-1));
    nextBtn.addEventListener("click", () => move(1));

    viewport.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") move(-1);
      if (e.key === "ArrowRight") move(1);
    });

    let startX = 0;
    let startY = 0;
    let tracking = false;

    viewport.addEventListener("pointerdown", (e) => {
      tracking = true;
      startX = e.clientX;
      startY = e.clientY;
      viewport.setPointerCapture(e.pointerId);
    });

    viewport.addEventListener("pointerup", (e) => {
      if (!tracking) return;
      tracking = false;

      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dy) > Math.abs(dx)) return;

      if (dx > 40) move(-1);
      if (dx < -40) move(1);
    });

    window.addEventListener("resize", update);
    update();
  });
})();
