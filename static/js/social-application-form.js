(function () {
  function showMessage(el, text, kind) {
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.className = "mw-form-message mw-form-message--" + (kind || "success");
  }

  function toggleTelegramField(form) {
    var select = form.querySelector('[name="preferred_contact"]');
    var field = form.querySelector(".js-social-telegram-field");
    if (!select || !field) return;
    var show = select.value === "telegram";
    field.hidden = !show;
  }

  function initForm(form) {
    if (!form || form.dataset.socialReady === "1") return;
    form.dataset.socialReady = "1";

    var messageEl = document.getElementById("social-form-message");
    var contactSelect = form.querySelector('[name="preferred_contact"]');
    if (contactSelect) {
      contactSelect.addEventListener("change", function () {
        toggleTelegramField(form);
      });
      toggleTelegramField(form);
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      messageEl.hidden = true;

      var fd = new FormData(form);
      var body = {};
      fd.forEach(function (value, key) {
        body[key] = value;
      });
      body.consent_personal_data = form.querySelector('[name="consent_personal_data"]').checked;
      body.consent_training = form.querySelector('[name="consent_training"]').checked;
      body.consent_media = form.querySelector('[name="consent_media"]').checked;

      fetch("/api/social/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
        credentials: "same-origin",
      })
        .then(function (resp) {
          return resp.json().then(function (data) {
            return { ok: resp.ok, status: resp.status, data: data };
          });
        })
        .then(function (result) {
          if (result.ok && result.data && result.data.ok) {
            showMessage(messageEl, result.data.message || "Заявка отправлена.", "success");
            form.reset();
            toggleTelegramField(form);
            return;
          }
          var errText =
            (result.data && result.data.errors && result.data.errors.join(", ")) ||
            (result.data && result.data.error) ||
            "Не удалось отправить заявку. Попробуйте позже.";
          showMessage(messageEl, errText, "error");
        })
        .catch(function () {
          showMessage(messageEl, "Ошибка сети. Проверьте подключение и попробуйте снова.", "error");
        });
    });
  }

  function initAll() {
    document.querySelectorAll("#social-application-form").forEach(initForm);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
