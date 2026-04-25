// static/js/catalog-modal.js
(function () {
  const modal = document.getElementById("mwCatalogModal");
  if (!modal) return;

  const overlayCloseEls = modal.querySelectorAll("[data-mw-modal-close]");
  const panel = modal.querySelector(".mw-modal__panel");

  const elTitle = document.getElementById("mwCatalogModalTitle");
  const elPrice = document.getElementById("mwCatalogModalPrice");
  const elDesc = document.getElementById("mwCatalogModalDesc");
  const elImg = document.getElementById("mwCatalogModalImg");
  const elCta = document.getElementById("mwCatalogModalCta");

  const reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let lastActiveEl = null;
  let isClosing = false;
  let trapHandler = null;

  function qsAll(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function openModalFromCard(card) {
    if (!card || isClosing) return;

    lastActiveEl = document.activeElement;

    const title =
      card.dataset.mwTitle ||
      card.dataset.title ||
      card.querySelector("h4")?.textContent?.trim() ||
      "";
    const price =
      card.dataset.mwPrice ||
      card.dataset.price ||
      card.querySelector(".price")?.textContent?.trim() ||
      "";
    const cta =
      card.dataset.mwCtaLabel ||
      card.dataset.cta ||
      "Ок";

    const img = card.querySelector("img");
    const imgSrc = img?.getAttribute("src") || "";
    const imgAlt = img?.getAttribute("alt") || title;

    const details = card.querySelector(".mw-item-card__details");
    const detailHtml = details ? details.innerHTML : "";

    elTitle.textContent = title;
    elPrice.textContent = price;
    elDesc.innerHTML = detailHtml || "<p>Описание скоро появится.</p>";

    elImg.src = imgSrc;
    elImg.alt = imgAlt;
    if (img && img.classList.contains("is-rotated-left")) {
      elImg.classList.add("is-rotated-left");
    } else {
      elImg.classList.remove("is-rotated-left");
    }
    if (img && img.classList.contains("mw-image-contain")) {
      elImg.classList.add("mw-image-contain");
    } else {
      elImg.classList.remove("mw-image-contain");
    }

    elCta.textContent = cta;

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");

    setTimeout(() => {
      panel.focus();
      trapFocus(modal);
    }, 0);
  }

  function closeModal({ disintegrate = true } = {}) {
    if (!modal.classList.contains("is-open") || isClosing) return;

    if (reduceMotion) disintegrate = false;

    if (!disintegrate) {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
      releaseFocusTrap();
      if (lastActiveEl) lastActiveEl.focus();
      return;
    }

    isClosing = true;

    const layer = document.createElement("div");
    layer.className = "mw-disintegrate-layer";
    panel.appendChild(layer);

    const rect = panel.getBoundingClientRect();
    const cols = 6;
    const rows = 3;
    const pieceW = rect.width / cols;
    const pieceH = rect.height / rows;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const piece = document.createElement("div");
        piece.className = "mw-disintegrate-piece";
        piece.style.left = c * pieceW + "px";
        piece.style.top = r * pieceH + "px";
        piece.style.width = pieceW + "px";
        piece.style.height = pieceH + "px";

        const dx = Math.random() * 220 - 110 + "px";
        const dy = Math.random() * 220 - 110 + "px";
        const rot = Math.random() * 40 - 20 + "deg";

        piece.style.setProperty("--dx", dx);
        piece.style.setProperty("--dy", dy);
        piece.style.setProperty("--rot", rot);

        layer.appendChild(piece);
      }
    }

    panel.style.opacity = "0";
    panel.style.transform = "translate(-50%, -50%) scale(.98)";

    setTimeout(() => {
      panel.style.opacity = "";
      panel.style.transform = "";
      layer.remove();

      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
      releaseFocusTrap();
      if (lastActiveEl) lastActiveEl.focus();

      isClosing = false;
    }, 560);
  }

  function trapFocus(root) {
    const focusable = qsAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      root
    ).filter(
      (el) => !el.hasAttribute("disabled") && !el.getAttribute("aria-hidden")
    );

    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    trapHandler = (e) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    root.addEventListener("keydown", trapHandler);
  }

  function releaseFocusTrap() {
    if (!trapHandler) return;
    modal.removeEventListener("keydown", trapHandler);
    trapHandler = null;
  }

  let lastPointerCard = null;

  function findCardFromEvent(e) {
    if (e.composedPath) {
      const path = e.composedPath();
      for (const el of path) {
        if (el && el.classList && el.classList.contains("js-catalog-card")) {
          return el;
        }
      }
    }
    if (e.target && e.target.closest) {
      return e.target.closest(".js-catalog-card");
    }
    return null;
  }

  function handleCardClick(e) {
    if (e.defaultPrevented) return;
    const card = findCardFromEvent(e) || lastPointerCard;
    lastPointerCard = null;
    if (!card) return;

    if (e.target.closest("[data-booking]")) {
      return;
    }
    if (e.target.closest("[data-request-modal]")) {
      return;
    }

    if (
      e.target.closest(".product-card-media-btn") ||
      e.target.closest(".service-card-media-btn")
    ) {
      return;
    }

    if (e.target.closest("button,a")) {
      openModalFromCard(card);
      e.preventDefault();
      return;
    }

    openModalFromCard(card);
  }

  document.addEventListener(
    "pointerdown",
    (e) => {
      lastPointerCard = findCardFromEvent(e);
    },
    true
  );
  document.addEventListener("click", handleCardClick, true);

  document.addEventListener("keydown", (e) => {
    if (!["Enter", " "].includes(e.key)) return;
    if (modal.classList.contains("is-open")) return;
    if (e.target.closest("button,a,input,textarea,select")) return;
    const card = e.target.closest(".js-catalog-card");
    if (!card) return;
    e.preventDefault();
    openModalFromCard(card);
  });

  overlayCloseEls.forEach((el) => {
    el.addEventListener("click", () => closeModal({ disintegrate: true }));
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("is-open")) {
      closeModal({ disintegrate: true });
    }
  });

  elCta.addEventListener("click", () => {
    closeModal({ disintegrate: true });
  });
})();
