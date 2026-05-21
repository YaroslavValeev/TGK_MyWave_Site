/**
 * Бегущая строка соревнований: дублирование track для seamless loop, pause on hover/focus.
 */
(function () {
  function initTicker(root) {
    const track = root.querySelector("[data-ticker-track]");
    if (!track || track.dataset.tickerReady === "1") {
      return;
    }

    const prefersReduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (!prefersReduced) {
      const children = Array.from(track.children);
      children.forEach((node) => {
        const dup = node.cloneNode(true);
        dup.setAttribute("aria-hidden", "true");
        track.appendChild(dup);
      });
    }

    track.dataset.tickerReady = "1";

    const pause = () => track.classList.add("is-paused");
    const resume = () => track.classList.remove("is-paused");

    root.addEventListener("mouseenter", pause);
    root.addEventListener("mouseleave", resume);
    root.addEventListener("focusin", pause);
    root.addEventListener("focusout", resume);
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
