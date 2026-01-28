(() => {
  const ready = (fn) =>
    document.readyState !== "loading" ? fn() : document.addEventListener("DOMContentLoaded", fn);

  ready(() => {
    const fill = document.getElementById("progress-fill");
    const links = Array.from(document.querySelectorAll(".js-scrollspy-link[href^='#']"));
    if (!fill || !links.length) return;

    const items = links
      .map((a) => {
        const id = a.getAttribute("href").slice(1);
        const el = document.getElementById(id);
        return el ? { a, el, top: 0 } : null;
      })
      .filter(Boolean);

    const header = document.querySelector("header") || document.getElementById("site-header");
    let headerH = header ? header.offsetHeight : 0;

    function recalc() {
      headerH = header ? header.offsetHeight : 0;
      document.documentElement.style.setProperty("--mw-header-h", `${headerH}px`);
      items.forEach((it) => (it.top = it.el.getBoundingClientRect().top + window.pageYOffset));
      items.sort((x, y) => x.top - y.top);
    }

    function setActive(activeEl) {
      links.forEach((a) => a.classList.toggle("active", a === activeEl));
    }

    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;

      requestAnimationFrame(() => {
        const marker = window.pageYOffset + headerH + 24;

        let idx = 0;
        for (let i = 0; i < items.length; i++) {
          if (items[i].top <= marker) idx = i;
          else break;
        }

        setActive(items[idx]?.a);

        const curTop = items[idx]?.top ?? 0;
        const nextTop = items[idx + 1]?.top;
        const docEnd = document.documentElement.scrollHeight - window.innerHeight + headerH;
        const endTop = typeof nextTop === "number" ? nextTop : docEnd;

        const denom = Math.max(1, endTop - curTop);
        const sectionProgress = Math.max(0, Math.min(1, (marker - curTop) / denom));
        const total = (idx + sectionProgress) / Math.max(1, items.length);

        fill.style.transform = `scaleX(${total})`;

        ticking = false;
      });
    }

    links.forEach((a) => {
      a.addEventListener("click", (e) => {
        const id = a.getAttribute("href").slice(1);
        const target = document.getElementById(id);
        if (!target) return;
        e.preventDefault();
        const y = target.getBoundingClientRect().top + window.pageYOffset - headerH + 8;
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

