/**
 * Обработка форм WakeSurf Safari и плавная прокрутка к якорям (#join и др.).
 */
(() => {
  const ready = (fn) =>
    document.readyState !== "loading" ? fn() : document.addEventListener("DOMContentLoaded", fn);

  async function getCSRFToken() {
    try {
      const r = await fetch("/api/csrf-token", { credentials: "same-origin" });
      const d = await r.json();
      return (d && d.csrf_token) || "";
    } catch {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.content : "";
    }
  }

  function setupAnchorScroll() {
    document.querySelectorAll('.safari-page a[href^="#"]').forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href === "#") return;
      const target = document.querySelector(href);
      if (!target) return;
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const header =
          document.querySelector("header") || document.getElementById("site-header");
        const subnav = document.getElementById("mw-subnav");
        const offset =
          (header ? header.offsetHeight : 0) + (subnav ? subnav.offsetHeight : 0) + 12;
        const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
      });
    });
  }

  ready(() => {
    setupAnchorScroll();

    const participantForm = document.querySelector(".js-safari-participant");
    if (participantForm) {
      setupForm(participantForm, "safari-participant-message");
    }

    const partnerForm = document.querySelector(".js-safari-partner");
    if (partnerForm) {
      setupForm(partnerForm, "safari-partner-message");
    }

    const mediaForm = document.querySelector(".js-safari-media");
    if (mediaForm) {
      setupForm(mediaForm, "safari-media-message");
    }

    const feedbackForm = document.querySelector(".js-safari-feedback");
    if (feedbackForm) {
      setupForm(feedbackForm, "safari-feedback-message");
    }
  });

  function setupForm(form, messageId) {
    const messageEl = document.getElementById(messageId);

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Отправка...";

      if (messageEl) {
        messageEl.textContent = "";
        messageEl.className = "mw-form-message";
      }

      try {
        const formData = new FormData(form);
        const csrfToken = await getCSRFToken();
        if (csrfToken) {
          formData.set("csrf_token", csrfToken);
        }

        const response = await fetch(form.action, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRFToken": csrfToken,
          },
          body: formData,
        });

        let result = {};
        try {
          result = await response.json();
        } catch {
          result = {};
        }

        if (response.ok && result.success) {
          if (messageEl) {
            messageEl.textContent = result.message || "Заявка успешно отправлена!";
            messageEl.className = "mw-form-message mw-form-message--success";
          }
          form.reset();
          if (messageEl) {
            messageEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        } else {
          if (messageEl) {
            messageEl.textContent =
              result.error || "Произошла ошибка при отправке заявки.";
            messageEl.className = "mw-form-message mw-form-message--error";
          }
        }
      } catch (err) {
        console.error("[safari-forms]", err);
        if (messageEl) {
          messageEl.textContent = "Ошибка сети. Пожалуйста, попробуйте позже.";
          messageEl.className = "mw-form-message mw-form-message--error";
        }
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    });
  }
})();
