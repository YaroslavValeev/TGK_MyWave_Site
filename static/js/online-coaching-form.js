(function () {
  var DEFAULT_CONSENT_VERSION = "2026-07-v1";
  var UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"];
  var state = {
    onlineRequestId: "",
    serviceType: "",
    showVideoStep: false,
  };

  function showMessage(el, text, kind) {
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.className = "mw-form-message mw-form-message--" + (kind || "success");
  }

  function hideMessage(el) {
    if (el) el.hidden = true;
  }

  function showPanel(el) {
    if (el) el.hidden = false;
  }

  function hidePanel(el) {
    if (el) el.hidden = true;
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

  function resolveMediaErrorMessage(result) {
    if (result.status === 400) {
      return "Проверьте ссылки и обязательные поля";
    }
    if (result.status === 404) {
      return "Заявка не найдена. Отправьте анкету заново.";
    }
    if (result.status === 409) {
      return "Видео уже отправлено по этой заявке";
    }
    if (result.status >= 500) {
      return "Не удалось отправить видео, попробуйте позже";
    }
    return "Не удалось отправить видео, попробуйте позже";
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

  function buildMediaPayload(form) {
    var urls = [];
    ["video_url_1", "video_url_2", "video_url_3"].forEach(function (name) {
      var input = form.querySelector('[name="' + name + '"]');
      var val = input && String(input.value || "").trim();
      if (val) urls.push(val);
    });
    return {
      video_urls: urls,
      review_task: String((form.querySelector('[name="review_task"]') || {}).value || "").trim(),
      training_comment: String((form.querySelector('[name="training_comment"]') || {}).value || "").trim(),
      training_date: String((form.querySelector('[name="training_date"]') || {}).value || "").trim(),
      spot_or_location: String((form.querySelector('[name="spot_or_location"]') || {}).value || "").trim(),
    };
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

  function showApplySuccess(data) {
    var applyForm = document.getElementById("oc-application-form");
    var successPanel = document.getElementById("oc-apply-success");
    var requestIdEl = document.getElementById("oc-request-id-display");
    var successText = document.getElementById("oc-apply-success-text");
    var videoForm = document.getElementById("oc-video-form");
    var donePanel = document.getElementById("oc-video-done");

    hidePanel(videoForm);
    hidePanel(donePanel);

    if (data.show_video_step) {
      hidePanel(applyForm);
      showPanel(successPanel);
      if (requestIdEl) requestIdEl.textContent = data.online_request_id || "";
      if (successText) {
        successText.textContent =
          data.message ||
          "Следующий шаг — добавьте видео тренировки, задачу для разбора и комментарий. Оплата за разбор видео — после получения разбора.";
      }
      state.onlineRequestId = data.online_request_id || "";
      state.showVideoStep = true;
      return;
    }

    showMessage(
      document.getElementById("oc-form-message"),
      data.message || "Заявка принята. Мы свяжемся с вами в выбранном канале.",
      "success"
    );
    if (applyForm) applyForm.reset();
    toggleContactFields(applyForm);
  }

  function showVideoStep() {
    var successPanel = document.getElementById("oc-apply-success");
    var videoForm = document.getElementById("oc-video-form");
    hidePanel(successPanel);
    showPanel(videoForm);
    if (videoForm) videoForm.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function showVideoDone() {
    var videoForm = document.getElementById("oc-video-form");
    var donePanel = document.getElementById("oc-video-done");
    hidePanel(videoForm);
    showPanel(donePanel);
    if (donePanel) donePanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function initVideoForm() {
    var videoForm = document.getElementById("oc-video-form");
    if (!videoForm || videoForm.dataset.ocReady === "1") return;
    videoForm.dataset.ocReady = "1";

    var messageEl = document.getElementById("oc-video-message");
    var addVideoBtn = document.getElementById("oc-btn-add-video");
    if (addVideoBtn) {
      addVideoBtn.addEventListener("click", showVideoStep);
    }

    videoForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (messageEl) messageEl.hidden = true;
      if (!state.onlineRequestId) {
        showMessage(messageEl, "Сначала отправьте заявку.", "error");
        return;
      }

      var body = buildMediaPayload(videoForm);
      fetch("/api/online-coaching/" + encodeURIComponent(state.onlineRequestId) + "/media", {
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
            showVideoDone();
            return;
          }
          showMessage(messageEl, resolveMediaErrorMessage(result), "error");
        })
        .catch(function () {
          showMessage(messageEl, "Ошибка сети. Проверьте подключение и попробуйте снова.", "error");
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
      state.serviceType = String(body.service_type || "").toLowerCase();

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
            showApplySuccess(result.data);
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
    initVideoForm();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
