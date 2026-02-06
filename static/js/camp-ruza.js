/**
 * MyWave Camp Ruza — модалка, sticky CTA, валидация формы, FAQ, аналитика.
 */
(function () {
  "use strict";

  var CAMP_RUZA_APPLY_URL = "/api/camp-ruza/apply";
  var ANALYTICS_URL = "/analytics/log";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function getCsrfToken() {
    var el =
      document.querySelector('input[name="csrf_token"]') ||
      document.querySelector('meta[name="csrf-token"]');
    return el ? (el.value || el.getAttribute("content")) : "";
  }

  function getFreshCsrfToken() {
    return fetch("/api/csrf-token", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        return data.csrf_token || getCsrfToken();
      })
      .catch(function () {
        return getCsrfToken();
      });
  }

  function sendAnalytics(eventName, meta) {
    meta = meta || {};
    var payload = { event: eventName, meta: meta };
    getFreshCsrfToken().then(function (token) {
      fetch(ANALYTICS_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token,
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      }).catch(function () {});
    });
    if (window.gtag) {
      gtag("event", eventName, {
        event_category: "camp_ruza",
        event_label: meta.question_id || meta.source_cta || "",
      });
    }
  }

  ready(function () {
    var modal = document.getElementById("camp-ruza-modal");
    var form = document.getElementById("camp-ruza-form");
    var formBox = modal && modal.querySelector(".camp-ruza-modal__box");
    var successEl = document.getElementById("camp-ruza-success");
    var stickyCta = document.getElementById("camp-ruza-sticky-cta");
    var applicantTypeInput = document.getElementById("camp-ruza-applicant-type");
    var healthRestrictions = form && form.querySelectorAll('input[name="health_restrictions"]');
    var healthDetailWrap = form && form.querySelector(".camp-ruza-field--health-detail");
    var healthDetailInput = form && form.querySelector('#health_detail');
    var agreeRules = form && form.querySelector('input[name="agree_rules"]');
    var agreePersonalData = form && form.querySelector('input[name="agree_personal_data"]');
    var healthDocs = form && form.querySelector('input[name="health_docs"]');

    // Просмотр страницы
    sendAnalytics("view_camp_ruza_page");

    // --- Sticky CTA ---
    if (stickyCta) {
      var hero = document.querySelector(".camp-ruza-hero");
      var scrollTreshold = 400;
      function onScroll() {
        var y = window.scrollY || window.pageYOffset;
        if (y >= scrollTreshold) {
          stickyCta.classList.add("is-visible");
          stickyCta.setAttribute("aria-hidden", "false");
        } else {
          stickyCta.classList.remove("is-visible");
          stickyCta.setAttribute("aria-hidden", "true");
        }
      }
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }

    // --- Открытие модалки по CTA ---
    function openModal(source) {
      source = source || "parent";
      if (applicantTypeInput) {
        applicantTypeInput.value = source;
      }
      var whoAppliesRadios = form && form.querySelectorAll('input[name="who_applies"]');
      if (whoAppliesRadios && whoAppliesRadios.length) {
        whoAppliesRadios.forEach(function (r) {
          r.checked = r.value === source;
        });
      }
      if (modal) {
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        if (formBox) formBox.focus();
      }
      sendAnalytics("form_open", { source_cta: source });
      if (source === "parent") {
        sendAnalytics("click_cta_parent");
      } else {
        sendAnalytics("click_cta_teen");
      }
    }

    function closeModal() {
      if (modal) {
        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
      }
    }

    var ctaButtons = document.querySelectorAll(".js-camp-ruza-cta");
    ctaButtons.forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var source = btn.getAttribute("data-source") || "parent";
        openModal(source);
      });
    });

    if (modal) {
      var backdrop = modal.querySelector(".camp-ruza-modal__backdrop");
      var closeBtn = modal.querySelector(".camp-ruza-modal__close");
      if (backdrop) {
        backdrop.addEventListener("click", closeModal);
      }
      if (closeBtn) {
        closeBtn.addEventListener("click", closeModal);
      }
    }

    // --- Поле «Ограничения/аллергии» ---
    if (healthRestrictions && healthRestrictions.length && healthDetailWrap && healthDetailInput) {
      function toggleHealthDetail() {
        var yesChecked = false;
        healthRestrictions.forEach(function (r) {
          if (r.value === "yes" && r.checked) yesChecked = true;
        });
        if (yesChecked) {
          healthDetailWrap.classList.remove("hidden");
          healthDetailInput.setAttribute("required", "required");
        } else {
          healthDetailWrap.classList.add("hidden");
          healthDetailInput.removeAttribute("required");
          healthDetailInput.value = "";
        }
      }
      healthRestrictions.forEach(function (r) {
        r.addEventListener("change", toggleHealthDetail);
      });
      toggleHealthDetail();
    }

    // --- FAQ аккордеон ---
    var faqToggles = document.querySelectorAll(".js-faq-toggle");
    faqToggles.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var item = btn.closest(".camp-ruza-faq-item");
        var questionId = btn.getAttribute("data-faq-id") || "";
        var expanded = btn.getAttribute("aria-expanded") === "true";
        if (item) {
          item.classList.toggle("is-open");
          btn.setAttribute("aria-expanded", !expanded);
          sendAnalytics("faq_open_question", { question_id: questionId });
        }
      });
    });

    // --- Скачивание документов ---
    var downloadLinks = document.querySelectorAll(".js-camp-ruza-download");
    downloadLinks.forEach(function (a) {
      a.addEventListener("click", function () {
        var doc = a.getAttribute("data-doc");
        if (doc === "contract") {
          sendAnalytics("download_contract_pdf");
        } else if (doc === "appendices") {
          sendAnalytics("download_appendices_pdf");
        }
      });
    });

    // --- Валидация и отправка формы ---
    function allRequiredChecked() {
      if (!agreeRules || !agreePersonalData || !healthDocs) return false;
      return agreeRules.checked && agreePersonalData.checked && healthDocs.checked;
    }

    function updateSubmitState() {
      var submitBtn = form && form.querySelector('#camp-ruza-submit');
      if (!submitBtn) return;
      submitBtn.disabled = !allRequiredChecked();
    }

    if (form) {
      [agreeRules, agreePersonalData, healthDocs].forEach(function (el) {
        if (el) el.addEventListener("change", updateSubmitState);
      });
      updateSubmitState();
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!allRequiredChecked()) {
          return;
        }

        sendAnalytics("form_submit_attempt", {
          package_selected: (form.querySelector('select[name="package"]') || {}).value,
          age_group: (form.querySelector('select[name="age_group"]') || {}).value,
          level: (form.querySelector('select[name="level"]') || {}).value,
        });

        var formData = new FormData(form);
        var data = {};
        formData.forEach(function (v, k) {
          data[k] = v;
        });
        data.agree_rules = agreeRules ? agreeRules.checked : false;
        data.agree_personal_data = agreePersonalData ? agreePersonalData.checked : false;
        data.health_docs = healthDocs ? healthDocs.checked : false;

        var submitBtn = form.querySelector('#camp-ruza-submit');
        var originalText = submitBtn ? submitBtn.textContent : "";
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = "Отправка...";
        }

        getFreshCsrfToken().then(function (token) {
          fetch(CAMP_RUZA_APPLY_URL, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": token,
            },
            credentials: "same-origin",
            body: JSON.stringify(data),
          })
            .then(function (res) {
              return res.json().then(function (body) {
                return { ok: res.ok, body: body };
              });
            })
            .then(function (_ref) {
              var ok = _ref.ok;
              var body = _ref.body;
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
              }
              if (ok && body.ok) {
                sendAnalytics("form_submit_success");
                if (form) form.classList.add("hidden");
                if (successEl) {
                  successEl.classList.remove("hidden");
                  successEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
                }
              } else {
                alert(body.error || "Ошибка при отправке заявки. Попробуйте позже.");
              }
            })
            .catch(function () {
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
              }
              alert("Ошибка сети. Попробуйте позже.");
            });
        });
      });
    }
  });
})();
