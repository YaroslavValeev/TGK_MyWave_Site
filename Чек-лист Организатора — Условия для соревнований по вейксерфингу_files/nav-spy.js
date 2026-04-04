(() => {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(() => {
    const header = document.getElementById("site-header");
    const nav = document.getElementById("site-nav");
    const burger = document.getElementById("burger-menu");
    const ul = nav ? nav.querySelector("ul") : null;

    const progressBar = document.getElementById("progress-bar");
    const progressFill = document.getElementById("progress-fill");
    const root = document.documentElement;

    function setProgress(p) {
      if (!progressFill) return;
      const v = Math.max(0, Math.min(1, p));
      progressFill.style.transform = `scaleX(${v})`;
    }

    const links = Array.from(document.querySelectorAll("#site-nav a.js-nav-link[href^='#']"));
    if (!links.length) return;

    let headerOffset = header ? header.offsetHeight : 0;

    const items = links
      .map((a) => {
        const id = (a.getAttribute("href") || "").replace("#", "").trim();
        const el = id ? document.getElementById(id) : null;
        return el ? { id, a, el, top: 0 } : null;
      })
      .filter(Boolean);

    function recalcTops() {
      headerOffset = header ? header.offsetHeight : 0;
      if (root) root.style.setProperty("--mw-header-h", `${headerOffset}px`);
      items.forEach((it) => {
        it.top = it.el.getBoundingClientRect().top + window.pageYOffset;
      });
      items.sort((x, y) => x.top - y.top);
    }

    function setActive(id) {
      links.forEach((a) => {
        const isActive = a.getAttribute("href") === `#${id}`;
        a.classList.toggle("active", isActive);
        if (isActive) a.setAttribute("aria-current", "page");
        else a.removeAttribute("aria-current");
      });
    }

    function closeMobileMenu() {
      // поддержка обоих вариантов из style.css (open на nav и active на ul/burger)
      if (nav) nav.classList.remove("open");
      if (ul) ul.classList.remove("active");
      if (burger) burger.classList.remove("active");
    }

    // Smooth scroll with header offset
    links.forEach((a) => {
      a.addEventListener("click", (e) => {
        const href = a.getAttribute("href");
        if (!href || !href.startsWith("#")) return;

        const id = href.slice(1);
        const target = document.getElementById(id);
        if (!target) return;

        e.preventDefault();

        const y = target.getBoundingClientRect().top + window.pageYOffset - (headerOffset || 0) + 8;
        window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });

        closeMobileMenu();
        history.replaceState(null, "", href);
      });
    });

    // Scroll spy (throttled)
    let ticking = false;

    function onScroll() {
      if (ticking) return;
      ticking = true;

      window.requestAnimationFrame(() => {
        const marker = window.pageYOffset + (headerOffset || 0) + 24;

        let currentIdx = 0;
        for (let i = 0; i < items.length; i++) {
          if (items[i].top <= marker) currentIdx = i;
          else break;
        }

        const current = items[currentIdx]?.id;
        if (current) setActive(current);

        /* Section-synced progress:
           - прогресс внутри текущей секции
           - плюс прогресс по количеству секций */
        if (items.length) {
          const currentTop = items[currentIdx].top;
          const nextTop = items[currentIdx + 1]?.top;

          // если это последняя секция — берём нижнюю границу документа
          const docEnd = (document.documentElement.scrollHeight - window.innerHeight) + (headerOffset || 0);
          const endTop = (typeof nextTop === "number") ? nextTop : docEnd;

          const denom = Math.max(1, endTop - currentTop);
          const sectionProgress = Math.max(0, Math.min(1, (marker - currentTop) / denom));

          const total = (currentIdx + sectionProgress) / items.length;
          setProgress(total);
        }

        ticking = false;
      });
    }

    // Init
    recalcTops();
    onScroll();

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", () => {
      recalcTops();
      onScroll();
    });

    // Recalc after images load (hero, cards)
    window.addEventListener("load", () => {
      recalcTops();
      onScroll();
    });
  });
})();

