(function () {
  var DEFAULT_CONSENT_VERSION = "2026-07-v1";
  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"];

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
    if (result.status === 503) {
      return "Приём заявок временно недоступен";
    }
    if (result.status >= 500) {
      return "Не удалось отправить заявку, попробуйте позже";
    }
    if (result.data && result.data.errors && result.data.errors.length) {
      return "Проверьте обязательные поля";
    }
    return "Не удалось отправить заявку, попробуйте позже";
  }

  function captureUtm() {
    var params = new URLSearchParams(window.location.search);
    var utm = {};
    UTM_KEYS.forEach(function (key) {
      var val = params.get(key);
      if (val) utm[key] = val;
    });
    return utm;
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

    body.consent_personal_data = form.querySelector('[name="consent_personal_data"]').checked;
    var training = form.querySelector('[name="consent_training"]');
    if (training) body.consent_training = training.checked;

    var utm = captureUtm();
    Object.keys(utm).forEach(function (k) {
      body[k] = utm[k];
    });

    return body;
  }

  function toggleContactFields(form) {
    var select = form.querySelector('[name="preferred_channel"]');
    if (!select) return;
    var mode = (select.value || "").toLowerCase();

    var phoneField = form.querySelector(".js-oc-phone-field");
    var emailField = form.querySelector(".js-oc-email-field");
    var tgField = form.querySelector(".js-oc-telegram-field");
    var waField = form.querySelector(".js-oc-whatsapp-field");
    var maxField = form.querySelector(".js-oc-max-field");

    if (phoneField) phoneField.hidden = mode === "email";
    if (emailField) emailField.hidden = mode !== "email";
    if (tgField) tgField.hidden = mode !== "telegram";
    if (waField) waField.hidden = mode !== "whatsapp";
    if (maxField) maxField.hidden = mode !== "max";
  }

  function preselectServiceType(form) {
    var select = form.querySelector('[name="service_type"]');
    if (!select) return;

    var hash = (window.location.hash || "").replace(/^#/, "").trim().toLowerCase();
    var allowed = ["video_check", "progress_month", "live_coach_land", "live_coach_water"];
    if (hash && allowed.indexOf(hash) !== -1) {
      select.value = hash;
      return;
    }

    var cta = document.querySelector('[data-service-type].is-oc-preselected');
    if (cta) {
      var fromCta = (cta.getAttribute("data-service-type") || "").trim().toLowerCase();
      if (fromCta && allowed.indexOf(fromCta) !== -1) {
        select.value = fromCta;
      }
    }
  }

  function bindServiceCtas(form) {
    document.querySelectorAll("[data-service-type]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-service-type]").forEach(function (el) {
          el.classList.remove("is-oc-preselected");
        });
        btn.classList.add("is-oc-preselected");
        var select = form.querySelector('[name="service_type"]');
        var val = (btn.getAttribute("data-service-type") || "").trim();
        if (select && val) select.value = val;
        var apply = document.getElementById("oc-apply");
        if (apply) apply.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  function initForm(form) {
    if (!form || form.dataset.ocReady === "1") return;
    form.dataset.ocReady = "1";

    var messageEl = document.getElementById("oc-form-message");
    var contactSelect = form.querySelector('[name="preferred_channel"]');
    if (contactSelect) {
      contactSelect.addEventListener("change", function () {
        toggleContactFields(form);
      });
      toggleContactFields(form);
    }

    preselectServiceType(form);
    bindServiceCtas(form);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (messageEl) messageEl.hidden = true;

      var body = buildPayload(form);

      fetch("/api/online-coaching/apply", {
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
              result.data.message || "Заявка принята. Мы свяжемся с вами в выбранном канале.",
              "success"
            );
            form.reset();
            toggleContactFields(form);
            return;
          }
          showMessage(messageEl, resolveErrorMessage(result), "error");
        })
        .catch(function () {
          showMessage(
            messageEl,
            "Ошибка сети. Проверьте подключение и попробуйте снова.",
            "error"
          );
        });
    });
  }

  function initAll() {
    document.querySelectorAll("#oc-application-form").forEach(initForm);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
