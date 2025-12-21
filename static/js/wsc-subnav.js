(() => {
  const ready = (fn) =>
    document.readyState !== "loading" ? fn() : document.addEventListener("DOMContentLoaded", fn);

  ready(() => {
    const header = document.getElementById("site-header");
    const root = document.documentElement;
    const links = Array.from(document.querySelectorAll(".js-wsc-link[href^='#']"));
    if (!links.length) return;

    const items = links
      .map((a) => {
        const id = a.getAttribute("href").slice(1);
        const el = document.getElementById(id);
        return el ? { id, a, el, top: 0 } : null;
      })
      .filter(Boolean);

    let headerOffset = header ? header.offsetHeight : 0;

    function recalc() {
      headerOffset = header ? header.offsetHeight : 0;
      root.style.setProperty("--mw-header-h", `${headerOffset}px`);
      items.forEach((it) => (it.top = it.el.getBoundingClientRect().top + window.pageYOffset));
      items.sort((x, y) => x.top - y.top);
    }

    function setActive(id) {
      links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${id}`));
    }

    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;

      requestAnimationFrame(() => {
        const marker = window.pageYOffset + headerOffset + 24;

        let idx = 0;
        for (let i = 0; i < items.length; i++) {
          if (items[i].top <= marker) idx = i;
          else break;
        }

        const current = items[idx]?.id;
        if (current) setActive(current);

        // sync with global progress bar if exists
        const fill = document.getElementById("progress-fill");
        if (fill && items.length) {
          const curTop = items[idx].top;
          const nextTop = items[idx + 1]?.top;
          const docEnd = document.documentElement.scrollHeight - window.innerHeight + headerOffset;
          const endTop = typeof nextTop === "number" ? nextTop : docEnd;
          const denom = Math.max(1, endTop - curTop);
          const sectionProgress = Math.max(0, Math.min(1, (marker - curTop) / denom));
          const total = (idx + sectionProgress) / items.length;
          fill.style.transform = `scaleX(${total})`;
        }

        ticking = false;
      });
    }

    // smooth scroll
    links.forEach((a) => {
      a.addEventListener("click", (e) => {
        const id = a.getAttribute("href").slice(1);
        const target = document.getElementById(id);
        if (!target) return;
        e.preventDefault();
        const y = target.getBoundingClientRect().top + window.pageYOffset - headerOffset + 8;
        window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
        history.replaceState(null, "", `#${id}`);
      });
    });

    recalc();
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", () => { recalc(); onScroll(); });
    window.addEventListener("load", () => { recalc(); onScroll(); });
  });
})();

