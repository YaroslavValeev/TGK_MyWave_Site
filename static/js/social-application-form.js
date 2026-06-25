(function () {
  var DEFAULT_CONSENT_VERSION = "2026-06-v1";

  function showMessage(el, text, kind) {
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.className = "mw-form-message mw-form-message--" + (kind || "success");
  }

  function parseResponse(resp) {
    return resp.text().then(function (text) {
      var data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch (e) {
          data = null;
        }
      }
      return { ok: resp.ok, status: resp.status, data: data };
    });
  }

  function resolveErrorMessage(result) {
    if (result.status === 400) {
      return "Проверьте обязательные поля";
    }
    if (result.status >= 500) {
      return "Не удалось отправить заявку, попробуйте позже";
    }
    if (result.data && result.data.errors && result.data.errors.length) {
      return "Проверьте обязательные поля";
    }
    return "Не удалось отправить заявку, попробуйте позже";
  }

  function buildPayload(form) {
    var fd = new FormData(form);
    var body = {};
    fd.forEach(function (value, key) {
      body[key] = value;
    });

    var consentInput = form.querySelector('[name="consent_version"]');
    body.consent_version =
      (body.consent_version && String(body.consent_version).trim()) ||
      (consentInput && consentInput.value) ||
      DEFAULT_CONSENT_VERSION;

    if (body.child_age !== undefined && body.child_age !== "") {
      body.child_age = parseInt(body.child_age, 10);
    }

    body.consent_personal_data = form.querySelector('[name="consent_personal_data"]').checked;
    body.consent_training = form.querySelector('[name="consent_training"]').checked;
    body.consent_media = form.querySelector('[name="consent_media"]').checked;

    return body;
  }

  function toggleContactFields(form) {
    var select = form.querySelector('[name="preferred_contact"]');
    var phoneField = form.querySelector(".js-social-phone-field");
    var tgField = form.querySelector(".js-social-telegram-field");
    if (!select) return;
    var mode = select.value;
    if (phoneField) phoneField.hidden = mode === "telegram";
    if (tgField) tgField.hidden = mode !== "telegram";
  }

  function initForm(form) {
    if (!form || form.dataset.socialReady === "1") return;
    form.dataset.socialReady = "1";

    var messageEl = document.getElementById("social-form-message");
    var contactSelect = form.querySelector('[name="preferred_contact"]');
    if (contactSelect) {
      contactSelect.addEventListener("change", function () {
        toggleContactFields(form);
      });
      toggleContactFields(form);
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      messageEl.hidden = true;

      var body = buildPayload(form);

      fetch("/api/social/apply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
        credentials: "same-origin",
      })
        .then(parseResponse)
        .then(function (result) {
          if (result.ok && result.data && result.data.ok) {
            showMessage(
              messageEl,
              (result.data.message || "Заявка отправлена"),
              "success"
            );
            form.reset();
            toggleContactFields(form);
            return;
          }
          showMessage(messageEl, resolveErrorMessage(result), "error");
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
